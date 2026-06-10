import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Building(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'buildings'

    def __str__(self):
        return self.name


class Department(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    building = models.ForeignKey(Building, on_delete=models.PROTECT, related_name='departments')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    head_doctor = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='headed_departments'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'departments'

    def __str__(self):
        return f'{self.building.name} - {self.name}'


class Room(TimeStampedModel):
    class RoomType(models.TextChoices):
        STANDARD = 'STANDARD', 'Standard'
        PRIVATE = 'PRIVATE', 'Privee'
        ICU = 'ICU', 'Soins intensifs'
        EMERGENCY = 'EMERGENCY', 'Urgence'
        OPERATING = 'OPERATING', 'Bloc operatoire'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='rooms')
    number = models.CharField(max_length=20)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.STANDARD)
    floor = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'rooms'
        unique_together = [['department', 'number']]

    def __str__(self):
        return f'Chambre {self.number} - {self.department}'


class Bed(TimeStampedModel):
    class BedStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Disponible'
        OCCUPIED = 'OCCUPIED', 'Occupe'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        RESERVED = 'RESERVED', 'Reserve'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='beds')
    number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=BedStatus.choices, default=BedStatus.AVAILABLE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'beds'
        unique_together = [['room', 'number']]

    def __str__(self):
        return f'Lit {self.number} - {self.room}'

    def is_available(self):
        return self.status == self.BedStatus.AVAILABLE


class Hospitalization(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        DISCHARGED = 'DISCHARGED', 'Sortie'
        TRANSFERRED = 'TRANSFERRED', 'Transferee'
        DECEASED = 'DECEASED', 'Decede'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, related_name='hospitalizations')
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='hospitalizations')
    referring_doctor = models.ForeignKey(
        'authentication.User', on_delete=models.PROTECT, related_name='referred_hospitalizations'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    admission_date = models.DateTimeField()
    expected_discharge_date = models.DateField()
    actual_discharge_date = models.DateTimeField(null=True, blank=True)
    admission_reason = models.TextField()
    discharge_summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'hospitalizations'
        ordering = ['-admission_date']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['bed', 'status']),
        ]

    def __str__(self):
        return f'Hospitalisation {self.id} - {self.patient}'

    def save(self, *args, **kwargs):
        # Verrouillage : 1 lit = 1 patient max
        if self._state.adding and self.status == self.Status.ACTIVE:
            active_hosp = Hospitalization.objects.filter(
                bed=self.bed, status=self.Status.ACTIVE
            ).exists()
            if active_hosp:
                raise ValueError('Ce lit est deja occupe')
            self.bed.status = Bed.BedStatus.OCCUPIED
            self.bed.save(update_fields=['status'])
        super().save(*args, **kwargs)


class Transfer(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospitalization = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name='transfers')
    from_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='transfers_from')
    to_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='transfers_to')
    transfer_date = models.DateTimeField()
    reason = models.TextField()
    ordered_by = models.ForeignKey('authentication.User', on_delete=models.PROTECT)

    class Meta:
        db_table = 'transfers'
        ordering = ['-transfer_date']
