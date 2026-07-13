"""Appointments Celery tasks for reminders and notifications."""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('apps.appointments')


@shared_task(bind=True, max_retries=2)
def send_appointment_confirmation(self, appointment_id):
    """Send appointment confirmation email to patient."""
    try:
        from apps.appointments.models import Appointment

        appointment = Appointment.objects.get(id=appointment_id)
        patient = appointment.patient
        doctor = appointment.doctor

        if not patient.email:
            logger.warning(f'No email for patient {patient.id}')
            return {'status': 'skipped', 'reason': 'no_email'}

        subject = f'Confirmation de rendez-vous - {appointment.appointment_date.strftime("%d/%m/%Y %H:%M")}'
        message = f"""
Bonjour {patient.get_full_name()},

Votre rendez-vous a été confirmé:

Date: {appointment.appointment_date.strftime("%d/%m/%Y à %H:%M")}
Médecin: Dr. {doctor.get_full_name()}
Motif: {appointment.reason or 'Consultation'}

Lieu: SGHL - Urgences

Veuillez arriver 15 minutes avant l'heure du rendez-vous.

Cordialement,
L'équipe SGHL
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [patient.email],
            fail_silently=False,
        )

        logger.info(f'Appointment confirmation sent to {patient.email}')
        return {'status': 'success', 'appointment_id': str(appointment_id)}

    except Exception as exc:
        logger.error(f'send_appointment_confirmation failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=2)
def send_appointment_reminder(self):
    """Send appointment reminders to patients 24h before appointment."""
    try:
        from apps.appointments.models import Appointment

        now = timezone.now()
        tomorrow = now + timedelta(hours=24)

        # Find appointments in the next 24 hours
        appointments = Appointment.objects.filter(
            appointment_date__gte=now,
            appointment_date__lte=tomorrow,
            status='CONFIRMED',
            reminder_sent=False
        )

        sent_count = 0
        for appointment in appointments:
            patient = appointment.patient

            if not patient.email:
                continue

            subject = f'Rappel: Rendez-vous demain à {appointment.appointment_date.strftime("%H:%M")}'
            message = f"""
Bonjour {patient.get_full_name()},

Ceci est un rappel de votre rendez-vous demain:

Date: {appointment.appointment_date.strftime("%d/%m/%Y à %H:%M")}
Médecin: Dr. {appointment.doctor.get_full_name()}

Veuillez arriver 15 minutes avant l'heure du rendez-vous.

Cordialement,
L'équipe SGHL
            """

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [patient.email],
                    fail_silently=False,
                )
                appointment.reminder_sent = True
                appointment.save(update_fields=['reminder_sent'])
                sent_count += 1
            except Exception as e:
                logger.error(f'Failed to send reminder for appointment {appointment.id}: {str(e)}')

        logger.info(f'Sent {sent_count} appointment reminders')
        return {'status': 'success', 'reminders_sent': sent_count}

    except Exception as exc:
        logger.error(f'send_appointment_reminder failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=2)
def send_cancellation_notification(self, appointment_id):
    """Send appointment cancellation notification."""
    try:
        from apps.appointments.models import Appointment

        appointment = Appointment.objects.get(id=appointment_id)
        patient = appointment.patient

        if not patient.email:
            logger.warning(f'No email for patient {patient.id}')
            return {'status': 'skipped', 'reason': 'no_email'}

        subject = 'Annulation de rendez-vous - SGHL'
        message = f"""
Bonjour {patient.get_full_name()},

Votre rendez-vous du {appointment.appointment_date.strftime("%d/%m/%Y à %H:%M")}
avec Dr. {appointment.doctor.get_full_name()} a été annulé.

Pour prendre un nouveau rendez-vous, veuillez utiliser l'application SGHL.

Cordialement,
L'équipe SGHL
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [patient.email],
            fail_silently=False,
        )

        logger.info(f'Cancellation notification sent to {patient.email}')
        return {'status': 'success', 'appointment_id': str(appointment_id)}

    except Exception as exc:
        logger.error(f'send_cancellation_notification failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)
