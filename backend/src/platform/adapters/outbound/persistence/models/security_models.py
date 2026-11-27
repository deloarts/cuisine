"""Sessions, trusted devices, passkeys, tokens and the security log."""

from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


def _user_fk(*, nullable: bool = False) -> Mapped[int]:
    return mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL" if nullable else "CASCADE"),
        nullable=nullable,
        index=True,
    )


class UserSessionModel(PublicIdMixin, Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = _user_fk()
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class TrustedDeviceModel(PublicIdMixin, Base):
    __tablename__ = "trusted_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = _user_fk()
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class PasskeyModel(PublicIdMixin, Base):
    __tablename__ = "passkeys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = _user_fk()
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    backed_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transports: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class PersonalAccessTokenModel(PublicIdMixin, Base):
    __tablename__ = "personal_access_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = _user_fk()
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class ApiKeyModel(PublicIdMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    service_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    creator_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class SecurityEventModel(PublicIdMixin, Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[int | None] = _user_fk(nullable=True)
    target_user_id: Mapped[int | None] = _user_fk(nullable=True)
    detail: Mapped[dict[str, object]] = mapped_column(JsonType, nullable=False, default=dict)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
