import uuid
from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy import false
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class RecipeModel(PublicIdMixin, Base):
    __tablename__ = "recipes"
    # One recipe per source recipe and owner, so every cook may hold their own
    # import of the same recipe; rows without an origin or an owner hold NULLs,
    # which never collide. The two origin columns are set together or not at
    # all.
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "origin_instance_id", "origin_public_id", name="uq_recipes_origin"
        ),
        CheckConstraint(
            "(origin_instance_id IS NULL) = (origin_public_id IS NULL)", name="origin_pair"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(
        String(16), nullable=False, default="instance", server_default="instance"
    )
    original_locale: Mapped[str] = mapped_column(String(8), nullable=False)
    base_servings: Mapped[int] = mapped_column(Integer, nullable=False)
    prep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cook_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    cover_file_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_via: Mapped[str] = mapped_column(String(16), nullable=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    yield_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    yield_unit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    # The recipe this one was copied from; cleared when that one is deleted.
    based_on_recipe_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The source of an imported or mirrored recipe: the source instance's id
    # and the recipe's public id there.
    origin_instance_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    origin_public_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    # A mirror of a recipe a paired instance shares with this one: the peer
    # it came from (`recipe_mirrors` holds the rest).
    mirror_peer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Mirrors and copies of mirrors never go to a paired instance and are
    # never public.
    peer_capped: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )


class RecipeTranslationModel(Base):
    __tablename__ = "recipe_translations"

    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tips: Mapped[str] = mapped_column(Text, nullable=False, default="")


class RecipeTagModel(Base):
    __tablename__ = "recipe_tags"

    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class RecipeUserShareModel(Base):
    __tablename__ = "recipe_user_shares"

    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class RecipeGroupShareModel(Base):
    __tablename__ = "recipe_group_shares"

    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class RecipePeerShareModel(Base):
    """A paired instance the owner shares the recipe with."""

    __tablename__ = "recipe_peer_shares"

    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class RecipeCoEditorModel(Base):
    """A person the owner lets edit the recipe's content."""

    __tablename__ = "recipe_co_editors"

    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class RecipeStepModel(PublicIdMixin, Base):
    __tablename__ = "recipe_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_file_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stored_files.id", ondelete="SET NULL"), nullable=True
    )


class RecipeStepTranslationModel(Base):
    __tablename__ = "recipe_step_translations"

    step_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipe_steps.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)


class StepIngredientModel(PublicIdMixin, Base):
    __tablename__ = "step_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    step_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipe_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # A catalogue ingredient or a sub-recipe, exactly one.
    ingredient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    sub_recipe_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )


class StepIngredientTranslationModel(Base):
    __tablename__ = "step_ingredient_translations"

    step_ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("step_ingredients.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    note: Mapped[str] = mapped_column(String(255), nullable=False)


class RecipeIngredientModel(PublicIdMixin, Base):
    """A line of the ingredient list the cook declared for the whole recipe,
    next to the lines of its steps."""

    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # A catalogue ingredient or a sub-recipe, exactly one.
    ingredient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    sub_recipe_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )


class RecipeIngredientTranslationModel(Base):
    __tablename__ = "recipe_ingredient_translations"

    recipe_ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipe_ingredients.id", ondelete="CASCADE"), primary_key=True
    )
    locale: Mapped[str] = mapped_column(String(8), primary_key=True)
    note: Mapped[str] = mapped_column(String(255), nullable=False)
