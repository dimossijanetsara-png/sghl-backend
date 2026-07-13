"""Factory Boy factories for test data generation."""
import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from faker import Faker

User = get_user_model()
fake = Faker(['fr_FR', 'en_US'])


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGeneration(lambda obj, create, extracted, **kwargs: obj.set_password('TestPass123!'))
    is_active = True
    role = 'PATIENT'


class AdminFactory(UserFactory):
    """Factory for creating admin users."""
    role = 'ADMIN'
    is_staff = True
    is_superuser = True


class DoctorFactory(UserFactory):
    """Factory for creating doctor users."""
    role = 'DOCTOR'


class NurseFactory(UserFactory):
    """Factory for creating nurse users."""
    role = 'NURSE'


class BiologistFactory(UserFactory):
    """Factory for creating biologist users."""
    role = 'BIOLOGIST'


class PharmacistFactory(UserFactory):
    """Factory for creating pharmacist users."""
    role = 'PHARMACIST'


class PatientFactory(factory.django.DjangoModelFactory):
    """Factory for creating Patient instances."""

    class Meta:
        model = 'patients.Patient'

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=90)
    gender = factory.Faker('random_element', elements=['M', 'F', 'O'])
    blood_type = factory.Faker('random_element', elements=['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'])
    phone = factory.Faker('phone_number')
    email = factory.Faker('email')
    address = factory.Faker('address')
    city = factory.Faker('city')


class BuildingFactory(factory.django.DjangoModelFactory):
    """Factory for creating Building instances."""

    class Meta:
        model = 'hospitalization.Building'

    name = factory.Faker('catch_phrase')


class DepartmentFactory(factory.django.DjangoModelFactory):
    """Factory for creating Department instances."""

    class Meta:
        model = 'hospitalization.Department'

    building = factory.SubFactory(BuildingFactory)
    name = factory.Faker('word')
    code = factory.Sequence(lambda n: f'DEPT{n:03d}')
    head_doctor = factory.SubFactory(DoctorFactory)


class RoomFactory(factory.django.DjangoModelFactory):
    """Factory for creating Room instances."""

    class Meta:
        model = 'hospitalization.Room'

    department = factory.SubFactory(DepartmentFactory)
    number = factory.Sequence(lambda n: f'{n:03d}')
    room_type = factory.Faker('random_element', elements=['STANDARD', 'PRIVATE', 'ICU', 'EMERGENCY'])


class BedFactory(factory.django.DjangoModelFactory):
    """Factory for creating Bed instances."""

    class Meta:
        model = 'hospitalization.Bed'

    room = factory.SubFactory(RoomFactory)
    number = factory.Sequence(lambda n: chr(65 + (n % 26)))  # A, B, C, ...
    status = 'AVAILABLE'


class HospitalizationFactory(factory.django.DjangoModelFactory):
    """Factory for creating Hospitalization instances."""

    class Meta:
        model = 'hospitalization.Hospitalization'

    patient = factory.SubFactory(PatientFactory)
    bed = factory.SubFactory(BedFactory)
    referring_doctor = factory.SubFactory(DoctorFactory)
    status = 'ACTIVE'
    admission_date = factory.Faker('date_time')
    expected_discharge_date = factory.LazyAttribute(lambda obj: obj.admission_date.date() + timedelta(days=7))
    admission_reason = factory.Faker('sentence')


class ConsultationFactory(factory.django.DjangoModelFactory):
    """Factory for creating Consultation instances."""

    class Meta:
        model = 'clinical.Consultation'

    patient = factory.SubFactory(PatientFactory)
    doctor = factory.SubFactory(DoctorFactory)
    hospitalization = factory.SubFactory(HospitalizationFactory)
    status = 'COMPLETED'
    consultation_date = factory.Faker('date_time')
    chief_complaint = factory.Faker('sentence')
    notes = factory.Faker('text', max_nb_chars=200)


class PrescriptionFactory(factory.django.DjangoModelFactory):
    """Factory for creating Prescription instances."""

    class Meta:
        model = 'clinical.Prescription'

    consultation = factory.SubFactory(ConsultationFactory)
    prescribed_by = factory.SubFactory(DoctorFactory)
    status = 'DRAFT'
    notes = factory.Faker('text', max_nb_chars=100)


class MedicationFactory(factory.django.DjangoModelFactory):
    """Factory for creating Medication instances."""

    class Meta:
        model = 'pharmacy.Medication'

    name = factory.Faker('word')
    generic_name = factory.Faker('word')
    category = factory.Faker('word')
    dosage_form = 'Tablet'
    strength = factory.Sequence(lambda n: f'{100 * (n + 1)}mg')
    unit = 'mg'


class LabTestFactory(factory.django.DjangoModelFactory):
    """Factory for creating LabTest instances."""

    class Meta:
        model = 'laboratory.LabTest'

    code = factory.Sequence(lambda n: f'TEST{n:03d}')
    name = factory.Faker('catch_phrase')
    category = factory.Faker('word')
    unit = factory.Faker('random_element', elements=['mg/dL', 'g/L', 'units/L', '%'])


class LabOrderFactory(factory.django.DjangoModelFactory):
    """Factory for creating LabOrder instances."""

    class Meta:
        model = 'laboratory.LabOrder'

    patient = factory.SubFactory(PatientFactory)
    ordered_by = factory.SubFactory(DoctorFactory)
    hospitalization = factory.SubFactory(HospitalizationFactory)
    status = 'ORDERED'
    priority = 'NORMAL'
    clinical_notes = factory.Faker('text', max_nb_chars=100)


class InvoiceFactory(factory.django.DjangoModelFactory):
    """Factory for creating Invoice instances."""

    class Meta:
        model = 'billing.Invoice'

    patient = factory.SubFactory(PatientFactory)
    issued_by = factory.SubFactory(DoctorFactory)
    status = 'DRAFT'
    subtotal = factory.Faker('random.random') * 1000
    discount = Decimal('0.00')
    tax = factory.LazyAttribute(lambda obj: Decimal(obj.subtotal) * Decimal('0.20'))
    total = factory.LazyAttribute(lambda obj: Decimal(obj.subtotal) - Decimal(obj.discount) + Decimal(obj.tax))


class AuditLogFactory(factory.django.DjangoModelFactory):
    """Factory for creating AuditLog instances."""

    class Meta:
        model = 'core.AuditLog'

    user = factory.SubFactory(UserFactory)
    action = factory.Faker('random_element', elements=['CREATE', 'UPDATE', 'DELETE', 'VIEW', 'LOGIN'])
    resource = factory.Faker('word')
    resource_id = factory.Faker('uuid4')
    ip_address = factory.Faker('ipv4')
    timestamp = factory.Faker('date_time')
