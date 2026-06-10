import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings


def _get_fernet():
    key = settings.AES_ENCRYPTION_KEY.encode()
    # Dérive une clé Fernet de 32 bytes depuis la clé configurée
    key_32 = hashlib.sha256(key).digest()
    fernet_key = base64.urlsafe_b64encode(key_32)
    return Fernet(fernet_key)


def encrypt(value: str) -> str:
    if not value:
        return value
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return value
    f = _get_fernet()
    return f.decrypt(value.encode()).decode()


class EncryptedField:
    """Descriptor pour chiffrer/déchiffrer automatiquement les champs sensibles."""

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f'_encrypted_{name}'

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        raw = getattr(obj, self.private_name, None)
        if raw:
            return decrypt(raw)
        return None

    def __set__(self, obj, value):
        if value:
            setattr(obj, self.private_name, encrypt(value))
        else:
            setattr(obj, self.private_name, None)
