"""
What this instance holds of the recipes paired instances share with it.

A mirror is a recipe row of its own (`Recipe.mirror_peer_id` set, no owner)
plus a `RecipeMirror` with the source's side of it: the document it was
built from, the source revision and author name, and what the source said
about allergens and diet markers beyond this instance's catalogue. A recipe
from a peer first waits as an `IncomingRecipe` until an administrator
accepts it; so does an update that brings catalogue entries without a
mapping. `CatalogueMapping` records, per peer, how each of the peer's
catalogue entries maps onto this instance's catalogue.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class IncomingStatus(StrValueEnum):
    PENDING = "pending"
    # Discarded by an administrator; later updates of the recipe do not
    # queue it again until an administrator reopens it.
    REJECTED = "rejected"


class IncomingKind(StrValueEnum):
    # No mirror of the recipe exists yet.
    NEW = "new"
    # An update of a mirror that brought catalogue entries without a
    # mapping; the mirror keeps its previous revision meanwhile.
    UPDATE = "update"


class MappingKind(StrValueEnum):
    UNIT = "unit"
    TAG = "tag"
    INGREDIENT = "ingredient"
    EQUIPMENT = "equipment"


class MappingAction(StrValueEnum):
    # Points at a local entry (found, chosen or created from the peer's data).
    MAP = "map"
    # An ingredient or equipment line kept as text with the source's data.
    PLAIN = "plain"
    # A unit left out (the amount keeps no unit) or a tag dropped.
    NONE = "none"


@dataclass(kw_only=True)
class RecipeMirror:
    recipe_id: int
    peer_id: int
    origin_public_id: UUID
    etag: str
    source_revision: str
    source_author_name: str | None = None
    # The `recipes.json` of the item as received.
    document: dict[str, Any] = field(default_factory=dict)
    # Source file id to the public id of the local stored file.
    files: dict[str, str] = field(default_factory=dict)
    # Plain-text lines, the source's allergens and markers per local
    # ingredient and the sub-recipes not mirrored here
    # (`application/services/mirror_facts.py` reads it).
    extras: dict[str, Any] = field(default_factory=dict)
    accepted_at: datetime
    updated_at: datetime


@dataclass(kw_only=True)
class IncomingRecipe(Entity):
    peer_id: int
    origin_public_id: UUID
    status: IncomingStatus
    kind: IncomingKind
    title: str
    author_name: str | None = None
    etag: str
    payload: bytes
    received_at: datetime
    decided_at: datetime | None = None


@dataclass(kw_only=True)
class CatalogueMapping:
    peer_id: int
    kind: MappingKind
    remote_id: str
    # None while no decision was made.
    action: MappingAction | None = None
    # The local entry's internal id for MappingAction.MAP.
    local_id: int | None = None
    created_here: bool = False
    # "seed_key" or "decision".
    matched_by: str | None = None
    remote_name: str = ""
    # The latest catalogue entry the peer sent, as in the format.
    remote_data: dict[str, Any] = field(default_factory=dict)
    updated: datetime

    @property
    def decided(self) -> bool:
        """A decision that still holds: a mapping whose local entry was
        deleted counts as undecided again."""
        if self.action is None:
            return False
        return self.action is not MappingAction.MAP or self.local_id is not None


@dataclass(frozen=True, kw_only=True)
class SuggestionDismissal:
    """A suggestion from a peer's catalogue data an administrator dismissed:
    one field of one of the peer's entries and a digest of the value the
    peer offered when it was dismissed."""

    peer_id: int
    kind: MappingKind
    remote_id: str
    field: str
    value_hash: str
    dismissed_at: datetime
