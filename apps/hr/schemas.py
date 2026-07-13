from ninja import Schema
from typing import Optional
from datetime import date, datetime
import uuid


class UserBriefOut(Schema):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    phone: str
    is_active: bool


class StaffProfileOut(Schema):
    id: uuid.UUID
    user: UserBriefOut
    user_id: uuid.UUID
    department_id: Optional[uuid.UUID]
    employee_number: str
    specialization: str
    license_number: str
    hire_date: Optional[date]
    is_active: bool


class StaffCreateSchema(Schema):
    user_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    employee_number: str
    specialization: Optional[str] = ''
    license_number: Optional[str] = ''
    hire_date: Optional[date] = None


class ShiftCreateSchema(Schema):
    staff_id: uuid.UUID
    department_id: uuid.UUID
    shift_type: str
    start_datetime: datetime
    end_datetime: datetime
    notes: Optional[str] = ''


class ShiftOut(Schema):
    id: uuid.UUID
    staff_id: uuid.UUID
    department_id: uuid.UUID
    shift_type: str
    start_datetime: datetime
    end_datetime: datetime
    notes: str
    is_confirmed: bool
