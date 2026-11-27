from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class NoticeModel(PublicIdMixin, Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # {locale: {"title": ..., "body": ...}}
    texts: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class NoticeAcknowledgementModel(Base):
    __tablename__ = "notice_acknowledgements"

    notice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notices.id", ondelete="CASCADE"), primary_key=True
    )
    # Deleting a user deletes their acknowledgements.
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    acknowledged_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
