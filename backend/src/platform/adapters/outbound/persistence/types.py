"""
Column types shared by the models, written so the same schema runs on
Postgres in production and on SQLite in the test suite.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from src.platform.infrastructure.logging.logger import log
from src.platform.infrastructure.security.secret_box import SecretDecryptionError
from src.platform.infrastructure.security.secret_box import decrypt_secret
from src.platform.infrastructure.security.secret_box import encrypt_secret
from src.shared_kernel.domain.services.clock import as_utc

# JSONB on Postgres, plain JSON elsewhere.
JsonType = JSON().with_variant(JSONB(), "postgresql")


class UtcDateTime(TypeDecorator[datetime]):
    """A timezone-aware UTC datetime on every backend. SQLite drops the
    zone on the way in, so values are read back as UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return as_utc(value)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return as_utc(value)


class EncryptedString(TypeDecorator[str]):
    """A string encrypted at rest with secret_box. The domain only ever sees
    the plain value. A value no configured key can decrypt, usually because
    the encryption key was changed without keeping the old one, loads as
    unset and logs an error, so the row stays readable: a TOTP secret then
    has to be enrolled again instead of locking its user out of the app."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if not value:
            return value
        return encrypt_secret(value)

    def process_result_value(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        text = str(value)
        if not text:
            return text
        try:
            return decrypt_secret(text)
        except SecretDecryptionError:
            log.error("A stored secret could not be decrypted with the configured keys.")
            return None
