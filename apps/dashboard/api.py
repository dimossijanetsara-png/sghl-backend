from ninja import Router
from django.core.cache import cache
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

from apps.authentication.permissions import require_permission

router = Router()

CACHE_TTL = 60  # secondes


@router.get('/kpis')
@require_permission('dashboard:read')
def get_kpis(request):
    cache_key = 'dashboard_kpis'
    cached = cache.get(cache_key)
    if cached:
        return cached

    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)

    from apps.hospitalization.models import Bed, Hospitalization
    from apps.laboratory.models import LabOrder
    from apps.billing.models import Invoice
    from apps.appointments.models import Appointment

    total_beds = Bed.objects.filter(is_active=True).count()
    occupied_beds = Bed.objects.filter(is_active=True, status='OCCUPIED').count()
    occupancy_rate = round((occupied_beds / total_beds * 100), 1) if total_beds else 0

    monthly_revenue = Invoice.objects.filter(
        status__in=['PARTIALLY_PAID', 'PAID'],
        created_at__date__gte=month_start,
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    pending_lab = LabOrder.objects.filter(
        status__in=['ORDERED', 'SAMPLED', 'ASSIGNED', 'IN_PROGRESS']
    ).count()

    today_appointments = Appointment.objects.filter(
        appointment_date__date=today,
        status__in=['PENDING', 'CONFIRMED'],
    ).count()

    active_hospitalizations = Hospitalization.objects.filter(status='ACTIVE').count()

    kpis = {
        'total_beds': total_beds,
        'occupied_beds': occupied_beds,
        'available_beds': total_beds - occupied_beds,
        'occupancy_rate': occupancy_rate,
        'active_hospitalizations': active_hospitalizations,
        'monthly_revenue': float(monthly_revenue),
        'pending_lab_orders': pending_lab,
        'today_appointments': today_appointments,
        'generated_at': now.isoformat(),
    }

    cache.set(cache_key, kpis, CACHE_TTL)
    return kpis


@router.get('/statistiques/hospitalisations')
@require_permission('dashboard:read')
def hospitalization_stats(request, days: int = 30):
    cache_key = f'hosp_stats_{days}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    from apps.hospitalization.models import Hospitalization, Department
    since = timezone.now() - timedelta(days=days)

    by_dept = list(
        Hospitalization.objects.filter(created_at__gte=since)
        .values('bed__room__department__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    by_status = list(
        Hospitalization.objects.filter(created_at__gte=since)
        .values('status')
        .annotate(count=Count('id'))
    )

    result = {'by_department': by_dept, 'by_status': by_status, 'period_days': days}
    cache.set(cache_key, result, CACHE_TTL)
    return result


@router.get('/statistiques/revenus')
@require_permission('dashboard:read')
def revenue_stats(request, days: int = 30):
    from apps.billing.models import Invoice, Payment
    since = timezone.now() - timedelta(days=days)

    total_invoiced = Invoice.objects.filter(
        created_at__gte=since, status__in=['ISSUED', 'PARTIALLY_PAID', 'PAID']
    ).aggregate(total=Sum('total'))['total'] or 0

    total_collected = Payment.objects.filter(
        created_at__gte=since
    ).aggregate(total=Sum('amount'))['total'] or 0

    return {
        'total_invoiced': float(total_invoiced),
        'total_collected': float(total_collected),
        'collection_rate': round(float(total_collected) / float(total_invoiced) * 100, 1) if total_invoiced else 0,
        'period_days': days,
    }
