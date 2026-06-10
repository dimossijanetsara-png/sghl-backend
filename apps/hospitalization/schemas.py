from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
import uuid


class BuildingSchema(Schema):
    name: str
    description: Optional[str] = ''


class BuildingOut(Schema):
    id: uuid.UUID
    name: str
    description: str
    is_active: bool


class DepartmentSchema(Schema):
    building_id: uuid.UUID
    name: str
    code: str
    head_doctor_id: Optional[uuid.UUID] = None


class DepartmentOut(Schema):
    id: uuid.UUID
    building_id: uuid.UUID
    name: str
    code: str
    is_active: bool


class RoomSchema(Schema):
    department_id: uuid.UUID
    number: str
    room_type: str = 'STANDARD'
    floor: int = 0


class RoomOut(Schema):
    id: uuid.UUID
    department_id: uuid.UUID
    number: str
    room_type: str
    floor: int
    is_active: bool


class BedOut(Schema):
    id: uuid.UUID
    room_id: uuid.UUID
    number: str
    status: str
    is_active: bool


class BedSchema(Schema):
    room_id: uuid.UUID
    number: str


class HospitalizationCreateSchema(Schema):
    patient_id: uuid.UUID
    bed_id: uuid.UUID
    referring_doctor_id: uuid.UUID
    admission_date: datetime
    expected_discharge_date: date
    admission_reason: str
    notes: Optional[str] = ''


class HospitalizationOut(Schema):
    id: uuid.UUID
    patient_id: uuid.UUID
    bed_id: uuid.UUID
    referring_doctor_id: uuid.UUID
    status: str
    admission_date: datetime
    expected_discharge_date: date
    actual_discharge_date: Optional[datetime]
    admission_reason: str
    discharge_summary: str
    notes: str
    created_at: datetime


class DischargeSchema(Schema):
    discharge_summary: str
    actual_discharge_date: Optional[datetime] = None


class TransferSchema(Schema):
    to_bed_id: uuid.UUID
    reason: str
    transfer_date: Optional[datetime] = None


class TransferOut(Schema):
    id: uuid.UUID
    hospitalization_id: uuid.UUID
    from_bed_id: uuid.UUID
    to_bed_id: uuid.UUID
    transfer_date: datetime
    reason: str
