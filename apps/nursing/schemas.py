from ninja import Schema
from typing import Optional, List
from datetime import datetime, time
from decimal import Decimal
import uuid


class VitalSignSchema(Schema):
    recorded_at: datetime
    temperature: Optional[Decimal] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    height: Optional[Decimal] = None
    pain_score: Optional[int] = None
    notes: Optional[str] = ''


class VitalSignOut(VitalSignSchema):
    id: uuid.UUID
    hospitalization_id: uuid.UUID
    recorded_by_id: uuid.UUID


class CareTaskSchema(Schema):
    title: str
    description: Optional[str] = ''
    frequency: str = 'DAILY'
    scheduled_time: Optional[time] = None
    assigned_to_id: Optional[uuid.UUID] = None
    prescription_item_id: Optional[uuid.UUID] = None


class CareTaskOut(Schema):
    id: uuid.UUID
    title: str
    description: str
    frequency: str
    scheduled_time: Optional[time]
    status: str
    done_at: Optional[datetime]
    notes: str


class CareTaskDoneSchema(Schema):
    notes: Optional[str] = ''


class CareplanCreateSchema(Schema):
    hospitalization_id: uuid.UUID
    goals: Optional[str] = ''
    notes: Optional[str] = ''
    tasks: Optional[List[CareTaskSchema]] = []


class CareplanOut(Schema):
    id: uuid.UUID
    hospitalization_id: uuid.UUID
    status: str
    goals: str
    notes: str
    created_at: datetime
    tasks: List[CareTaskOut]


class NursingNoteSchema(Schema):
    content: str
    category: Optional[str] = ''


class NursingNoteOut(Schema):
    id: uuid.UUID
    hospitalization_id: uuid.UUID
    written_by_id: uuid.UUID
    content: str
    category: str
    created_at: datetime
