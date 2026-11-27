from datetime import datetime
from typing import Any

from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class UnitModel(PublicIdMixin, Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    # The key of the reference data the row was seeded from; None for rows
    # people created.
    seed_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    to_base: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class UnitTranslationModel(Base):
    __tablename__ = "unit_translations"

    unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("units.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    plural_name: Mapped[str] = mapped_column(String(64), nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(16), nullable=False)


class IngredientCategoryModel(PublicIdMixin, Base):
    __tablename__ = "ingredient_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The key of the reference data the row was seeded from; None for rows
    # people created.
    seed_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class IngredientCategoryTranslationModel(Base):
    __tablename__ = "ingredient_category_translations"

    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient_categories.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class IngredientFamilyModel(PublicIdMixin, Base):
    __tablename__ = "ingredient_families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seed_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class IngredientFamilyTranslationModel(Base):
    __tablename__ = "ingredient_family_translations"

    family_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredient_families.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class TagModel(PublicIdMixin, Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The key of the reference data the row was seeded from; None for rows
    # people created.
    seed_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class TagTranslationModel(Base):
    __tablename__ = "tag_translations"

    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class SeededKeyModel(Base):
    """Every reference key the startup seed ever inserted or adopted, so a
    row an administrator deleted or renamed is never seeded again."""

    __tablename__ = "seeded_keys"

    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    seeded_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    # The field values the seed last wrote into the row, for the per-field
    # merge of seed updates; None for keys remembered before bases existed.
    base: Mapped[dict[str, Any] | None] = mapped_column(JsonType, nullable=True)
