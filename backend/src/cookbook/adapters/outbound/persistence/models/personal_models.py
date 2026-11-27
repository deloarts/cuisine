from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class RecipeFavouriteModel(Base):
    __tablename__ = "recipe_favourites"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class RecipeRatingModel(PublicIdMixin, Base):
    """One rating per user for the recipe itself (no variation) and one per
    variation; a NULL never collides in a unique constraint, so the first
    case is a partial unique index."""

    __tablename__ = "recipe_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "variation_id"),
        Index(
            "uq_recipe_ratings_user_id_recipe_id_original",
            "user_id",
            "recipe_id",
            unique=True,
            postgresql_where=sql_text("variation_id IS NULL"),
            sqlite_where=sql_text("variation_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipe_variations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class RecipeNoteModel(PublicIdMixin, Base):
    __tablename__ = "recipe_notes"
    # The unique constraint starts with user_id, so lookups and cascading
    # deletes by recipe need an index of their own.
    __table_args__ = (
        UniqueConstraint("user_id", "recipe_id"),
        Index("ix_recipe_notes_recipe_id", "recipe_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class FoodRestrictionModel(PublicIdMixin, Base):
    __tablename__ = "food_restrictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    allergen: Mapped[str | None] = mapped_column(String(32), nullable=True)
    diet: Mapped[str | None] = mapped_column(String(32), nullable=True)
    family_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredient_families.id", ondelete="CASCADE"), nullable=True
    )
    ingredient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=True
    )
    note: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
