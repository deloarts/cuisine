from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class LegalVersionModel(PublicIdMixin, Base):
    """One published version of the imprint or the privacy statement.
    Versions are only ever added, never changed."""

    __tablename__ = "legal_versions"
    __table_args__ = (UniqueConstraint("kind", "version", name="uq_legal_versions_kind_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # {locale: markdown}
    texts: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    # {"mode": ..., "default_visibility": ..., "allow_public_recipes": ...,
    # "peering_enabled": ...} on privacy statement versions.
    privacy_mode: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
    published_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    published_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
