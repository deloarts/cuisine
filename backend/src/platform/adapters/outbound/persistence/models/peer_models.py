from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Uuid
from sqlalchemy import false
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import EncryptedString
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class PeerModel(PublicIdMixin, Base):
    __tablename__ = "peers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # One record per instance; pairing again after a revoke reuses it.
    instance_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    app_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    protocol_version: Mapped[int] = mapped_column(Integer, nullable=False)
    format_versions: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    capabilities: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    revoked_by: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Empty strings once revoked.
    inbound_secret: Mapped[str] = mapped_column(EncryptedString(512), nullable=False)
    outbound_secret: Mapped[str] = mapped_column(EncryptedString(512), nullable=False)
    users_may_share: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accept_incoming: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_all: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    mirror_visibility: Mapped[str] = mapped_column(String(16), nullable=False)
    mirror_group_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user_groups.id", ondelete="SET NULL"), nullable=True
    )
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    paired_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class PeerInvitationModel(PublicIdMixin, Base):
    __tablename__ = "peer_invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    peer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="SET NULL"), nullable=True
    )
