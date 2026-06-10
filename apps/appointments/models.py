import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class DoctorAvailability(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.IntegerField(choices=[
        (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'),
        (3, 'Jeudi'), (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche'),
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'doctor_availabilities'


class Appointment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        CONFIRMED = 'CONFIRMED', 'Confirme'
        CANCELLED = 'CANCELLED', 'Annule'
        COMPLETED = 'COMPLETED', 'Termine'
        NO_SHOW = 'NO_SHOW', 'Absent'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='appointments')
    doctor = models.ForeignKey('authentication.User', on_delete=models.PROTECT, related_name='appointments')
    appointment_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        db_table = 'appointments'
        ordering = ['appointment_date']
        indexes = [
            models.Index(fields=['doctor', 'appointment_date']),
            models.Index(fields=['patient', 'appointment_date']),
        ]

    def __str__(self):
        return f'RDV {self.id} - {self.patient} avec {self.doctor} le {self.appointment_date}'
