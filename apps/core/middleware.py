import time
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
from apps.core.metrics import REQUEST_COUNT, REQUEST_DURATION, ERROR_RATE

logger = logging.getLogger('apps.core')


class MetricsMiddleware:
    """Track API metrics for Prometheus monitoring."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        start_time = time.time()
        endpoint = request.path.replace('/api/v1', '')
        method = request.method

        try:
            response = self.get_response(request)
            duration = time.time() - start_time
            status = response.status_code

            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

            return response
        except Exception as e:
            duration = time.time() - start_time
            ERROR_RATE.labels(error_type=type(e).__name__, endpoint=endpoint).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            raise


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        if request.path.startswith('/api/') and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            user_id = getattr(getattr(request, 'user', None), 'id', None)
            logger.info(
                'API %s %s user=%s status=%s duration=%.3fs ip=%s',
                request.method, request.path, user_id,
                response.status_code, duration, self._get_client_ip(request)
            )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.limit = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        self.window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)

    def __call__(self, request):
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        try:
            ip = self._get_client_ip(request)
            cache_key = f'rate_limit:{ip}'
            count = cache.get(cache_key, 0)

            if count >= self.limit:
                return JsonResponse(
                    {'detail': 'Trop de requetes. Reessayez plus tard.'},
                    status=429
                )

            if count == 0:
                cache.set(cache_key, 1, self.window)
            else:
                cache.incr(cache_key)
        except Exception:
            # Cache indisponible : on laisse passer sans rate limiting
            pass

        return self.get_response(request)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model


@database_sync_to_async
def get_user_from_token(token_key):
    User = get_user_model()
    try:
        token = AccessToken(token_key)
        return User.objects.get(id=token['user_id'])
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        token = params.get('token', '')
        scope['user'] = await get_user_from_token(token)
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
