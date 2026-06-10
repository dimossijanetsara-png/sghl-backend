import base64
import io
import qrcode
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import create_audit_log
from .models import RefreshTokenBlacklist
from .schemas import (
    LoginSchema, TokenSchema, RefreshSchema, RegisterSchema,
    UserOut, MFASetupOut, MFAVerifySchema, ChangePasswordSchema, UpdateProfileSchema,
)

User = get_user_model()
router = Router()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR', '')


@router.post('/login', response=TokenSchema, auth=None)
def login(request, payload: LoginSchema):
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        create_audit_log(None, 'LOGIN_FAILED', 'User', extra={'email': payload.email}, ip_address=_get_ip(request))
        raise HttpError(401, 'Identifiants invalides')

    if user.is_account_locked():
        raise HttpError(423, 'Compte temporairement verrouillé. Réessayez plus tard.')

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


@router.post('/register', response=UserOut)
def register(request, payload: RegisterSchema):
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
    )
    create_audit_log(request.auth, 'CREATE', 'User', resource_id=user.id, ip_address=_get_ip(request))
    return user


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
