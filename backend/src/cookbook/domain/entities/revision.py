"""
A recipe revision: the editable content of a recipe at one moment, kept so
people can see what changed and go back. Revisions are immutable; they are
only deleted with their recipe (or by the retention setting).
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import RevisionKind
from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class RecipeRevision(Entity):
    recipe_id: int
    # 1, 2, 3 per recipe.
    number: int
    kind: RevisionKind
    created: datetime
    created_via: CreatedVia = CreatedVia.WEB
    # None once the author's account was deleted.
    author_id: int | None = None
    # The revision a restore went back to.
    restored_from: int | None = None
    note: str | None = None
    # On an `adopted` revision: the author of the variation whose changes
    # were taken over. None otherwise or once the account was deleted.
    credited_author_id: int | None = None
    # The content (`revisions.build_snapshot`); JSON-compatible values only.
    snapshot: dict[str, Any] = field(default_factory=dict)
