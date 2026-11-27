from datetime import date
from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Date
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import false
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class CookEventModel(PublicIdMixin, Base):
    __tablename__ = "cook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cooked_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    variation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipe_variations.id", ondelete="SET NULL"), nullable=True, index=True
    )


class MealPlanEntryModel(PublicIdMixin, Base):
    __tablename__ = "meal_plan_entries"
    __table_args__ = (Index("ix_meal_plan_entries_user_date", "user_id", "plan_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot: Mapped[str] = mapped_column(String(16), nullable=False)
    # A deleted recipe leaves the entry as free text with its title.
    recipe_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    household_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("households.id", ondelete="CASCADE"), nullable=True, index=True
    )


class ShoppingListModel(PublicIdMixin, Base):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    # continuous or normal (ShoppingListMode).
    mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="normal", server_default="normal"
    )
    keep: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    last_activity_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    household_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
        index=True,
    )


class ShoppingListMemberModel(Base):
    __tablename__ = "shopping_list_members"

    list_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shopping_lists.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class ShoppingItemModel(PublicIdMixin, Base):
    __tablename__ = "shopping_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingredient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredient_categories.id", ondelete="SET NULL"), nullable=True
    )
    checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checked_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    checked_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    recipe_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    # The recipes whose amounts joined the item after `recipe_id`; plain
    # ids, so a deleted recipe only drops out of the label.
    extra_recipe_ids: Mapped[list[int]] = mapped_column(
        JsonType, nullable=False, default=list, server_default=sql_text("'[]'")
    )
    # Recipe ids, outermost first; plain ids, so a deleted sub-recipe only
    # drops out of the label.
    sub_recipe_path: Mapped[list[int]] = mapped_column(
        JsonType, nullable=False, default=list, server_default=sql_text("'[]'")
    )
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ShoppingListNoteModel(PublicIdMixin, Base):
    """An in-app note that an idle list deleted itself, one per former member."""

    __tablename__ = "shopping_list_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    list_name: Mapped[str] = mapped_column(String(128), nullable=False)
    idle_days: Mapped[int] = mapped_column(Integer, nullable=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
