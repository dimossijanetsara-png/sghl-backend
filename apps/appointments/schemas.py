from ninja import Schema
from typing import Optional
from datetime import datetime, time
import uuid


class AppointmentCreateSchema(Schema):
    patient_id: Optional[uuid.UUID] = None  # Auto-résolu pour le rôle PATIENT
    doctor_id: uuid.UUID
    appointment_date: datetime
    duration_minutes: int = 30
    reason: str
    notes: Optional[str] = ''


class DoctorOut(Schema):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str


class AppointmentOut(Schema):
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    appointment_date: datetime
    duration_minutes: int
    reason: str
    status: str
    notes: str
    created_at: datetime


class AppointmentUpdateSchema(Schema):
    status: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None


class AvailabilityCreateSchema(Schema):
    doctor_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int = 30


class AvailabilityOut(Schema):
    id: uuid.UUID
    doctor_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool
