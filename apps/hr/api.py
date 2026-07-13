from typing import List
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate
from apps.core.pagination import SGHLPagination

from apps.authentication.permissions import require_permission
from .models import StaffProfile, Shift
from .schemas import StaffProfileOut, StaffCreateSchema, ShiftCreateSchema, ShiftOut

router = Router()


@router.post('/personnel', response=StaffProfileOut)
@require_permission('hr:write')
def create_staff(request, payload: StaffCreateSchema):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = get_object_or_404(User, id=payload.user_id)
    staff = StaffProfile.objects.create(
        user=user,
        department_id=payload.department_id,
        employee_number=payload.employee_number,
        specialization=payload.specialization or '',
        license_number=payload.license_number or '',
        hire_date=payload.hire_date,
    )
    return staff


@router.get('/personnel', response=List[StaffProfileOut])
@require_permission('hr:read')
@paginate(SGHLPagination)
def list_staff(request, department_id: str = '', role: str = ''):
    qs = StaffProfile.objects.select_related('user').filter(is_active=True)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if role:
        qs = qs.filter(user__role=role)
    return qs


@router.post('/gardes', response=ShiftOut)
@require_permission('hr:write')
def create_shift(request, payload: ShiftCreateSchema):
    staff = get_object_or_404(StaffProfile, id=payload.staff_id)
    shift = Shift.objects.create(
        staff=staff,
        department_id=payload.department_id,
        shift_type=payload.shift_type,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        notes=payload.notes or '',
    )
    return shift


@router.get('/gardes', response=List[ShiftOut])
@require_permission('hr:read')
@paginate(SGHLPagination)
def list_shifts(request, department_id: str = '', staff_id: str = ''):
    qs = Shift.objects.all()
    if department_id:
        qs = qs.filter(department_id=department_id)
    if staff_id:
        qs = qs.filter(staff_id=staff_id)
    return qs


@router.patch('/gardes/{shift_id}/confirmer', response=ShiftOut)
@require_permission('hr:write')
def confirm_shift(request, shift_id: str):
    shift = get_object_or_404(Shift, id=shift_id)
    shift.is_confirmed = True
    shift.save(update_fields=['is_confirmed'])
    return shift

