from ninja import Schema
from pydantic import EmailStr, field_validator
from typing import Optional
import uuid


class LoginSchema(Schema):
    email: EmailStr
    password: str
    mfa_token: Optional[str] = None


class TokenSchema(Schema):
    access: str
    refresh: str
    token_type: str = 'bearer'
    user_id: str
    role: str
    mfa_required: bool = False


class RefreshSchema(Schema):
    refresh: str


class RegisterSchema(Schema):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str
    phone: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 10:
            raise ValueError('Le mot de passe doit contenir au moins 10 caractères')
        if not any(c.isupper() for c in v):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        if not any(c.isdigit() for c in v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        allowed = ['ADMIN', 'DOCTOR', 'NURSE', 'BIOLOGIST', 'PHARMACIST',
                   'RECEPTIONIST', 'ACCOUNTANT', 'PATIENT']
        if v not in allowed:
            raise ValueError(f'Rôle invalide. Valeurs acceptées: {allowed}')
        return v


class UserOut(Schema):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    phone: str
    is_active: bool
    mfa_enabled: bool


class MFASetupOut(Schema):
    secret: str
    qr_uri: str
    qr_image_base64: str


class MFAVerifySchema(Schema):
    token: str


class ChangePasswordSchema(Schema):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 10:
            raise ValueError('Minimum 10 caractères')
        if not any(c.isupper() for c in v):
            raise ValueError('Au moins une majuscule requise')
        if not any(c.isdigit() for c in v):
            raise ValueError('Au moins un chiffre requis')
        return v


class UpdateProfileSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
