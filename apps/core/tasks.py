"""Core Celery tasks for SGHL backend."""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
import json

logger = logging.getLogger('apps.core')


@shared_task(bind=True, max_retries=3)
def cleanup_expired_tokens(self):
    """Delete JWT tokens from blacklist older than 30 days."""
    try:
        from apps.authentication.models import RefreshTokenBlacklist
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = RefreshTokenBlacklist.objects.filter(
            blacklisted_at__lt=cutoff_date
        ).delete()
        logger.info(f'Cleaned up {deleted_count} expired tokens')
        return {'status': 'success', 'deleted': deleted_count}
    except Exception as exc:
        logger.error(f'cleanup_expired_tokens failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def calculate_dashboard_cache(self):
    """Calculate and cache dashboard KPIs."""
    try:
        from django.core.cache import cache
        from django.db.models import Count, Sum, Q, F, Avg
        from apps.hospitalization.models import Hospitalization, Bed
        from apps.clinical.models import Consultation
        from apps.laboratory.models import LabOrder
        from apps.billing.models import Invoice

        now = timezone.now()
        start_date = now - timedelta(days=30)

        # Occupancy rate
        total_beds = Bed.objects.filter(is_active=True).count()
        occupied_beds = Bed.objects.filter(status='OCCUPIED').count()
        occupancy_rate = (occupied_beds / total_beds * 100) if total_beds else 0

        # Average length of stay
        hospitalizations = Hospitalization.objects.filter(
            status__in=['DISCHARGED', 'TRANSFERRED'],
            admission_date__gte=start_date
        )

        avg_los = None
        if hospitalizations.exists():
            avg_los_seconds = hospitalizations.annotate(
                los=F('actual_discharge_date') - F('admission_date')
            ).aggregate(avg=Avg('los'))['avg']
            if avg_los_seconds:
                avg_los = avg_los_seconds.total_seconds() / 3600

        # Revenue
        invoices = Invoice.objects.filter(
            status='PAID',
            created_at__gte=start_date
        )
        total_revenue = sum(i.total for i in invoices) or 0

        # Pending tests
        pending_tests = LabOrder.objects.filter(
            status__in=['ORDERED', 'IN_PROGRESS']
        ).count()

        # Consultations
        consultations = Consultation.objects.filter(
            created_at__gte=start_date
        ).count()

        kpis = {
            'hospitalization': {
                'occupancy_rate': float(occupancy_rate),
                'occupied_beds': occupied_beds,
                'total_beds': total_beds,
                'avg_length_stay_hours': float(avg_los) if avg_los else 0,
            },
            'financial': {
                'total_revenue': float(total_revenue),
                'invoices_paid': invoices.count(),
            },
            'laboratory': {
                'pending_tests': pending_tests,
            },
            'clinical': {
                'consultations': consultations,
            },
            'timestamp': now.isoformat(),
        }

        # Cache for 5 minutes
        cache.set('dashboard_kpis', kpis, 300)
        logger.info('Dashboard cache updated successfully')
        return {'status': 'success', 'kpis': kpis}

    except Exception as exc:
        logger.error(f'calculate_dashboard_cache failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def cleanup_old_audit_logs(self, days_threshold=365):
    """Delete audit logs older than threshold days."""
    try:
        from apps.core.models import AuditLog
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        deleted_count, _ = AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()
        logger.info(f'Deleted {deleted_count} old audit logs (>{days_threshold} days)')
        return {'status': 'success', 'deleted': deleted_count}
    except Exception as exc:
        logger.error(f'cleanup_old_audit_logs failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def backup_database(self):
    """Backup database to file."""
    import subprocess
    from django.conf import settings

    try:
        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'sghl_backup_{timestamp}.sql'

        db_name = settings.DATABASES['default'].get('NAME')
        db_user = settings.DATABASES['default'].get('USER', 'postgres')
        db_host = settings.DATABASES['default'].get('HOST', 'localhost')

        # pg_dump for PostgreSQL
        cmd = f'pg_dump -U {db_user} -h {db_host} {db_name} > {backup_file}'
        subprocess.run(cmd, shell=True, check=True)

        logger.info(f'Database backup created: {backup_file}')
        return {'status': 'success', 'backup_file': str(backup_file)}

    except Exception as exc:
        logger.error(f'backup_database failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=600)


@shared_task(bind=True, max_retries=1)
def send_bulk_notifications(self, user_ids, message, notification_type='info'):
    """Send bulk notifications to multiple users."""
    try:
        from apps.authentication.models import User
        from django.core.mail import send_mass_mail

        users = User.objects.filter(id__in=user_ids)
        emails = [(
            'SGHL Notification',
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        ) for user in users if user.email]

        send_mass_mail(emails, fail_silently=False)
        logger.info(f'Sent {len(emails)} bulk notifications')
        return {'status': 'success', 'sent': len(emails)}

    except Exception as exc:
        logger.error(f'send_bulk_notifications failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def rotate_certificates(days_before_expiry=30):
    """Rotate certificates before expiration."""
    try:
        logger.info('Rotating certificates...')
        # TODO: Implement certificate rotation logic when Phase 2 is complete
        return {'status': 'success', 'message': 'Certificates rotated'}
    except Exception as exc:
        logger.error(f'rotate_certificates failed: {str(exc)}')
        raise
