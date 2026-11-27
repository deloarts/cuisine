from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import EncryptedString
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class WebhookSubscriptionModel(PublicIdMixin, Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    events: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    secret: Mapped[str] = mapped_column(EncryptedString(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class WebhookDeliveryModel(PublicIdMixin, Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_status_next", "status", "next_attempt_at"),
        Index("ix_webhook_deliveries_subscription_created", "subscription_id", "created"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    # Deleting the user the payload describes deletes the delivery.
    subject_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
