from typing import List
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.db import transaction
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from apps.core.pagination import SGHLPagination

from apps.core.models import create_audit_log
from apps.authentication.permissions import require_permission
from .models import Invoice, InvoiceItem, Payment, AccountingEntry
from .schemas import InvoiceCreateSchema, InvoiceOut, PaymentSchema, PaymentOut

router = Router()


def _get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR', '')


def _invoice_to_dict(invoice):
    return {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'patient_id': invoice.patient_id,
        'status': invoice.status,
        'subtotal': invoice.subtotal,
        'discount': invoice.discount,
        'tax': invoice.tax,
        'total': invoice.total,
        'amount_paid': invoice.amount_paid,
        'insurance_coverage': invoice.insurance_coverage,
        'balance_due': invoice.balance_due,
        'insurance_provider': invoice.insurance_provider,
        'notes': invoice.notes,
        'created_at': invoice.created_at,
        'items': list(invoice.items.all()),
    }


@router.post('/factures', response=InvoiceOut)
@require_permission('billing:write')
def create_invoice(request, payload: InvoiceCreateSchema):
    from apps.patients.models import Patient
    patient = get_object_or_404(Patient, id=payload.patient_id)

    with transaction.atomic():
        invoice = Invoice.objects.create(
            patient=patient,
            hospitalization_id=payload.hospitalization_id,
            discount=payload.discount,
            tax=payload.tax,
            insurance_coverage=payload.insurance_coverage,
            insurance_provider=payload.insurance_provider or '',
            insurance_claim_number=payload.insurance_claim_number or '',
            notes=payload.notes or '',
            issued_by=request.auth,
        )
        items = []
        for item_data in payload.items:
            items.append(InvoiceItem(
                invoice=invoice,
                item_type=item_data.item_type,
                description=item_data.description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                discount_percent=item_data.discount_percent,
                reference_id=item_data.reference_id or '',
            ))
        InvoiceItem.objects.bulk_create(items)
        invoice.recalculate()

        AccountingEntry.objects.create(
            entry_type='DEBIT',
            amount=invoice.total,
            description=f'Facture {invoice.invoice_number}',
            invoice=invoice,
        )

    create_audit_log(request.auth, 'CREATE', 'Invoice', resource_id=invoice.id, ip_address=_get_ip(request))
    return _invoice_to_dict(invoice)


@router.get('/factures', response=List[InvoiceOut])
@require_permission('billing:read')
@paginate(SGHLPagination)
def list_invoices(request, patient_id: str = '', status: str = ''):
    qs = Invoice.objects.prefetch_related('items').all()
    if patient_id:
        qs = qs.filter(patient_id=patient_id)
    if status:
        qs = qs.filter(status=status)
    return [_invoice_to_dict(i) for i in qs]


@router.get('/factures/{invoice_id}', response=InvoiceOut)
@require_permission('billing:read')
def get_invoice(request, invoice_id: str):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return _invoice_to_dict(invoice)


@router.post('/factures/{invoice_id}/emettre')
@require_permission('billing:write')
def issue_invoice(request, invoice_id: str):
    invoice = get_object_or_404(Invoice, id=invoice_id, status='DRAFT')
    invoice.status = 'ISSUED'
    invoice.save(update_fields=['status'])
    create_audit_log(request.auth, 'UPDATE', 'Invoice', resource_id=invoice_id, ip_address=_get_ip(request))
    return {'detail': 'Facture emise', 'invoice_number': invoice.invoice_number}


@router.post('/factures/{invoice_id}/paiements', response=PaymentOut)
@require_permission('billing:write')
def add_payment(request, invoice_id: str, payload: PaymentSchema):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.status in ('CANCELLED', 'PAID'):
        raise HttpError(400, 'Cette facture ne peut plus recevoir de paiement')
    if payload.amount <= 0:
        raise HttpError(400, 'Montant invalide')
    if payload.amount > invoice.balance_due:
        raise HttpError(400, f'Montant depasse le solde restant ({invoice.balance_due})')

    with transaction.atomic():
        payment = Payment.objects.create(
            invoice=invoice,
            amount=payload.amount,
            method=payload.method,
            reference=payload.reference or '',
            received_by=request.auth,
            notes=payload.notes or '',
        )
        AccountingEntry.objects.create(
            entry_type='CREDIT',
            amount=payload.amount,
            description=f'Paiement facture {invoice.invoice_number}',
            invoice=invoice,
            payment=payment,
        )

    create_audit_log(request.auth, 'CREATE', 'Payment', resource_id=payment.id, ip_address=_get_ip(request))
    return payment


@router.get('/factures/{invoice_id}/paiements', response=List[PaymentOut])
@require_permission('billing:read')
def list_payments(request, invoice_id: str):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return list(invoice.payments.all())

