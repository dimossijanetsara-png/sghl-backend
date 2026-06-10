from ninja import Schema
from typing import Optional, List
from datetime import datetime
import uuid


class LabTestOut(Schema):
    id: uuid.UUID
    code: str
    name: str
    category: str
    normal_range: str
    unit: str
    price: float
    turnaround_hours: int


class LabOrderItemSchema(Schema):
    test_id: uuid.UUID


class LabOrderItemOut(Schema):
    id: uuid.UUID
    test_id: uuid.UUID
    result_value: str
    result_unit: str
    is_abnormal: bool
    notes: str
    resulted_at: Optional[datetime]


class LabOrderCreateSchema(Schema):
    patient_id: uuid.UUID
    test_ids: List[uuid.UUID]
    hospitalization_id: Optional[uuid.UUID] = None
    consultation_id: Optional[uuid.UUID] = None
    priority: str = 'NORMAL'
    clinical_notes: Optional[str] = ''


class LabOrderOut(Schema):
    id: uuid.UUID
    patient_id: uuid.UUID
    ordered_by_id: uuid.UUID
    status: str
    priority: str
    clinical_notes: str
    sampled_at: Optional[datetime]
    validated_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    items: List[LabOrderItemOut]


class ResultEntrySchema(Schema):
    item_id: uuid.UUID
    result_value: str
    result_unit: Optional[str] = ''
    is_abnormal: bool = False
    notes: Optional[str] = ''


class AssignSchema(Schema):
    biologist_id: uuid.UUID
