"""OAuth clients, grants (the connected apps) and their tokens."""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class OAuthClientModel(PublicIdMixin, Base):
    __tablename__ = "oauth_clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    secret_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    client_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    redirect_uris: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    auth_method: Mapped[str] = mapped_column(String(32), nullable=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    last_grant_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class OAuthGrantModel(PublicIdMixin, Base):
    __tablename__ = "oauth_grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permissions: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class OAuthTokenModel(PublicIdMixin, Base):
    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("oauth_grants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
