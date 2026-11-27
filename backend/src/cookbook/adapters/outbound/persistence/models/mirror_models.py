"""
What this instance holds of the recipes paired instances share with it: the
mirrors (`recipe_mirrors`, next to the recipe row of each mirror), the
recipes waiting for an administrator's decision (`peer_incoming_recipes`)
and, per peer, how its catalogue entries map onto this instance's catalogue
(`peer_catalogue_mappings`), and the suggestions from a peer's catalogue
data an administrator dismissed (`peer_suggestion_dismissals`). Everything
here goes with its peer's pairing.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import Uuid
from sqlalchemy import false
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from src.platform.adapters.outbound.persistence.models.base import Base
from src.platform.adapters.outbound.persistence.models.base import PublicIdMixin
from src.platform.adapters.outbound.persistence.types import JsonType
from src.platform.adapters.outbound.persistence.types import UtcDateTime


class RecipeMirrorModel(Base):
    """The source side of a mirror: which peer's recipe it is, the document
    it was last built from (so a corrected mapping can rebuild it) and what
    the source said about allergens and markers beyond the local catalogue."""

    __tablename__ = "recipe_mirrors"
    # One mirror per recipe of a peer.
    __table_args__ = (
        UniqueConstraint("peer_id", "origin_public_id", name="uq_recipe_mirrors_origin"),
    )

    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    origin_public_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    etag: Mapped[str] = mapped_column(String(160), nullable=False)
    source_revision: Mapped[str] = mapped_column(String(160), nullable=False)
    source_author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The `recipes.json` of the item as received, and the local stored file
    # each of its images became.
    document: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    files: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    # Derived when the mirror is built: plain-text lines, the source's
    # allergens and markers per local ingredient, unknown values.
    extras: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    accepted_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class IncomingRecipeModel(PublicIdMixin, Base):
    """A recipe from a peer that waits for an administrator: a new one, or
    an update of a mirror that brought catalogue entries without a mapping.
    A rejected one stays as a marker, so later updates do not queue it
    again."""

    __tablename__ = "peer_incoming_recipes"
    __table_args__ = (
        UniqueConstraint("peer_id", "origin_public_id", name="uq_peer_incoming_recipes_origin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    origin_public_id: Mapped[uuid.UUID] = mapped_column(Uuid(), nullable=False)
    # pending or rejected; new or update.
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    etag: Mapped[str] = mapped_column(String(160), nullable=False)
    # The `.cui` bytes as received, images included, until a decision.
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class PeerCatalogueMappingModel(Base):
    """How one catalogue entry of a peer maps onto this instance: to a local
    entry, as plain text, or to nothing (a unit left out, a tag dropped).
    `action` is null while no decision was made. The latest data the peer
    sent for the entry is kept for comparing it with the local entry."""

    __tablename__ = "peer_catalogue_mappings"

    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), primary_key=True
    )
    # unit, tag, ingredient or equipment.
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    remote_public_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # map, plain or none; null until decided.
    action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ingredient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tag_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True, index=True
    )
    equipment_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The local entry was created from the peer's data.
    created_here: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # seed_key when the seed keys matched, decision when an administrator
    # chose.
    matched_by: Mapped[str | None] = mapped_column(String(16), nullable=True)
    remote_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    remote_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    updated: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)


class PeerSuggestionDismissalModel(Base):
    """A suggestion from a peer's catalogue data that an administrator
    dismissed: one field of one of the peer's entries, with a digest of the
    value the peer offered then. The suggestion stays hidden while the peer
    offers that same value and shows again once it offers another."""

    __tablename__ = "peer_suggestion_dismissals"

    peer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peers.id", ondelete="CASCADE"), primary_key=True
    )
    # unit, tag, ingredient or equipment.
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    remote_public_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    field: Mapped[str] = mapped_column(String(64), primary_key=True)
    # SHA-256 of the offered value in hex.
    value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dismissed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
