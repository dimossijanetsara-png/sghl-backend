from ninja import Schema
from pydantic import EmailStr
from typing import Optional
from datetime import date, datetime
import uuid


class PatientCreateSchema(Schema):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    national_id: Optional[str] = ''
    phone: Optional[str] = ''
    email: Optional[str] = None
    address: Optional[str] = ''
    city: Optional[str] = ''
    blood_type: Optional[str] = 'INC'
    allergies: Optional[str] = ''
    chronic_conditions: Optional[str] = ''
    emergency_contact_name: Optional[str] = ''
    emergency_contact_phone: Optional[str] = ''
    emergency_contact_relation: Optional[str] = ''
    insurance_provider: Optional[str] = ''
    insurance_number: Optional[str] = ''
    consent_given: Optional[bool] = False


class PatientUpdateSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None


class PatientOut(Schema):
    id: uuid.UUID
    record_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    national_id: str
    phone: str
    email: str
    address: str
    city: str
    blood_type: str
    allergies: str
    chronic_conditions: str
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_contact_relation: str
    insurance_provider: str
    insurance_number: str
    consent_given: bool
    consent_date: Optional[datetime]
    is_archived: bool
    created_at: datetime


class PatientListOut(Schema):
    id: uuid.UUID
    record_number: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str
    blood_type: str
    is_archived: bool


class DocumentOut(Schema):
    id: uuid.UUID
    doc_type: str
    title: str
    mime_type: str
    file_size: int
    description: str
    created_at: datetime
