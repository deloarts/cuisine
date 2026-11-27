"""
A variation of a recipe: someone's way of cooking it differently ("With
honey"), stored as differences to the original only. It belongs to the
recipe, is written in its author's language and is visible to whoever can see
the recipe, unless its author keeps it private.

The changes are stored as JSON objects that name ingredients, units,
equipment and sub-recipes by public id, so a variation survives the merge or
deletion of something it names: such a change simply no longer applies. Steps
are named by their number (from 1) in the recipe as it was at
`based_on_revision`; `services/variations.py` documents the shape and applies
the changes.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class RecipeVariation(Entity):
    recipe_id: int
    # None once the author's account was deleted and the variation stayed
    # online (see the deletion rules in docs/reference/cookbook.md).
    author_id: int | None
    name: str
    # The content locale the name, the note and every text are written in.
    locale: str
    created: datetime
    changed: datetime
    note: str = ""
    # Visible to its author only.
    private: bool = False
    # The recipe revision the step numbers refer to; None when the recipe
    # had no revision yet.
    based_on_revision: int | None = None
    changes: list[dict[str, Any]] = field(default_factory=list)
    # On a mirror: the variation's public id at the source instance, for a
    # variation that came with the mirrored recipe, and its author's display
    # name there (None when the author does not show it). Such a variation
    # is read only here.
    origin_public_id: UUID | None = None
    source_author_name: str | None = None

    @property
    def mirrored(self) -> bool:
        return self.origin_public_id is not None
