import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TimeStampedModel


class Invoice(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Brouillon'
        ISSUED = 'ISSUED', 'Emise'
        PARTIALLY_PAID = 'PARTIALLY_PAID', 'Partiellement payee'
        PAID = 'PAID', 'Payee'
        CANCELLED = 'CANCELLED', 'Annulee'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='invoices')
    hospitalization = models.ForeignKey(
        'hospitalization.Hospitalization', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='invoices'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    insurance_coverage = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    insurance_provider = models.CharField(max_length=200, blank=True)
    insurance_claim_number = models.CharField(max_length=100, blank=True)
    issued_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='billing/invoices/', null=True, blank=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f'Facture {self.invoice_number}'

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self._generate_number()
        super().save(*args, **kwargs)

    def _generate_number(self):
        from django.utils import timezone
        year = timezone.now().year
        count = Invoice.objects.filter(created_at__year=year).count() + 1
        return f'FAC-{year}-{count:06d}'

    @property
    def balance_due(self):
        return self.total - self.amount_paid - self.insurance_coverage

    def recalculate(self):
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.total = self.subtotal - self.discount + self.tax
        self.save(update_fields=['subtotal', 'total'])

    def update_payment_status(self):
        if self.amount_paid + self.insurance_coverage >= self.total:
            self.status = self.Status.PAID
        elif self.amount_paid + self.insurance_coverage > 0:
            self.status = self.Status.PARTIALLY_PAID
        self.save(update_fields=['status'])


class InvoiceItem(models.Model):
    class ItemType(models.TextChoices):
        CONSULTATION = 'CONSULTATION', 'Consultation'
        HOSPITALIZATION = 'HOSPITALIZATION', 'Nuitee'
        LAB = 'LAB', 'Examen labo'
        MEDICATION = 'MEDICATION', 'Medicament'
        PROCEDURE = 'PROCEDURE', 'Acte medical'
        SUPPLY = 'SUPPLY', 'Consommable'
        OTHER = 'OTHER', 'Autre'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    description = models.CharField(max_length=500)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'))
    reference_id = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'invoice_items'

    @property
    def total_price(self):
        base = self.quantity * self.unit_price
        return base * (1 - self.discount_percent / 100)


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = 'CASH', 'Especes'
        CARD = 'CARD', 'Carte'
        MOBILE = 'MOBILE', 'Mobile Money'
        INSURANCE = 'INSURANCE', 'Assurance'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Virement'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invoice.amount_paid = self.invoice.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        self.invoice.update_payment_status()


class AccountingEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry_type = models.CharField(max_length=20, choices=[
        ('DEBIT', 'Debit'), ('CREDIT', 'Credit'),
    ])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=100, blank=True)
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL)
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounting_entries'
        ordering = ['-timestamp']
