from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import false
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class EquipmentModel(PublicIdMixin, Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The key of the reference data the row was seeded from; None for rows
    # people or agents created.
    seed_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    basic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class EquipmentTranslationModel(Base):
    __tablename__ = "equipment_translations"

    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class EquipmentAliasModel(Base):
    """Another name of an item in one locale. The use case keeps it unique
    per locale across every catalogue name and alias."""

    __tablename__ = "equipment_aliases"

    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    alias: Mapped[str] = mapped_column(String(128), primary_key=True)


class StepEquipmentModel(PublicIdMixin, Base):
    __tablename__ = "step_equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    step_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipe_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StepEquipmentTranslationModel(Base):
    __tablename__ = "step_equipment_translations"

    step_equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("step_equipment.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    note: Mapped[str] = mapped_column(String(255), nullable=False)


class KitchenModel(PublicIdMixin, Base):
    """The equipment a household or a single cook owns: exactly one of the
    two owners is set, and each has at most one kitchen."""

    __tablename__ = "kitchens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    household_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("households.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    set_up_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class KitchenEquipmentModel(Base):
    __tablename__ = "kitchen_equipment"

    kitchen_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kitchens.id", ondelete="CASCADE"), primary_key=True
    )
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), primary_key=True, index=True
    )
