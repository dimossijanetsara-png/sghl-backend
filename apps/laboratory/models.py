import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class LabTest(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    normal_range = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    turnaround_hours = models.PositiveIntegerField(default=24)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'lab_tests'

    def __str__(self):
        return f'{self.code} - {self.name}'


class LabOrder(TimeStampedModel):
    class Status(models.TextChoices):
        ORDERED = 'ORDERED', 'Commande'
        SAMPLED = 'SAMPLED', 'Preleve'
        ASSIGNED = 'ASSIGNED', 'Affecte'
        IN_PROGRESS = 'IN_PROGRESS', 'En cours'
        RESULTED = 'RESULTED', 'Resultat saisi'
        VALIDATED = 'VALIDATED', 'Valide'
        PUBLISHED = 'PUBLISHED', 'Publie'
        CANCELLED = 'CANCELLED', 'Annule'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='lab_orders')
    ordered_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT, related_name='lab_orders_created')
    hospitalization = models.ForeignKey(
        'hospitalization.Hospitalization', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='lab_orders'
    )
    consultation = models.ForeignKey(
        'clinical.Consultation', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='lab_orders'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ORDERED)
    priority = models.CharField(max_length=10, default='NORMAL', choices=[
        ('URGENT', 'Urgent'), ('NORMAL', 'Normal'), ('ROUTINE', 'Routine'),
    ])
    clinical_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='assigned_lab_orders'
    )
    sampled_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='validated_lab_orders'
    )
    published_at = models.DateTimeField(null=True, blank=True)
    report_file = models.FileField(upload_to='laboratory/reports/', null=True, blank=True)

    class Meta:
        db_table = 'lab_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'Order {self.id} - {self.patient} - {self.status}'


class LabOrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='items')
    test = models.ForeignKey(LabTest, on_delete=models.PROTECT)
    result_value = models.TextField(blank=True)
    result_unit = models.CharField(max_length=50, blank=True)
    is_abnormal = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    resulted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lab_order_items'
        unique_together = [['order', 'test']]


class LabOrderAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='audit_trail')
    action = models.CharField(max_length=50)
    performed_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lab_order_audits'
        ordering = ['-timestamp']
