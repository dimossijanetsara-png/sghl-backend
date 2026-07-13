from functools import wraps
from ninja.errors import HttpError

ROLE_PERMISSIONS = {
    'ADMIN': {
        'users:read', 'users:write', 'users:delete',
        'patients:read', 'patients:write', 'patients:delete',
        'clinical:read', 'clinical:write',
        'hospitalization:read', 'hospitalization:write',
        'nursing:read', 'nursing:write',
        'laboratory:read', 'laboratory:write', 'laboratory:validate',
        'pharmacy:read', 'pharmacy:write',
        'billing:read', 'billing:write',
        'hr:read', 'hr:write',
        'appointments:read', 'appointments:write',
        'dashboard:read', 'audit:read',
    },
    'DOCTOR': {
        'patients:read', 'patients:write',
        'clinical:read', 'clinical:write',
        'hospitalization:read', 'hospitalization:write',
        'nursing:read',
        'laboratory:read', 'laboratory:write',
        'pharmacy:read',
        'appointments:read', 'appointments:write',
        'dashboard:read',
    },
    'NURSE': {
        'patients:read',
        'clinical:read',
        'hospitalization:read',
        'nursing:read', 'nursing:write',
        'laboratory:read',
        'pharmacy:read',
        'appointments:read',
    },
    'BIOLOGIST': {
        'patients:read',
        'laboratory:read', 'laboratory:write', 'laboratory:validate',
    },
    'PHARMACIST': {
        'patients:read',
        'clinical:read',
        'pharmacy:read', 'pharmacy:write',
    },
    'RECEPTIONIST': {
        'patients:read', 'patients:write',
        'hospitalization:read',
        'appointments:read', 'appointments:write',
        'billing:read',
    },
    'ACCOUNTANT': {
        'billing:read', 'billing:write',
        'dashboard:read',
    },
    'PATIENT': {
        'appointments:read', 'appointments:write',
        'clinical:read',
        'laboratory:read',
    },
    'LABTECH': {
        'patients:read',
        'laboratory:read', 'laboratory:write',
    },
    'OTHER': {
        'patients:read',
        'appointments:read',
        'dashboard:read',
    },
}


def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user if hasattr(request, 'user') else request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, 'Authentification requise')
            user_perms = ROLE_PERMISSIONS.get(user.role, set())
            if permission not in user_perms:
                raise HttpError(403, f'Permission refusée : {permission} requis')
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_roles(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user if hasattr(request, 'user') else request.auth
            if not user or not user.is_authenticated:
                raise HttpError(401, 'Authentification requise')
            if user.role not in roles:
                raise HttpError(403, f'Rôle requis : {", ".join(roles)}')
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
