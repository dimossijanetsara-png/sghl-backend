from ninja import Schema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid


class InvoiceItemSchema(Schema):
    item_type: str
    description: str
    quantity: int = 1
    unit_price: Decimal
    discount_percent: Decimal = Decimal('0')
    reference_id: Optional[str] = ''


class InvoiceItemOut(Schema):
    id: uuid.UUID
    item_type: str
    description: str
    quantity: int
    unit_price: Decimal
    discount_percent: Decimal
    total_price: Decimal


class InvoiceCreateSchema(Schema):
    patient_id: uuid.UUID
    hospitalization_id: Optional[uuid.UUID] = None
    items: List[InvoiceItemSchema]
    discount: Decimal = Decimal('0')
    tax: Decimal = Decimal('0')
    insurance_provider: Optional[str] = ''
    insurance_coverage: Decimal = Decimal('0')
    insurance_claim_number: Optional[str] = ''
    notes: Optional[str] = ''


class InvoiceOut(Schema):
    id: uuid.UUID
    invoice_number: str
    patient_id: uuid.UUID
    status: str
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    amount_paid: Decimal
    insurance_coverage: Decimal
    balance_due: Decimal
    insurance_provider: str
    notes: str
    created_at: datetime
    items: List[InvoiceItemOut]


class PaymentSchema(Schema):
    amount: Decimal
    method: str
    reference: Optional[str] = ''
    notes: Optional[str] = ''


class PaymentOut(Schema):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    method: str
    reference: str
    created_at: datetime
