from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class SettingsModel(Base):
    """One row per settings section, holding the whole section as JSON. A
    missing field falls back to the dataclass default when read, so a new
    setting needs no migration."""

    __tablename__ = "settings"

    section: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[dict[str, object]] = mapped_column(JsonType, nullable=False, default=dict)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
