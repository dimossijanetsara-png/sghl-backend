"""Prometheus metrics collection for SGHL backend."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import time
from functools import wraps

# Request metrics
REQUEST_COUNT = Counter(
    'sghl_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'sghl_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

REQUEST_SIZE = Histogram(
    'sghl_http_request_size_bytes',
    'HTTP request size in bytes',
    ['method'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

RESPONSE_SIZE = Histogram(
    'sghl_http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'status'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# Database metrics
DB_CONNECTIONS_ACTIVE = Gauge(
    'sghl_db_connections_active',
    'Active database connections'
)

DB_QUERY_DURATION = Histogram(
    'sghl_db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],  # SELECT, INSERT, UPDATE, DELETE
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5]
)

# Cache metrics
CACHE_HITS = Counter(
    'sghl_cache_hits_total',
    'Total cache hits',
    ['cache_key']
)

CACHE_MISSES = Counter(
    'sghl_cache_misses_total',
    'Total cache misses',
    ['cache_key']
)

CACHE_SIZE = Gauge(
    'sghl_cache_size_bytes',
    'Current cache size in bytes'
)

# Business metrics
ACTIVE_HOSPITALIZATIONS = Gauge(
    'sghl_active_hospitalizations',
    'Number of active hospitalizations'
)

OCCUPIED_BEDS = Gauge(
    'sghl_occupied_beds',
    'Number of occupied beds'
)

PENDING_LAB_ORDERS = Gauge(
    'sghl_pending_lab_orders',
    'Number of pending lab orders'
)

PENDING_PRESCRIPTIONS = Gauge(
    'sghl_pending_prescriptions',
    'Number of pending prescriptions'
)

# Error metrics
ERROR_RATE = Counter(
    'sghl_errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)

AUTHENTICATION_FAILURES = Counter(
    'sghl_auth_failures_total',
    'Total authentication failures',
    ['reason']  # invalid_credentials, mfa_failed, account_locked, etc.
)

# Task metrics (Celery)
CELERY_TASKS_PENDING = Gauge(
    'sghl_celery_tasks_pending',
    'Number of pending Celery tasks'
)

CELERY_TASKS_ACTIVE = Gauge(
    'sghl_celery_tasks_active',
    'Number of active Celery tasks'
)

CELERY_TASK_DURATION = Histogram(
    'sghl_celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name'],
    buckets=[1, 5, 10, 30, 60, 300]
)


def track_metrics():
    """Decorator to track API endpoint metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            endpoint = request.path.replace('/api/v1', '')
            method = request.method

            try:
                response = func(request, *args, **kwargs)
                duration = time.time() - start_time
                status = getattr(response, 'status_code', 200)

                REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
                REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

                if hasattr(request, 'content_length') and request.content_length:
                    REQUEST_SIZE.labels(method=method).observe(request.content_length)

                if hasattr(response, 'content_length') and response.content_length:
                    RESPONSE_SIZE.labels(method=method, status=status).observe(response.content_length)

                return response
            except Exception as e:
                duration = time.time() - start_time
                ERROR_RATE.labels(error_type=type(e).__name__, endpoint=endpoint).inc()
                REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=500).inc()
                REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
                raise

        return wrapper
    return decorator


def get_metrics():
    """Generate Prometheus metrics in text format."""
    return generate_latest(REGISTRY)
