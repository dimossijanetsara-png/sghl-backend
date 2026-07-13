import base64
import io
import qrcode
from datetime import timedelta
from typing import List

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import create_audit_log
from .models import RefreshTokenBlacklist
from .schemas import (
    LoginSchema, TokenSchema, RefreshSchema, RegisterSchema,
    UserOut, MFASetupOut, MFAVerifySchema, ChangePasswordSchema, UpdateProfileSchema,
    PublicRegisterSchema, RegisterResponseSchema, OTPVerifySchema, ResendOTPSchema,
)

User = get_user_model()
router = Router()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR', '')


def _send_otp_email(user, otp_code: str):
    """Envoie le code OTP par email."""
    try:
        send_mail(
            subject='[SGHL] Code de vérification — Activation de votre compte',
            message=(
                f'Bonjour {user.get_full_name()},\n\n'
                f'Votre code de vérification pour activer votre compte SGHL est :\n\n'
                f'    {otp_code}\n\n'
                f'Ce code est valable pendant 10 minutes.\n'
                f'Si vous n\'avez pas demandé ce code, ignorez cet email.\n\n'
                f'— Équipe SGHL'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        # En développement, afficher le code dans la console
        import logging
        logging.getLogger(__name__).warning(
            f'[DEV] OTP pour {user.email}: {otp_code} (email non envoyé)'
        )


# ─── Setup initial ────────────────────────────────────────────────────────────

@router.get('/setup', auth=None)
def setup_status(request):
    """Retourne True si au moins un utilisateur existe déjà."""
    return {'setup_done': User.objects.exists()}


@router.post('/setup', response=UserOut, auth=None)
def setup_first_admin(request, payload: RegisterSchema):
    """Crée le premier compte administrateur. Échoue si un utilisateur existe déjà."""
    if User.objects.exists():
        raise HttpError(409, 'Le système est déjà configuré.')
    user = User.objects.create_superuser(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone or '',
    )
    # Le premier admin est activé directement sans OTP
    user.is_active = True
    user.otp_verified = True
    user.save(update_fields=['is_active', 'otp_verified'])
    return user


# ─── Authentification ─────────────────────────────────────────────────────────

@router.post('/login', response=TokenSchema, auth=None)
def login(request, payload: LoginSchema):
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        create_audit_log(None, 'LOGIN_FAILED', 'User', extra={'email': payload.email}, ip_address=_get_ip(request))
        raise HttpError(401, 'Identifiants invalides')

    if user.is_account_locked():
        raise HttpError(423, 'Compte temporairement verrouillé. Réessayez dans 30 minutes.')

    if not user.is_active:
        raise HttpError(403, 'Compte non activé. Veuillez vérifier votre code OTP reçu par email.')

    if not user.check_password(payload.password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        user.save(update_fields=['failed_login_attempts', 'locked_until'])
        create_audit_log(user, 'LOGIN_FAILED', 'User', resource_id=user.id, ip_address=_get_ip(request))
        raise HttpError(401, 'Identifiants invalides')

    if user.mfa_enabled:
        if not payload.mfa_token:
            return TokenSchema(
                access='', refresh='', user_id=str(user.id),
                role=user.role, mfa_required=True
            )
        if not user.verify_mfa_token(payload.mfa_token):
            raise HttpError(401, 'Code MFA invalide')

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_ip = _get_ip(request)
    user.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login_ip'])

    refresh = RefreshToken.for_user(user)
    create_audit_log(user, 'LOGIN', 'User', resource_id=user.id, ip_address=_get_ip(request))

    return TokenSchema(
        access=str(refresh.access_token),
        refresh=str(refresh),
        user_id=str(user.id),
        role=user.role,
    )


@router.post('/refresh', response=TokenSchema, auth=None)
def refresh_token(request, payload: RefreshSchema):
    if RefreshTokenBlacklist.objects.filter(token=payload.refresh).exists():
        raise HttpError(401, 'Token révoqué')
    try:
        old_refresh = RefreshToken(payload.refresh)
        user = User.objects.get(id=old_refresh['user_id'])
        RefreshTokenBlacklist.objects.create(token=payload.refresh, user=user)
        new_refresh = RefreshToken.for_user(user)
        return TokenSchema(
            access=str(new_refresh.access_token),
            refresh=str(new_refresh),
            user_id=str(user.id),
            role=user.role,
        )
    except Exception:
        raise HttpError(401, 'Token invalide ou expiré')


@router.post('/logout')
def logout(request, payload: RefreshSchema):
    user = request.auth
    RefreshTokenBlacklist.objects.get_or_create(token=payload.refresh, user=user)
    create_audit_log(user, 'LOGOUT', 'User', resource_id=user.id, ip_address=_get_ip(request))
    return {'detail': 'Déconnexion réussie'}


# ─── Inscription avec OTP ─────────────────────────────────────────────────────

@router.post('/register', response=RegisterResponseSchema)
def register(request, payload: RegisterSchema):
    """
    Inscription par un administrateur.
    Le nouveau compte est créé inactif ; un code OTP est envoyé par email.
    """
    if request.auth.role != 'ADMIN':
        raise HttpError(403, 'Seul un administrateur peut créer des comptes')
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(409, 'Cet email est déjà utilisé')

    user = User.objects.create_user(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        phone=payload.phone or '',
        is_active=False,        # Inactif jusqu'à vérification OTP
        otp_verified=False,
    )
    otp = user.generate_otp()
    _send_otp_email(user, otp)
    create_audit_log(request.auth, 'CREATE', 'User', resource_id=user.id, ip_address=_get_ip(request))

    return RegisterResponseSchema(
        detail=f'Compte créé. Un code OTP a été envoyé à {user.email}. Le compte sera actif après vérification.',
        email=user.email,
        user_id=str(user.id),
    )


@router.post('/register/patient', response=RegisterResponseSchema, auth=None)
def register_patient(request, payload: PublicRegisterSchema):
    """Alias maintenu pour compatibilité — délègue à register_public."""
    return register_public(request, payload)


@router.post('/register/public', response=RegisterResponseSchema, auth=None)
def register_public(request, payload: PublicRegisterSchema):
    """
    Inscription publique — tous les rôles sauf ADMIN (Superutilisateur).
    Le compte est inactif jusqu'à vérification du code OTP reçu par email.
    """
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(409, 'Cet email est déjà utilisé')

    from django.db import transaction
    with transaction.atomic():
        user = User.objects.create_user(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            role=payload.role,
            phone=payload.phone or '',
            is_active=False,
            otp_verified=False,
        )
        # Créer un profil Patient minimal uniquement pour le rôle PATIENT
        if payload.role == 'PATIENT':
            from apps.patients.models import Patient
            from datetime import date
            Patient.objects.create(
                user=user,
                first_name=payload.first_name,
                last_name=payload.last_name,
                date_of_birth=date(2000, 1, 1),
                gender='O',
                email=payload.email,
                phone=payload.phone or '',
            )

    otp = user.generate_otp()
    _send_otp_email(user, otp)

    detail = f'Compte créé. Un code de vérification a été envoyé à {user.email}.'
    if django_settings.DEBUG:
        detail += f' [DEV] Code OTP : {otp}'

    return RegisterResponseSchema(
        detail=detail,
        email=user.email,
        user_id=str(user.id),
    )


@router.post('/verify-otp', response=UserOut, auth=None)
def verify_otp(request, payload: OTPVerifySchema):
    """
    Vérifie le code OTP et active le compte utilisateur.
    Après activation, l'utilisateur peut se connecter normalement.
    """
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        raise HttpError(404, 'Aucun compte trouvé avec cet email')

    if user.otp_verified and user.is_active:
        raise HttpError(400, 'Ce compte est déjà activé')

    valid, message = user.check_otp(payload.otp_code)
    if not valid:
        raise HttpError(400, message)

    user.activate_account()
    create_audit_log(user, 'UPDATE', 'User', resource_id=user.id,
                     extra={'action': 'OTP_VERIFIED'}, ip_address=_get_ip(request))
    return user


@router.post('/resend-otp', auth=None)
def resend_otp(request, payload: ResendOTPSchema):
    """
    Renvoie un nouveau code OTP par email.
    Limité à une fois toutes les 2 minutes.
    """
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        raise HttpError(404, 'Aucun compte trouvé avec cet email')

    if user.otp_verified and user.is_active:
        raise HttpError(400, 'Ce compte est déjà activé')

    # Anti-spam : refus si OTP encore valide pour plus de 8 minutes
    if user.otp_expires_at:
        remaining = (user.otp_expires_at - timezone.now()).total_seconds()
        if remaining > 8 * 60:
            raise HttpError(429, 'Un code OTP récent a déjà été envoyé. Attendez 2 minutes.')

    otp = user.generate_otp()
    _send_otp_email(user, otp)
    detail = f'Nouveau code OTP envoyé à {user.email}.'
    if django_settings.DEBUG:
        detail += f' [DEV] Code : {otp}'
    return {'detail': detail}


# ─── Gestion des utilisateurs (admin) ────────────────────────────────────────

@router.get('/users', response=List[UserOut])
def list_users(request, role: str = ''):
    if request.auth.role not in ('ADMIN', 'DOCTOR', 'RECEPTIONIST'):
        raise HttpError(403, 'Accès non autorisé')
    qs = User.objects.all()
    if role:
        qs = qs.filter(role=role)
    return list(qs.order_by('last_name', 'first_name'))


@router.patch('/users/{user_id}', response=UserOut)
def toggle_user(request, user_id: str):
    if request.auth.role != 'ADMIN':
        raise HttpError(403, 'Accès réservé aux administrateurs')
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    return user


# ─── Profil personnel ─────────────────────────────────────────────────────────

@router.get('/me', response=UserOut)
def get_me(request):
    return request.auth


@router.patch('/me', response=UserOut)
def update_profile(request, payload: UpdateProfileSchema):
    user = request.auth
    if payload.first_name:
        user.first_name = payload.first_name
    if payload.last_name:
        user.last_name = payload.last_name
    if payload.phone is not None:
        user.phone = payload.phone
    user.save()
    return user


@router.post('/change-password')
def change_password(request, payload: ChangePasswordSchema):
    user = request.auth
    if not user.check_password(payload.old_password):
        raise HttpError(400, 'Ancien mot de passe incorrect')
    user.set_password(payload.new_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=['password', 'password_changed_at'])
    create_audit_log(user, 'UPDATE', 'User', resource_id=user.id, ip_address=_get_ip(request))
    return {'detail': 'Mot de passe modifié avec succès'}


# ─── MFA ──────────────────────────────────────────────────────────────────────

@router.post('/mfa/setup', response=MFASetupOut)
def setup_mfa(request):
    user = request.auth
    secret = user.generate_mfa_secret()
    user.save(update_fields=['mfa_secret'])
    uri = user.get_mfa_uri()
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()
    return MFASetupOut(secret=secret, qr_uri=uri, qr_image_base64=qr_b64)


@router.post('/mfa/verify')
def verify_mfa(request, payload: MFAVerifySchema):
    user = request.auth
    if not user.mfa_secret:
        raise HttpError(400, 'MFA non configuré')
    if not user.verify_mfa_token(payload.token):
        raise HttpError(400, 'Code MFA invalide')
    user.mfa_enabled = True
    user.save(update_fields=['mfa_enabled'])
    return {'detail': 'MFA activé avec succès'}


@router.delete('/mfa/disable')
def disable_mfa(request, payload: MFAVerifySchema):
    user = request.auth
    if not user.verify_mfa_token(payload.token):
        raise HttpError(400, 'Code MFA invalide')
    user.mfa_enabled = False
    user.mfa_secret = ''
    user.save(update_fields=['mfa_enabled', 'mfa_secret'])
    return {'detail': 'MFA désactivé'}
