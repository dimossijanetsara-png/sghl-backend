import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Consultation(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Planifiee'
        IN_PROGRESS = 'IN_PROGRESS', 'En cours'
        COMPLETED = 'COMPLETED', 'Terminee'
        CANCELLED = 'CANCELLED', 'Annulee'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='consultations')
    doctor = models.ForeignKey('authentication.User', on_delete=models.PROTECT, related_name='consultations')
    hospitalization = models.ForeignKey(
        'hospitalization.Hospitalization', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='consultations'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    consultation_date = models.DateTimeField()
    chief_complaint = models.TextField()
    anamnesis = models.TextField(blank=True)
    physical_exam = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'consultations'
        ordering = ['-consultation_date']
        indexes = [
            models.Index(fields=['patient', 'consultation_date']),
            models.Index(fields=['doctor', 'consultation_date']),
        ]

    def __str__(self):
        return f'Consultation {self.id}'


class Diagnosis(TimeStampedModel):
    class DiagType(models.TextChoices):
        PRINCIPAL = 'PRINCIPAL', 'Principal'
        SECONDARY = 'SECONDARY', 'Secondaire'
        DIFFERENTIAL = 'DIFFERENTIAL', 'Differentiel'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='diagnoses')
    icd10_code = models.CharField(max_length=10)
    icd10_label = models.CharField(max_length=500)
    diag_type = models.CharField(max_length=20, choices=DiagType.choices, default=DiagType.PRINCIPAL)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'diagnoses'


class Prescription(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Brouillon'
        VALIDATED = 'VALIDATED', 'Validee'
        DISPENSED = 'DISPENSED', 'Dispensee'
        CANCELLED = 'CANCELLED', 'Annulee'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(Consultation, on_delete=models.PROTECT, related_name='prescriptions')
    prescribed_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT, related_name='prescriptions')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']

    def validate(self):
        from django.utils import timezone
        if self.status != self.Status.DRAFT:
            raise ValueError('Seule une ordonnance en brouillon peut etre validee')
        self.status = self.Status.VALIDATED
        self.validated_at = timezone.now()
        self.save(update_fields=['status', 'validated_at'])


class PrescriptionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    route = models.CharField(max_length=50, blank=True)
    instructions = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'prescription_items'
