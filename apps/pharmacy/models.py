import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Medication(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=100)
    dosage_form = models.CharField(max_length=50)
    strength = models.CharField(max_length=50)
    unit = models.CharField(max_length=30)
    reorder_threshold = models.PositiveIntegerField(default=10)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'medications'

    def __str__(self):
        return f'{self.name} {self.strength}'

    @property
    def total_stock(self):
        return self.batches.filter(
            is_active=True, quantity__gt=0
        ).aggregate(total=models.Sum('quantity'))['total'] or 0

    def is_low_stock(self):
        return self.total_stock <= self.reorder_threshold


class MedicationBatch(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    supplier = models.CharField(max_length=200, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    received_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'medication_batches'
        ordering = ['expiry_date']

    def __str__(self):
        return f'{self.medication} - Lot {self.batch_number}'

    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        IN = 'IN', 'Entree'
        OUT = 'OUT', 'Sortie'
        ADJUSTMENT = 'ADJUSTMENT', 'Ajustement'
        RETURN = 'RETURN', 'Retour'
        EXPIRED = 'EXPIRED', 'Perime'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(MedicationBatch, on_delete=models.PROTECT, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField()
    reference = models.CharField(max_length=200, blank=True)
    performed_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_movements'
        ordering = ['-timestamp']


class Dispensation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey('clinical.Prescription', on_delete=models.PROTECT, related_name='dispensations')
    dispensed_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'dispensations'


class DispensationItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispensation = models.ForeignKey(Dispensation, on_delete=models.CASCADE, related_name='items')
    batch = models.ForeignKey(MedicationBatch, on_delete=models.PROTECT)
    prescription_item = models.ForeignKey('clinical.PrescriptionItem', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = 'dispensation_items'
