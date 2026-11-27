"""
Symmetric encryption for secrets the app must read back in plaintext, such
as TOTP secrets and the SMTP password, so they cannot be hashed like a
password. Encrypting them at rest keeps them out of database dumps, backups
and SQL-injection reads.

HKDF-SHA256 derives the Fernet key from cfg.security.encryption_key, so any
sufficiently random string works. Fernet is authenticated, so a tampered or
foreign value fails to decrypt instead of returning garbage. Stored values
carry the `enc:v1:` prefix. For rotation, set the old key as
encryption_key_previous: MultiFernet decrypts with either and encrypts with
the new one.
"""

import base64
from functools import cache

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from cryptography.fernet import MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.platform.infrastructure.config.settings import cfg

ENCRYPTED_PREFIX = "enc:v1:"
_HKDF_INFO = b"cuisine-secret-at-rest-v1"


class SecretDecryptionError(Exception):
    """A stored secret could not be decrypted with any configured key."""


@cache
def _fernet_for(secret: str) -> Fernet:
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_HKDF_INFO).derive(
        secret.encode("utf-8")
    )
    return Fernet(base64.urlsafe_b64encode(derived))


def _box() -> MultiFernet:
    keys = [_fernet_for(cfg.security.encryption_key)]
    if cfg.security.encryption_key_previous:
        keys.append(_fernet_for(cfg.security.encryption_key_previous))
    return MultiFernet(keys)


def encrypt_secret(plain: str) -> str:
    return ENCRYPTED_PREFIX + _box().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(stored: str) -> str:
    if not stored.startswith(ENCRYPTED_PREFIX):
        raise SecretDecryptionError("Value is not an encrypted secret.")
    token = stored[len(ENCRYPTED_PREFIX) :].encode("ascii")
    try:
        return _box().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise SecretDecryptionError("No configured encryption key matches.") from exc
