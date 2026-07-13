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
from .models import Building, Department, Room, Bed, Hospitalization, Transfer
from .schemas import (
    BuildingSchema, BuildingOut, DepartmentSchema, DepartmentOut,
    RoomSchema, RoomOut, BedSchema, BedOut,
    HospitalizationCreateSchema, HospitalizationOut,
    DischargeSchema, TransferSchema, TransferOut,
)

router = Router()


def _get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR', '')


# --- Bâtiments ---
@router.post('/batiments', response=BuildingOut)
@require_permission('hospitalization:write')
def create_building(request, payload: BuildingSchema):
    b = Building.objects.create(name=payload.name, description=payload.description or '')
    return b


@router.get('/batiments', response=List[BuildingOut])
@require_permission('hospitalization:read')
def list_buildings(request):
    return list(Building.objects.filter(is_active=True))


# --- Services ---
@router.post('/services', response=DepartmentOut)
@require_permission('hospitalization:write')
def create_department(request, payload: DepartmentSchema):
    building = get_object_or_404(Building, id=payload.building_id)
    dept = Department.objects.create(
        building=building,
        name=payload.name,
        code=payload.code,
        head_doctor_id=payload.head_doctor_id,
    )
    return dept


@router.get('/services', response=List[DepartmentOut])
@require_permission('hospitalization:read')
def list_departments(request, building_id: str = ''):
    qs = Department.objects.filter(is_active=True)
    if building_id:
        qs = qs.filter(building_id=building_id)
    return list(qs)


# --- Chambres ---
@router.post('/chambres', response=RoomOut)
@require_permission('hospitalization:write')
def create_room(request, payload: RoomSchema):
    dept = get_object_or_404(Department, id=payload.department_id)
    room = Room.objects.create(
        department=dept,
        number=payload.number,
        room_type=payload.room_type,
        floor=payload.floor,
    )
    return room


@router.get('/chambres', response=List[RoomOut])
@require_permission('hospitalization:read')
def list_rooms(request, department_id: str = ''):
    qs = Room.objects.filter(is_active=True)
    if department_id:
        qs = qs.filter(department_id=department_id)
    return list(qs)


# --- Lits ---
@router.post('/lits', response=BedOut)
@require_permission('hospitalization:write')
def create_bed(request, payload: BedSchema):
    room = get_object_or_404(Room, id=payload.room_id)
    bed = Bed.objects.create(room=room, number=payload.number)
    return bed


@router.get('/lits', response=List[BedOut])
@require_permission('hospitalization:read')
def list_beds(request, room_id: str = '', status: str = ''):
    qs = Bed.objects.filter(is_active=True)
    if room_id:
        qs = qs.filter(room_id=room_id)
    if status:
        qs = qs.filter(status=status)
    return list(qs)


@router.get('/lits/disponibles', response=List[BedOut])
@require_permission('hospitalization:read')
def available_beds(request, department_id: str = ''):
    qs = Bed.objects.filter(is_active=True, status='AVAILABLE')
    if department_id:
        qs = qs.filter(room__department_id=department_id)
    return list(qs)


# --- Hospitalisations ---
@router.post('/admissions', response=HospitalizationOut)
@require_permission('hospitalization:write')
def admit_patient(request, payload: HospitalizationCreateSchema):
    from apps.patients.models import Patient
    from django.contrib.auth import get_user_model
    User = get_user_model()

    bed = get_object_or_404(Bed, id=payload.bed_id, is_active=True)
    if not bed.is_available():
        raise HttpError(409, 'Ce lit est deja occupe ou indisponible')

    patient = get_object_or_404(Patient, id=payload.patient_id)
    doctor = get_object_or_404(User, id=payload.referring_doctor_id)

    active_hosp = Hospitalization.objects.filter(patient=patient, status='ACTIVE').exists()
    if active_hosp:
        raise HttpError(409, 'Ce patient est deja hospitalise')

    with transaction.atomic():
        hosp = Hospitalization(
            patient=patient,
            bed=bed,
            referring_doctor=doctor,
            admission_date=payload.admission_date,
            expected_discharge_date=payload.expected_discharge_date,
            admission_reason=payload.admission_reason,
            notes=payload.notes or '',
        )
        hosp.save()

    create_audit_log(request.auth, 'CREATE', 'Hospitalization', resource_id=hosp.id, ip_address=_get_ip(request))
    return hosp


@router.get('/admissions', response=List[HospitalizationOut])
@require_permission('hospitalization:read')
@paginate(SGHLPagination)
def list_hospitalizations(request, status: str = 'ACTIVE', patient_id: str = ''):
    qs = Hospitalization.objects.all()
    if status:
        qs = qs.filter(status=status)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    return qs


@router.get('/admissions/{hosp_id}', response=HospitalizationOut)
@require_permission('hospitalization:read')
def get_hospitalization(request, hosp_id: str):
    return get_object_or_404(Hospitalization, id=hosp_id)


@router.post('/admissions/{hosp_id}/sortie', response=HospitalizationOut)
@require_permission('hospitalization:write')
def discharge_patient(request, hosp_id: str, payload: DischargeSchema):
    hosp = get_object_or_404(Hospitalization, id=hosp_id, status='ACTIVE')
    with transaction.atomic():
        hosp.status = 'DISCHARGED'
        hosp.discharge_summary = payload.discharge_summary
        hosp.actual_discharge_date = payload.actual_discharge_date or timezone.now()
        hosp.save(update_fields=['status', 'discharge_summary', 'actual_discharge_date'])
        hosp.bed.status = 'AVAILABLE'
        hosp.bed.save(update_fields=['status'])
    create_audit_log(request.auth, 'UPDATE', 'Hospitalization', resource_id=hosp_id, ip_address=_get_ip(request))
    return hosp


@router.post('/admissions/{hosp_id}/transfert', response=TransferOut)
@require_permission('hospitalization:write')
def transfer_patient(request, hosp_id: str, payload: TransferSchema):
    hosp = get_object_or_404(Hospitalization, id=hosp_id, status='ACTIVE')
    new_bed = get_object_or_404(Bed, id=payload.to_bed_id, is_active=True)
    if not new_bed.is_available():
        raise HttpError(409, 'Le lit de destination est indisponible')

    with transaction.atomic():
        old_bed = hosp.bed
        transfer = Transfer.objects.create(
            hospitalization=hosp,
            from_bed=old_bed,
            to_bed=new_bed,
            transfer_date=payload.transfer_date or timezone.now(),
            reason=payload.reason,
            ordered_by=request.auth,
        )
        old_bed.status = 'AVAILABLE'
        old_bed.save(update_fields=['status'])
        new_bed.status = 'OCCUPIED'
        new_bed.save(update_fields=['status'])
        hosp.bed = new_bed
        hosp.save(update_fields=['bed'])

    create_audit_log(request.auth, 'UPDATE', 'Transfer', resource_id=transfer.id, ip_address=_get_ip(request))
    return transfer

