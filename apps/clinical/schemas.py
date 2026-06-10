from ninja import Schema
from typing import Optional, List
from datetime import datetime
import uuid


class DiagnosisSchema(Schema):
    icd10_code: str
    icd10_label: str
    diag_type: str = 'PRINCIPAL'
    notes: Optional[str] = ''


class DiagnosisOut(Schema):
    id: uuid.UUID
    icd10_code: str
    icd10_label: str
    diag_type: str
    notes: str


class PrescriptionItemSchema(Schema):
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    route: Optional[str] = ''
    instructions: Optional[str] = ''
    quantity: int = 1


class PrescriptionItemOut(Schema):
    id: uuid.UUID
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    route: str
    instructions: str
    quantity: int


class PrescriptionCreateSchema(Schema):
    items: List[PrescriptionItemSchema]
    notes: Optional[str] = ''


class PrescriptionOut(Schema):
    id: uuid.UUID
    status: str
    notes: str
    validated_at: Optional[datetime]
    created_at: datetime
    items: List[PrescriptionItemOut]


class ConsultationCreateSchema(Schema):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    hospitalization_id: Optional[uuid.UUID] = None
    consultation_date: datetime
    chief_complaint: str
    anamnesis: Optional[str] = ''
    physical_exam: Optional[str] = ''
    notes: Optional[str] = ''


class ConsultationUpdateSchema(Schema):
    status: Optional[str] = None
    chief_complaint: Optional[str] = None
    anamnesis: Optional[str] = None
    physical_exam: Optional[str] = None
    notes: Optional[str] = None


class ConsultationOut(Schema):
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    status: str
    consultation_date: datetime
    chief_complaint: str
    anamnesis: str
    physical_exam: str
    notes: str
    created_at: datetime


class ConsultationDetailOut(ConsultationOut):
    diagnoses: List[DiagnosisOut]
    prescriptions: List[PrescriptionOut]
