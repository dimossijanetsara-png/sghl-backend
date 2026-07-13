from typing import List
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, File
from ninja.files import UploadedFile
from ninja.errors import HttpError
from ninja.pagination import paginate
from apps.core.pagination import SGHLPagination

from apps.core.models import create_audit_log
from apps.authentication.permissions import require_permission
from .models import Patient, PatientDocument
from .schemas import PatientCreateSchema, PatientUpdateSchema, PatientOut, PatientListOut, DocumentOut

router = Router()

ALLOWED_MIME_TYPES = ['application/pdf', 'image/jpeg', 'image/png']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR', '')


@router.post('', response=PatientOut)
@require_permission('patients:write')
def create_patient(request, payload: PatientCreateSchema):
    if payload.consent_given:
        consent_date = timezone.now()
    else:
        consent_date = None
    patient = Patient.objects.create(
        **payload.dict(exclude={'consent_given'}),
        consent_given=payload.consent_given,
        consent_date=consent_date,
    )
    create_audit_log(request.auth, 'CREATE', 'Patient', resource_id=patient.id, ip_address=_get_ip(request))
    return patient


@router.get('', response=List[PatientListOut])
@require_permission('patients:read')
@paginate(SGHLPagination)
def list_patients(request, search: str = '', archived: bool = False):
    qs = Patient.objects.filter(is_archived=archived)
    if search:
        qs = qs.filter(
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(record_number__icontains=search) |
            models.Q(national_id__icontains=search)
        )
    return qs


@router.get('/{patient_id}', response=PatientOut)
@require_permission('patients:read')
def get_patient(request, patient_id: str):
    patient = get_object_or_404(Patient, id=patient_id)
    create_audit_log(request.auth, 'VIEW', 'Patient', resource_id=patient_id, ip_address=_get_ip(request))
    return patient


@router.patch('/{patient_id}', response=PatientOut)
@require_permission('patients:write')
def update_patient(request, patient_id: str, payload: PatientUpdateSchema):
    patient = get_object_or_404(Patient, id=patient_id)
    old_data = {f: getattr(patient, f) for f in payload.dict(exclude_none=True)}
    for field, value in payload.dict(exclude_none=True).items():
        setattr(patient, field, value)
    patient.save()
    create_audit_log(
        request.auth, 'UPDATE', 'Patient', resource_id=patient_id,
        old_value=old_data, new_value=payload.dict(exclude_none=True),
        ip_address=_get_ip(request)
    )
    return patient


@router.delete('/{patient_id}/archive')
@require_permission('patients:delete')
def archive_patient(request, patient_id: str):
    patient = get_object_or_404(Patient, id=patient_id)
    patient.is_archived = True
    patient.archived_at = timezone.now()
    patient.save(update_fields=['is_archived', 'archived_at'])
    create_audit_log(request.auth, 'DELETE', 'Patient', resource_id=patient_id, ip_address=_get_ip(request))
    return {'detail': 'Patient archivé'}


@router.post('/{patient_id}/consentement')
@require_permission('patients:write')
def update_consent(request, patient_id: str, consent: bool):
    patient = get_object_or_404(Patient, id=patient_id)
    patient.consent_given = consent
    patient.consent_date = timezone.now() if consent else None
    patient.save(update_fields=['consent_given', 'consent_date'])
    return {'detail': 'Consentement mis à jour', 'consent_given': consent}


@router.post('/{patient_id}/documents', response=DocumentOut)
@require_permission('patients:write')
def upload_document(
    request, patient_id: str,
    doc_type: str, title: str,
    file: UploadedFile = File(...),
    description: str = '',
):
    patient = get_object_or_404(Patient, id=patient_id)
    content_type = file.content_type or ''
    if content_type not in ALLOWED_MIME_TYPES:
        raise HttpError(400, f'Type de fichier non autorisé: {content_type}')
    if file.size > MAX_FILE_SIZE:
        raise HttpError(400, 'Fichier trop volumineux (max 10MB)')

    doc = PatientDocument.objects.create(
        patient=patient,
        doc_type=doc_type,
        title=title,
        file=file,
        mime_type=content_type,
        file_size=file.size,
        uploaded_by=request.auth,
        description=description,
    )
    create_audit_log(request.auth, 'CREATE', 'PatientDocument', resource_id=doc.id, ip_address=_get_ip(request))
    return doc


@router.get('/{patient_id}/documents', response=List[DocumentOut])
@require_permission('patients:read')
def list_documents(request, patient_id: str):
    patient = get_object_or_404(Patient, id=patient_id)
    return list(patient.documents.all())


# Import manquant pour Q
from django.db import models

