from typing import List
from django.shortcuts import get_object_or_404
from django.db import transaction
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination

from apps.core.models import create_audit_log
from apps.authentication.permissions import require_permission
from .models import Medication, MedicationBatch, StockMovement, Dispensation, DispensationItem
from .schemas import MedicationOut, BatchCreateSchema, BatchOut, DispensationCreateSchema, DispensationOut, StockMovementOut

router = Router()


def _get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR', '')


@router.get('/medicaments', response=List[MedicationOut])
@require_permission('pharmacy:read')
@paginate(PageNumberPagination)
def list_medications(request, search: str = '', low_stock: bool = False):
    qs = Medication.objects.filter(is_active=True)
    if search:
        qs = qs.filter(name__icontains=search)
    meds = list(qs)
    if low_stock:
        meds = [m for m in meds if m.is_low_stock()]
    return meds


@router.get('/medicaments/{med_id}', response=MedicationOut)
@require_permission('pharmacy:read')
def get_medication(request, med_id: str):
    return get_object_or_404(Medication, id=med_id)


@router.post('/lots', response=BatchOut)
@require_permission('pharmacy:write')
def receive_batch(request, payload: BatchCreateSchema):
    med = get_object_or_404(Medication, id=payload.medication_id)
    with transaction.atomic():
        batch = MedicationBatch.objects.create(
            medication=med,
            batch_number=payload.batch_number,
            quantity=payload.quantity,
            expiry_date=payload.expiry_date,
            supplier=payload.supplier or '',
            purchase_price=payload.purchase_price or 0,
            received_at=payload.received_at,
        )
        StockMovement.objects.create(
            batch=batch,
            movement_type='IN',
            quantity=payload.quantity,
            reference=f'Reception lot {payload.batch_number}',
            performed_by=request.auth,
        )
    create_audit_log(request.auth, 'CREATE', 'MedicationBatch', resource_id=batch.id, ip_address=_get_ip(request))
    return batch


@router.get('/lots', response=List[BatchOut])
@require_permission('pharmacy:read')
def list_batches(request, medication_id: str = '', expiring_soon: bool = False):
    from django.utils import timezone
    from datetime import timedelta
    qs = MedicationBatch.objects.filter(is_active=True, quantity__gt=0)
    if medication_id:
        qs = qs.filter(medication_id=medication_id)
    if expiring_soon:
        limit = timezone.now().date() + timedelta(days=30)
        qs = qs.filter(expiry_date__lte=limit)
    return list(qs)


@router.post('/dispensations', response=DispensationOut)
@require_permission('pharmacy:write')
def dispense(request, payload: DispensationCreateSchema):
    from apps.clinical.models import Prescription
    prescription = get_object_or_404(Prescription, id=payload.prescription_id, status='VALIDATED')

    with transaction.atomic():
        dispensation = Dispensation.objects.create(
            prescription=prescription,
            dispensed_by=request.auth,
            notes=payload.notes or '',
        )
        for item_data in payload.items:
            batch = get_object_or_404(MedicationBatch, id=item_data.batch_id, is_active=True)
            if batch.quantity < item_data.quantity:
                raise HttpError(400, f'Stock insuffisant pour le lot {batch.batch_number}')
            DispensationItem.objects.create(
                dispensation=dispensation,
                batch=batch,
                prescription_item_id=item_data.prescription_item_id,
                quantity=item_data.quantity,
            )
            batch.quantity -= item_data.quantity
            batch.save(update_fields=['quantity'])
            StockMovement.objects.create(
                batch=batch,
                movement_type='OUT',
                quantity=-item_data.quantity,
                reference=f'Dispensation {dispensation.id}',
                performed_by=request.auth,
            )
        prescription.status = 'DISPENSED'
        prescription.save(update_fields=['status'])

    create_audit_log(request.auth, 'CREATE', 'Dispensation', resource_id=dispensation.id, ip_address=_get_ip(request))
    return dispensation


@router.get('/mouvements', response=List[StockMovementOut])
@require_permission('pharmacy:read')
@paginate(PageNumberPagination)
def list_movements(request, medication_id: str = ''):
    qs = StockMovement.objects.all()
    if medication_id:
        qs = qs.filter(batch__medication_id=medication_id)
    return qs


@router.get('/alertes/rupture', response=List[MedicationOut])
@require_permission('pharmacy:read')
def low_stock_alerts(request):
    meds = Medication.objects.filter(is_active=True)
    return [m for m in meds if m.is_low_stock()]
