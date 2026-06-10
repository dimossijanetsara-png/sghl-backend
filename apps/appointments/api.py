from typing import List
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate, PageNumberPagination

from apps.authentication.permissions import require_permission
from .models import Appointment, DoctorAvailability
from .schemas import (
    AppointmentCreateSchema, AppointmentOut, AppointmentUpdateSchema,
    AvailabilityCreateSchema, AvailabilityOut,
)

router = Router()


def _send_confirmation_email(appointment):
    try:
        send_mail(
            subject='Confirmation de votre rendez-vous - SGHL',
            message=(
                f'Bonjour {appointment.patient.get_full_name()},\n\n'
                f'Votre rendez-vous avec Dr {appointment.doctor.get_full_name()} '
                f'est confirme pour le {appointment.appointment_date.strftime("%d/%m/%Y a %H:%M")}.\n\n'
                f'Motif : {appointment.reason}\n\n'
                'Merci de votre confiance.\nEquipe SGHL'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.patient.email],
            fail_silently=True,
        )
    except Exception:
        pass


@router.post('/disponibilites', response=AvailabilityOut)
@require_permission('appointments:write')
def set_availability(request, payload: AvailabilityCreateSchema):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    doctor = get_object_or_404(User, id=payload.doctor_id, role='DOCTOR')
    avail, _ = DoctorAvailability.objects.get_or_create(
        doctor=doctor,
        day_of_week=payload.day_of_week,
        defaults={
            'start_time': payload.start_time,
            'end_time': payload.end_time,
            'slot_duration_minutes': payload.slot_duration_minutes,
        }
    )
    return avail


@router.get('/disponibilites/{doctor_id}', response=List[AvailabilityOut])
@require_permission('appointments:read')
def get_availability(request, doctor_id: str):
    return list(DoctorAvailability.objects.filter(doctor_id=doctor_id, is_active=True))


@router.post('', response=AppointmentOut)
@require_permission('appointments:write')
def create_appointment(request, payload: AppointmentCreateSchema):
    from apps.patients.models import Patient
    from django.contrib.auth import get_user_model
    User = get_user_model()

    patient = get_object_or_404(Patient, id=payload.patient_id)
    doctor = get_object_or_404(User, id=payload.doctor_id, role='DOCTOR')

    # Vérifier conflits
    conflict = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=payload.appointment_date,
        status__in=['PENDING', 'CONFIRMED'],
    ).exists()
    if conflict:
        raise HttpError(409, 'Ce creneau est deja pris')

    appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        appointment_date=payload.appointment_date,
        duration_minutes=payload.duration_minutes,
        reason=payload.reason,
        notes=payload.notes or '',
    )
    if patient.email:
        _send_confirmation_email(appointment)
    return appointment


@router.get('', response=List[AppointmentOut])
@require_permission('appointments:read')
@paginate(PageNumberPagination)
def list_appointments(request, doctor_id: str = '', patient_id: str = '', status: str = ''):
    qs = Appointment.objects.all()
    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if status:
        qs = qs.filter(status=status)
    return qs


@router.patch('/{appointment_id}', response=AppointmentOut)
@require_permission('appointments:write')
def update_appointment(request, appointment_id: str, payload: AppointmentUpdateSchema):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if payload.status:
        appointment.status = payload.status
    if payload.notes is not None:
        appointment.notes = payload.notes
    if payload.cancellation_reason:
        appointment.cancellation_reason = payload.cancellation_reason
    appointment.save()
    return appointment
