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
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class AgentCallModel(PublicIdMixin, Base):
    __tablename__ = "agent_calls"
    __table_args__ = (
        Index("ix_agent_calls_token_called_at", "token_kind", "token_id", "called_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    called_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    token_id: Mapped[int] = mapped_column(Integer, nullable=False)
    token_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_refs: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result: Mapped[Any] = mapped_column(JsonType, nullable=True)
    is_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
