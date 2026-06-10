import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Careplan(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Actif'
        COMPLETED = 'COMPLETED', 'Termine'
        CANCELLED = 'CANCELLED', 'Annule'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        'hospitalization.Hospitalization', on_delete=models.CASCADE, related_name='careplans'
    )
    created_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    goals = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'careplans'


class CareTask(TimeStampedModel):
    class Frequency(models.TextChoices):
        ONCE = 'ONCE', 'Une fois'
        DAILY = 'DAILY', 'Quotidien'
        BID = 'BID', '2x/jour'
        TID = 'TID', '3x/jour'
        QID = 'QID', '4x/jour'
        PRN = 'PRN', 'Si besoin'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        DONE = 'DONE', 'Effectue'
        MISSED = 'MISSED', 'Manque'
        SKIPPED = 'SKIPPED', 'Ignore'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    careplan = models.ForeignKey(Careplan, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.DAILY)
    scheduled_time = models.TimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='care_tasks'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    done_at = models.DateTimeField(null=True, blank=True)
    done_by = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='completed_tasks'
    )
    notes = models.TextField(blank=True)
    prescription_item = models.ForeignKey(
        'clinical.PrescriptionItem', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='care_tasks'
    )

    class Meta:
        db_table = 'care_tasks'
        ordering = ['scheduled_time']


class VitalSign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        'hospitalization.Hospitalization', on_delete=models.CASCADE, related_name='vital_signs'
    )
    recorded_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    recorded_at = models.DateTimeField()
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    systolic_bp = models.PositiveIntegerField(null=True, blank=True)
    diastolic_bp = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    oxygen_saturation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pain_score = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'vital_signs'
        ordering = ['-recorded_at']
        indexes = [models.Index(fields=['hospitalization', 'recorded_at'])]


class NursingNote(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(
        'hospitalization.Hospitalization', on_delete=models.CASCADE, related_name='nursing_notes'
    )
    written_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    content = models.TextField()
    category = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'nursing_notes'
        ordering = ['-created_at']
