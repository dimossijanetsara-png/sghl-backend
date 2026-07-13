"""Pytest configuration and fixtures for SGHL tests."""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.fixture
def db_with_models(db):
    """Fixture that provides database with initial models."""
    return db


@pytest.fixture
def admin_user(db):
    """Fixture that creates an admin user."""
    return User.objects.create_superuser(
        email='admin@sghl.test',
        password='TestAdmin123!',
        first_name='Admin',
        last_name='SGHL',
    )


@pytest.fixture
def doctor_user(db):
    """Fixture that creates a doctor user."""
    return User.objects.create_user(
        email='doctor@sghl.test',
        password='TestDoctor123!',
        first_name='Jean',
        last_name='Dubois',
        role='DOCTOR',
    )


@pytest.fixture
def nurse_user(db):
    """Fixture that creates a nurse user."""
    return User.objects.create_user(
        email='nurse@sghl.test',
        password='TestNurse123!',
        first_name='Marie',
        last_name='Martin',
        role='NURSE',
    )


@pytest.fixture
def biologist_user(db):
    """Fixture that creates a biologist user."""
    return User.objects.create_user(
        email='biologist@sghl.test',
        password='TestBio123!',
        first_name='Paul',
        last_name='Lemoine',
        role='BIOLOGIST',
    )


@pytest.fixture
def pharmacist_user(db):
    """Fixture that creates a pharmacist user."""
    return User.objects.create_user(
        email='pharmacist@sghl.test',
        password='TestPharm123!',
        first_name='Sophie',
        last_name='Arnaud',
        role='PHARMACIST',
    )


@pytest.fixture
def patient_user(db):
    """Fixture that creates a patient user."""
    return User.objects.create_user(
        email='patient@sghl.test',
        password='TestPatient123!',
        first_name='Pierre',
        last_name='Moreau',
        role='PATIENT',
    )


@pytest.fixture
def accountant_user(db):
    """Fixture that creates an accountant user."""
    return User.objects.create_user(
        email='accountant@sghl.test',
        password='TestAccount123!',
        first_name='Robert',
        last_name='Dupont',
        role='ACCOUNTANT',
    )


@pytest.fixture
def client():
    """Fixture that provides a Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(client, doctor_user):
    """Fixture that provides an authenticated client."""
    client.user = doctor_user
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(doctor_user)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {str(refresh.access_token)}'
    return client


@pytest.fixture
def patient(db):
    """Fixture that creates a test patient."""
    from apps.patients.models import Patient
    return Patient.objects.create(
        first_name='Test',
        last_name='Patient',
        date_of_birth=timezone.now().date() - timedelta(days=365*30),
        gender='M',
        blood_type='O+',
        email='patient.test@sghl.test',
        phone='+243123456789',
    )


@pytest.fixture
def hospitalization(db, patient, doctor_user):
    """Fixture that creates a test hospitalization."""
    from apps.hospitalization.models import Building, Department, Room, Bed, Hospitalization

    building = Building.objects.create(name='Building A')
    department = Department.objects.create(
        building=building,
        name='Emergency',
        code='EMERG',
        head_doctor=doctor_user,
    )
    room = Room.objects.create(
        department=department,
        number='101',
        room_type='EMERGENCY',
    )
    bed = Bed.objects.create(
        room=room,
        number='A',
        status='AVAILABLE',
    )

    return Hospitalization.objects.create(
        patient=patient,
        bed=bed,
        referring_doctor=doctor_user,
        status='ACTIVE',
        admission_date=timezone.now(),
        expected_discharge_date=timezone.now().date() + timedelta(days=3),
        admission_reason='Emergency admission',
    )


@pytest.fixture
def consultation(db, patient, doctor_user, hospitalization):
    """Fixture that creates a test consultation."""
    from apps.clinical.models import Consultation
    return Consultation.objects.create(
        patient=patient,
        doctor=doctor_user,
        hospitalization=hospitalization,
        status='COMPLETED',
        consultation_date=timezone.now(),
        chief_complaint='Chest pain',
        notes='Patient stable',
    )


@pytest.fixture
def prescription(db, consultation, doctor_user):
    """Fixture that creates a test prescription."""
    from apps.clinical.models import Prescription, PrescriptionItem
    from apps.pharmacy.models import Medication

    medication = Medication.objects.create(
        name='Aspirin',
        generic_name='Acetylsalicylic acid',
        category='Analgesic',
        dosage_form='Tablet',
        strength='500mg',
        unit='mg',
    )

    prescription = Prescription.objects.create(
        consultation=consultation,
        prescribed_by=doctor_user,
        status='DRAFT',
        notes='For pain relief',
    )

    PrescriptionItem.objects.create(
        prescription=prescription,
        medication_name=medication.name,
        dosage='500mg',
        frequency='2 times daily',
        duration='7 days',
        quantity=14,
    )

    return prescription


@pytest.fixture
def lab_order(db, patient, doctor_user, hospitalization):
    """Fixture that creates a test lab order."""
    from apps.laboratory.models import LabOrder, LabTest, LabOrderItem

    test = LabTest.objects.create(
        code='CBC',
        name='Complete Blood Count',
        category='Hematology',
        unit='',
    )

    order = LabOrder.objects.create(
        patient=patient,
        ordered_by=doctor_user,
        hospitalization=hospitalization,
        status='ORDERED',
        priority='NORMAL',
    )

    LabOrderItem.objects.create(
        order=order,
        test=test,
    )

    return order


@pytest.fixture
def invoice(db, patient, doctor_user):
    """Fixture that creates a test invoice."""
    from apps.billing.models import Invoice, InvoiceItem
    from decimal import Decimal

    invoice = Invoice.objects.create(
        patient=patient,
        issued_by=doctor_user,
        status='DRAFT',
        subtotal=Decimal('100.00'),
        tax=Decimal('20.00'),
        total=Decimal('120.00'),
    )

    InvoiceItem.objects.create(
        invoice=invoice,
        item_type='CONSULTATION',
        description='Medical consultation',
        quantity=1,
        unit_price=Decimal('100.00'),
    )

    return invoice
