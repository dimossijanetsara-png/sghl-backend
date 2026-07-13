import uuid
import random
import pyotp
from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Superutilisateur'
        DOCTOR = 'DOCTOR', 'Médecin'
        NURSE = 'NURSE', 'Infirmier(e)'
        BIOLOGIST = 'BIOLOGIST', 'Biologiste'
        PHARMACIST = 'PHARMACIST', 'Pharmacien(ne)'
        RECEPTIONIST = 'RECEPTIONIST', 'Secrétaire / Réceptionniste'
        ACCOUNTANT = 'ACCOUNTANT', 'Comptable'
        PATIENT = 'PATIENT', 'Patient'
        LABTECH = 'LABTECH', 'Technicien(ne) de laboratoire'
        OTHER = 'OTHER', 'Autre personnel'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True)

    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    # OTP pour vérification lors de l'inscription
    otp_code = models.CharField(max_length=6, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_verified = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        indexes = [models.Index(fields=['email', 'role'])]

    def __str__(self):
        return f'{self.get_full_name()} ({self.role})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def generate_mfa_secret(self):
        self.mfa_secret = pyotp.random_base32()
        return self.mfa_secret

    def get_mfa_uri(self):
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.email, issuer_name='SGHL'
        )

    def verify_mfa_token(self, token):
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token)

    def generate_otp(self):
        """Génère un code OTP à 6 chiffres valable 10 minutes."""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=['otp_code', 'otp_expires_at'])
        return self.otp_code

    def check_otp(self, code: str):
        """Vérifie le code OTP. Retourne (bool, message)."""
        if not self.otp_code:
            return False, "Aucun code OTP généré"
        if not self.otp_expires_at or timezone.now() > self.otp_expires_at:
            return False, "Code OTP expiré"
        if self.otp_code != code.strip():
            return False, "Code OTP invalide"
        return True, "OK"

    def activate_account(self):
        """Active le compte après vérification OTP."""
        self.is_active = True
        self.otp_verified = True
        self.otp_code = ''
        self.otp_expires_at = None
        self.save(update_fields=['is_active', 'otp_verified', 'otp_code', 'otp_expires_at'])

    def is_account_locked(self):
        from django.utils import timezone
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    @property
    def permissions_map(self):
        from apps.authentication.permissions import ROLE_PERMISSIONS
        return ROLE_PERMISSIONS.get(self.role, set())


class RefreshTokenBlacklist(models.Model):
    token = models.TextField(unique=True)
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blacklisted_tokens')

    class Meta:
        db_table = 'token_blacklist'
        indexes = [models.Index(fields=['token'])]
