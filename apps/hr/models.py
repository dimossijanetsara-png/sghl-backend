import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class StaffProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('authentication.User', on_delete=models.CASCADE, related_name='staff_profile')
    department = models.ForeignKey(
        'hospitalization.Department', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='staff'
    )
    employee_number = models.CharField(max_length=30, unique=True)
    specialization = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'staff_profiles'

    def __str__(self):
        return f'{self.user.get_full_name()} - {self.employee_number}'


class Shift(TimeStampedModel):
    class ShiftType(models.TextChoices):
        MORNING = 'MORNING', 'Matin'
        AFTERNOON = 'AFTERNOON', 'Apres-midi'
        NIGHT = 'NIGHT', 'Nuit'
        ON_CALL = 'ON_CALL', 'De garde'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name='shifts')
    department = models.ForeignKey(
        'hospitalization.Department', on_delete=models.PROTECT, related_name='shifts'
    )
    shift_type = models.CharField(max_length=20, choices=ShiftType.choices)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    notes = models.TextField(blank=True)
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        db_table = 'shifts'
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['staff', 'start_datetime']),
            models.Index(fields=['department', 'start_datetime']),
        ]

    def __str__(self):
        return f'{self.staff} - {self.shift_type} - {self.start_datetime.date()}'
