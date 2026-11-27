from datetime import datetime

from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class IngredientModel(PublicIdMixin, Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The key of the reference data the row was seeded from; None for rows
    # people created.
    seed_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_locale: Mapped[str] = mapped_column(String(8), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredient_categories.id", ondelete="SET NULL"), nullable=True
    )
    family_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingredient_families.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Nutrition per 100 g; kcal for energy, grams for the rest.
    kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat: Mapped[float | None] = mapped_column(Float, nullable=True)
    saturated_fat: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbohydrates: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar: Mapped[float | None] = mapped_column(Float, nullable=True)
    fibre: Mapped[float | None] = mapped_column(Float, nullable=True)
    salt: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Extended nutrients per 100 g by catalogue key; a missing key is unknown.
    extended_nutrition: Mapped[dict[str, float]] = mapped_column(
        JsonType, nullable=False, default=dict, server_default=text("'{}'")
    )
    # Months 1 to 12 when the ingredient is in season; empty means not seasonal.
    season_months: Mapped[list[int]] = mapped_column(
        JsonType, nullable=False, default=list, server_default=text("'[]'")
    )
    density_g_per_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    allergens: Mapped[list[str]] = mapped_column(JsonType, nullable=False, default=list)
    diet_markers: Mapped[list[str]] = mapped_column(
        JsonType, nullable=False, default=list, server_default=text("'[]'")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    nutrition_source: Mapped[str] = mapped_column(String(16), nullable=False)
    usda_fdc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class IngredientTranslationModel(Base):
    __tablename__ = "ingredient_translations"

    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plural_name: Mapped[str] = mapped_column(String(128), nullable=False)


class IngredientAliasModel(Base):
    """Another name of an ingredient in one locale. The use case keeps an
    alias unique per locale across main names and aliases."""

    __tablename__ = "ingredient_aliases"

    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    alias: Mapped[str] = mapped_column(String(128), primary_key=True)


class IngredientConversionModel(Base):
    __tablename__ = "ingredient_conversions"

    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True
    )
    unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("units.id", ondelete="RESTRICT"), primary_key=True
    )
    grams: Mapped[float] = mapped_column(Float, nullable=False)
