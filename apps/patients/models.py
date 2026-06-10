import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Patient(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = 'M', 'Masculin'
        FEMALE = 'F', 'Feminin'
        OTHER = 'O', 'Autre'

    class BloodType(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'
        UNKNOWN = 'INC', 'Inconnu'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record_number = models.CharField(max_length=20, unique=True, editable=False)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)
    national_id = models.CharField(max_length=50, blank=True)

    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    blood_type = models.CharField(max_length=3, choices=BloodType.choices, default=BloodType.UNKNOWN)
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)

    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)

    insurance_provider = models.CharField(max_length=200, blank=True)
    insurance_number = models.CharField(max_length=100, blank=True)

    user = models.OneToOneField(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='patient_profile'
    )

    consent_given = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)

    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'patients'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['record_number']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['national_id']),
        ]

    def __str__(self):
        return f'{self.record_number} - {self.get_full_name()}'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def save(self, *args, **kwargs):
        if not self.record_number:
            self.record_number = self._generate_record_number()
        super().save(*args, **kwargs)

    def _generate_record_number(self):
        from django.utils import timezone
        year = timezone.now().year
        count = Patient.objects.filter(created_at__year=year).count() + 1
        return f'PAT-{year}-{count:05d}'


class PatientDocument(TimeStampedModel):
    class DocType(models.TextChoices):
        IDENTITY = 'IDENTITY', 'Piece identite'
        INSURANCE = 'INSURANCE', 'Attestation assurance'
        MEDICAL_REPORT = 'MEDICAL_REPORT', 'Rapport medical'
        IMAGING = 'IMAGING', 'Imagerie'
        OTHER = 'OTHER', 'Autre'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='patients/documents/')
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'patient_documents'
        ordering = ['-created_at']
