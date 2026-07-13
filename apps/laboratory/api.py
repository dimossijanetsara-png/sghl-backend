from typing import List
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from apps.core.pagination import SGHLPagination

from apps.core.models import create_audit_log
from apps.authentication.permissions import require_permission
from apps.authentication.patient_utils import enforce_patient_filter, assert_patient_owns
from .models import LabTest, LabOrder, LabOrderItem, LabOrderAudit
from .schemas import (
    LabTestOut, LabOrderCreateSchema, LabOrderOut,
    ResultEntrySchema, AssignSchema,
)

router = Router()


def _get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR', '')


def _audit(order, user, action, notes=''):
    LabOrderAudit.objects.create(
        order=order,
        action=action,
        performed_by=user,
        new_status=order.status,
        notes=notes,
    )


def _order_to_dict(order):
    return {
        'id': order.id,
        'patient_id': order.patient_id,
        'ordered_by_id': order.ordered_by_id,
        'status': order.status,
        'priority': order.priority,
        'clinical_notes': order.clinical_notes,
        'sampled_at': order.sampled_at,
        'validated_at': order.validated_at,
        'published_at': order.published_at,
        'created_at': order.created_at,
        'items': list(order.items.all()),
    }


@router.get('/analyses', response=List[LabTestOut])
@require_permission('laboratory:read')
def list_tests(request):
    return list(LabTest.objects.filter(is_active=True))


@router.post('/commandes', response=LabOrderOut)
@require_permission('laboratory:write')
def create_order(request, payload: LabOrderCreateSchema):
    from apps.patients.models import Patient
    patient = get_object_or_404(Patient, id=payload.patient_id)

    tests = list(LabTest.objects.filter(id__in=payload.test_ids, is_active=True))
    if len(tests) != len(payload.test_ids):
        raise HttpError(400, 'Un ou plusieurs tests sont invalides')

    with transaction.atomic():
        order = LabOrder.objects.create(
            patient=patient,
            ordered_by=request.auth,
            hospitalization_id=payload.hospitalization_id,
            consultation_id=payload.consultation_id,
            priority=payload.priority,
            clinical_notes=payload.clinical_notes or '',
        )
        items = [LabOrderItem(order=order, test=t) for t in tests]
        LabOrderItem.objects.bulk_create(items)
        _audit(order, request.auth, 'CREATE')

    create_audit_log(request.auth, 'CREATE', 'LabOrder', resource_id=order.id, ip_address=_get_ip(request))
    return _order_to_dict(order)


@router.get('/commandes', response=List[LabOrderOut])
@require_permission('laboratory:read')
@paginate(SGHLPagination)
def list_orders(request, status: str = '', patient_id: str = ''):
    qs = LabOrder.objects.prefetch_related('items').all()
    # PATIENT : uniquement ses propres analyses
    qs = enforce_patient_filter(request, qs)
    if status:
        qs = qs.filter(status=status)
    if patient_id and request.auth.role != 'PATIENT':
        qs = qs.filter(patient_id=patient_id)
    return [_order_to_dict(o) for o in qs]


@router.get('/commandes/{order_id}', response=LabOrderOut)
@require_permission('laboratory:read')
def get_order(request, order_id: str):
    order = get_object_or_404(LabOrder, id=order_id)
    # PATIENT : uniquement ses propres analyses
    assert_patient_owns(request, order)
    return _order_to_dict(order)


@router.post('/commandes/{order_id}/prelever')
@require_permission('laboratory:write')
def mark_sampled(request, order_id: str):
    order = get_object_or_404(LabOrder, id=order_id, status='ORDERED')
    order.status = 'SAMPLED'
    order.sampled_at = timezone.now()
    order.save(update_fields=['status', 'sampled_at'])
    _audit(order, request.auth, 'SAMPLE')
    return {'detail': 'Prelevement enregistre'}


@router.post('/commandes/{order_id}/affecter')
@require_permission('laboratory:write')
def assign_order(request, order_id: str, payload: AssignSchema):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    order = get_object_or_404(LabOrder, id=order_id, status='SAMPLED')
    biologist = get_object_or_404(User, id=payload.biologist_id, role='BIOLOGIST')
    order.assigned_to = biologist
    order.status = 'ASSIGNED'
    order.save(update_fields=['assigned_to', 'status'])
    _audit(order, request.auth, 'ASSIGN')
    return {'detail': 'Commande affectee'}


@router.post('/commandes/{order_id}/resultats')
@require_permission('laboratory:write')
def enter_results(request, order_id: str, results: List[ResultEntrySchema]):
    order = get_object_or_404(LabOrder, id=order_id)
    if order.status in ('VALIDATED', 'PUBLISHED'):
        raise HttpError(400, 'Resultat valide = immuable')

    with transaction.atomic():
        for r in results:
            item = get_object_or_404(LabOrderItem, id=r.item_id, order=order)
            item.result_value = r.result_value
            item.result_unit = r.result_unit or ''
            item.is_abnormal = r.is_abnormal
            item.notes = r.notes or ''
            item.resulted_at = timezone.now()
            item.save()
        order.status = 'RESULTED'
        order.save(update_fields=['status'])
        _audit(order, request.auth, 'ENTER_RESULTS')

    return {'detail': 'Resultats enregistres'}


@router.post('/commandes/{order_id}/valider')
@require_permission('laboratory:validate')
def validate_order(request, order_id: str):
    if request.auth.role != 'BIOLOGIST':
        raise HttpError(403, 'Seul un biologiste peut valider')
    order = get_object_or_404(LabOrder, id=order_id, status='RESULTED')

    with transaction.atomic():
        order.status = 'VALIDATED'
        order.validated_at = timezone.now()
        order.validated_by = request.auth
        order.save(update_fields=['status', 'validated_at', 'validated_by'])
        _audit(order, request.auth, 'VALIDATE')

    create_audit_log(request.auth, 'VALIDATE', 'LabOrder', resource_id=order_id, ip_address=_get_ip(request))
    return {'detail': 'Commande validee'}


@router.post('/commandes/{order_id}/publier')
@require_permission('laboratory:validate')
def publish_order(request, order_id: str):
    order = get_object_or_404(LabOrder, id=order_id, status='VALIDATED')
    order.status = 'PUBLISHED'
    order.published_at = timezone.now()
    order.save(update_fields=['status', 'published_at'])
    _audit(order, request.auth, 'PUBLISH')
    return {'detail': 'Resultats publies'}

