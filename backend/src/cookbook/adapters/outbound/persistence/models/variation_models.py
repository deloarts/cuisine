import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Uuid
from sqlalchemy import false
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class RecipeVariationModel(PublicIdMixin, Base):
    """A variation of a recipe; its changes are JSON naming records by
    public id (domain/entities/variation.py)."""

    __tablename__ = "recipe_variations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Deleting an account settles its variations first; whatever is left
    # goes with the account.
    author_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    private: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    based_on_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, nullable=False)
    created: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    changed: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    # A variation that came with a mirror: its public id at the source and
    # its author's display name there.
    origin_public_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    source_author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
