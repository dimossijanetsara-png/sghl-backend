"""Celery configuration for SGHL backend."""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('sghl')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery configurations
app.conf.update(
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Result backend settings
    result_backend_transport_options={
        'retry_on_timeout': True,
        'health_check_interval': 30,
    },

    # Task settings
    task_serializer='json',
    accept_content=['application/json'],
    result_serializer='json',
    timezone='Africa/Brazzaville',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit for cleanup

    # Beat schedule
    beat_schedule={
        # Appointment reminders - 9 AM daily
        'send-appointment-reminders': {
            'task': 'apps.appointments.tasks.send_appointment_reminder',
            'schedule': crontab(hour=9, minute=0),
        },

        # Cleanup tokens - 3 AM daily
        'cleanup-tokens': {
            'task': 'apps.core.tasks.cleanup_expired_tokens',
            'schedule': crontab(hour=3, minute=0),
        },

        # Refresh dashboard cache - every 5 minutes
        'refresh-dashboard-cache': {
            'task': 'apps.core.tasks.calculate_dashboard_cache',
            'schedule': 300.0,
        },

        # Monthly accounting report - 1st day at midnight
        'monthly-accounting': {
            'task': 'apps.billing.tasks.generate_monthly_accounting_report',
            'schedule': crontab(day_of_month=1, hour=0, minute=0),
        },

        # Archive old lab orders - 2 AM daily
        'archive-old-lab-orders': {
            'task': 'apps.laboratory.tasks.archive_old_lab_orders',
            'schedule': crontab(hour=2, minute=0),
        },

        # Cleanup old audit logs - 1 AM on first day of month
        'cleanup-audit-logs': {
            'task': 'apps.core.tasks.cleanup_old_audit_logs',
            'schedule': crontab(day_of_month=1, hour=1, minute=0),
        },

        # Rotate certificates - 1st day at 1 AM
        'rotate-certificates': {
            'task': 'apps.core.tasks.rotate_certificates',
            'schedule': crontab(day_of_month=1, hour=1, minute=0),
        },

        # Database backup - 4 AM daily
        'backup-database': {
            'task': 'apps.core.tasks.backup_database',
            'schedule': crontab(hour=4, minute=0),
        },
    }
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
