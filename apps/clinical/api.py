from typing import List
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination

from apps.core.models import create_audit_log
from apps.authentication.permissions import require_permission
from .models import Consultation, Diagnosis, Prescription, PrescriptionItem
from .schemas import (
    ConsultationCreateSchema, ConsultationUpdateSchema, ConsultationOut, ConsultationDetailOut,
    DiagnosisSchema, DiagnosisOut,
    PrescriptionCreateSchema, PrescriptionOut,
)

router = Router()


def _get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR', '')


@router.post('/consultations', response=ConsultationOut)
@require_permission('clinical:write')
def create_consultation(request, payload: ConsultationCreateSchema):
    from apps.patients.models import Patient
    from django.contrib.auth import get_user_model
    User = get_user_model()

    patient = get_object_or_404(Patient, id=payload.patient_id)
    doctor = get_object_or_404(User, id=payload.doctor_id, role='DOCTOR')

    hosp = None
    if payload.hospitalization_id:
        from apps.hospitalization.models import Hospitalization
        hosp = get_object_or_404(Hospitalization, id=payload.hospitalization_id, patient=patient)

    consultation = Consultation.objects.create(
        patient=patient,
        doctor=doctor,
        hospitalization=hosp,
        consultation_date=payload.consultation_date,
        chief_complaint=payload.chief_complaint,
        anamnesis=payload.anamnesis or '',
        physical_exam=payload.physical_exam or '',
        notes=payload.notes or '',
    )
    create_audit_log(request.auth, 'CREATE', 'Consultation', resource_id=consultation.id, ip_address=_get_ip(request))
    return consultation


@router.get('/consultations', response=List[ConsultationOut])
@require_permission('clinical:read')
@paginate(PageNumberPagination)
def list_consultations(request, patient_id: str = '', doctor_id: str = ''):
    qs = Consultation.objects.all()
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    return qs


@router.get('/consultations/{consultation_id}', response=ConsultationDetailOut)
@require_permission('clinical:read')
def get_consultation(request, consultation_id: str):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    create_audit_log(request.auth, 'VIEW', 'Consultation', resource_id=consultation_id, ip_address=_get_ip(request))
    return {
        'id': consultation.id,
        'patient_id': consultation.patient_id,
        'doctor_id': consultation.doctor_id,
        'status': consultation.status,
        'consultation_date': consultation.consultation_date,
        'chief_complaint': consultation.chief_complaint,
        'anamnesis': consultation.anamnesis,
        'physical_exam': consultation.physical_exam,
        'notes': consultation.notes,
        'created_at': consultation.created_at,
        'diagnoses': list(consultation.diagnoses.all()),
        'prescriptions': [
            {**p.__dict__, 'items': list(p.items.all())}
            for p in consultation.prescriptions.all()
        ],
    }


@router.patch('/consultations/{consultation_id}', response=ConsultationOut)
@require_permission('clinical:write')
def update_consultation(request, consultation_id: str, payload: ConsultationUpdateSchema):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    for field, value in payload.dict(exclude_none=True).items():
        setattr(consultation, field, value)
    consultation.save()
    return consultation


@router.post('/consultations/{consultation_id}/diagnostics', response=DiagnosisOut)
@require_permission('clinical:write')
def add_diagnosis(request, consultation_id: str, payload: DiagnosisSchema):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    diag = Diagnosis.objects.create(
        consultation=consultation,
        icd10_code=payload.icd10_code,
        icd10_label=payload.icd10_label,
        diag_type=payload.diag_type,
        notes=payload.notes or '',
    )
    return diag


@router.post('/consultations/{consultation_id}/prescriptions', response=PrescriptionOut)
@require_permission('clinical:write')
def create_prescription(request, consultation_id: str, payload: PrescriptionCreateSchema):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    prescription = Prescription.objects.create(
        consultation=consultation,
        prescribed_by=request.auth,
        notes=payload.notes or '',
    )
    items = [
        PrescriptionItem(
            prescription=prescription,
            medication_name=item.medication_name,
            dosage=item.dosage,
            frequency=item.frequency,
            duration=item.duration,
            route=item.route or '',
            instructions=item.instructions or '',
            quantity=item.quantity,
        )
        for item in payload.items
    ]
    PrescriptionItem.objects.bulk_create(items)
    create_audit_log(request.auth, 'CREATE', 'Prescription', resource_id=prescription.id, ip_address=_get_ip(request))
    return {
        'id': prescription.id,
        'status': prescription.status,
        'notes': prescription.notes,
        'validated_at': prescription.validated_at,
        'created_at': prescription.created_at,
        'items': list(prescription.items.all()),
    }


@router.post('/prescriptions/{prescription_id}/valider')
@require_permission('clinical:write')
def validate_prescription(request, prescription_id: str):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    if prescription.status != 'DRAFT':
        raise HttpError(400, 'Seule une ordonnance en brouillon peut etre validee')
    if request.auth.role not in ('DOCTOR', 'ADMIN'):
        raise HttpError(403, 'Seul un medecin peut valider une ordonnance')
    try:
        prescription.validate()
    except ValueError as e:
        raise HttpError(400, str(e))
    create_audit_log(
        request.auth, 'VALIDATE', 'Prescription',
        resource_id=prescription_id, ip_address=_get_ip(request)
    )
    return {'detail': 'Ordonnance validee', 'status': prescription.status}
