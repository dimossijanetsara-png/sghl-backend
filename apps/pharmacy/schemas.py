from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import uuid


class MedicationOut(Schema):
    id: uuid.UUID
    name: str
    generic_name: str
    category: str
    dosage_form: str
    strength: str
    unit: str
    reorder_threshold: int
    unit_price: Decimal
    total_stock: int
    is_low_stock: bool


class BatchCreateSchema(Schema):
    medication_id: uuid.UUID
    batch_number: str
    quantity: int
    expiry_date: date
    supplier: Optional[str] = ''
    purchase_price: Optional[Decimal] = Decimal('0')
    received_at: datetime


class BatchOut(Schema):
    id: uuid.UUID
    medication_id: uuid.UUID
    batch_number: str
    quantity: int
    expiry_date: date
    supplier: str
    purchase_price: Decimal
    received_at: datetime
    is_expired: bool


class DispensationItemSchema(Schema):
    batch_id: uuid.UUID
    prescription_item_id: uuid.UUID
    quantity: int


class DispensationCreateSchema(Schema):
    prescription_id: uuid.UUID
    items: List[DispensationItemSchema]
    notes: Optional[str] = ''


class DispensationOut(Schema):
    id: uuid.UUID
    prescription_id: uuid.UUID
    dispensed_by_id: uuid.UUID
    notes: str
    created_at: datetime


class StockMovementOut(Schema):
    id: uuid.UUID
    batch_id: uuid.UUID
    movement_type: str
    quantity: int
    reference: str
    notes: str
    timestamp: datetime
