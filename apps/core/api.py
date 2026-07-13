from ninja import NinjaAPI
from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
import logging

User = get_user_model()
logger = logging.getLogger('apps.core')


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            access_token = AccessToken(token)
            user = User.objects.get(id=access_token['user_id'])
            if not user.is_active:
                return None
            request.user = user
            return user
        except Exception:
            return None


jwt_auth = JWTAuth()

api = NinjaAPI(
    title='SGHL API',
    version='1.0.0',
    description='Système de Gestion Hospitalière et de Laboratoire',
    docs_url='/docs',
    auth=jwt_auth,
)


@api.get('/health', auth=None, tags=['Système'])
def health_check(request):
    """Liveness and readiness probe for Kubernetes."""
    from django.db import connection, DatabaseError
    from django.core.cache import cache
    import redis

    checks = {}
    errors = []

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = 'ok'
    except DatabaseError as e:
        checks['database'] = 'error'
        errors.append(f'Database: {str(e)}')

    # Cache/Redis check
    try:
        cache.set('health_check', 'ok', 5)
        if cache.get('health_check') == 'ok':
            checks['cache'] = 'ok'
        else:
            checks['cache'] = 'degraded'
            errors.append('Cache get failed')
    except Exception as e:
        checks['cache'] = 'error'
        errors.append(f'Cache: {str(e)}')

    # Storage check (media directory writable)
    from django.conf import settings
    try:
        test_file = settings.MEDIA_ROOT / '.health_check'
        test_file.touch()
        test_file.unlink()
        checks['storage'] = 'ok'
    except Exception as e:
        checks['storage'] = 'error'
        errors.append(f'Storage: {str(e)}')

    overall_status = 'ok' if not errors else ('degraded' if len(errors) < 3 else 'critical')

    response_data = {
        'status': overall_status,
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
        'checks': checks,
    }

    if errors:
        response_data['errors'] = errors

    status_code = 200 if overall_status == 'ok' else (503 if overall_status == 'critical' else 200)
    return response_data


@api.get('/metrics', auth=None, tags=['Système'])
def metrics(request):
    """Prometheus metrics endpoint."""
    from apps.core.metrics import get_metrics

    # Only allow from localhost or specific IPs in production
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    allowed_ips = ['127.0.0.1', 'localhost', '0.0.0.0']

    if not request.META.get('DEBUG') and client_ip not in allowed_ips:
        from ninja.errors import HttpError
        raise HttpError(403, 'Metrics endpoint access denied')

    metrics_data = get_metrics()
    return HttpResponse(metrics_data, content_type='text/plain')


# Enregistrement des routers de chaque module
from apps.authentication.api import router as auth_router
from apps.patients.api import router as patients_router
from apps.clinical.api import router as clinical_router
from apps.hospitalization.api import router as hospitalization_router
from apps.nursing.api import router as nursing_router
from apps.laboratory.api import router as laboratory_router
from apps.pharmacy.api import router as pharmacy_router
from apps.billing.api import router as billing_router
from apps.hr.api import router as hr_router
from apps.appointments.api import router as appointments_router
from apps.messaging.api import router as messaging_router
from apps.dashboard.api import router as dashboard_router

api.add_router('/auth', auth_router, tags=['Authentification'])
api.add_router('/patients', patients_router, tags=['Patients'])
api.add_router('/clinique', clinical_router, tags=['Clinique'])
api.add_router('/hospitalisation', hospitalization_router, tags=['Hospitalisation'])
api.add_router('/soins', nursing_router, tags=['Soins Infirmiers'])
api.add_router('/laboratoire', laboratory_router, tags=['Laboratoire'])
api.add_router('/pharmacie', pharmacy_router, tags=['Pharmacie'])
api.add_router('/facturation', billing_router, tags=['Facturation'])
api.add_router('/rh', hr_router, tags=['Ressources Humaines'])
api.add_router('/rendez-vous', appointments_router, tags=['Rendez-vous'])
api.add_router('/messagerie', messaging_router, tags=['Messagerie'])
api.add_router('/dashboard', dashboard_router, tags=['Dashboard'])
