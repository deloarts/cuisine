"""
Which public id each step, ingredient line, equipment line and line of the
declared ingredient list gets when a recipe is saved. A save replaces the
steps as a whole, yet a step or line the request names by an id the recipe
already uses keeps that id, so links and later updates can point at it. Any
other id, including one of another recipe or another instance, is ignored
and the row gets a fresh one, so a request can never take over or collide
with a row it does not own.

An import names steps and lines by their ids at the source instead. Those
are never taken over; each becomes `uuid5(<local recipe public id>,
"<kind>:<source id>")`, so importing the same source step into the same
local recipe again (updating an earlier import) gives it the same id, while
another recipe, a new copy included, gets other ids.
"""

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from uuid import UUID
from uuid import uuid4
from uuid import uuid5

from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepIngredient


def _parse(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


@dataclass
class IdKeeper:
    """Hands out the ids of one kind of row for one save: a requested id the
    recipe already uses, once, and a fresh one otherwise."""

    kind: str = ""
    known: set[UUID] = field(default_factory=set)
    used: set[UUID] = field(default_factory=set)
    # Set for an import: requested ids are source ids and turn into ids
    # derived from this namespace, the local recipe's public id.
    source_namespace: UUID | None = None

    def take(self, requested: object) -> UUID:
        parsed = _parse(requested)
        if parsed is not None and self.source_namespace is not None:
            derived = uuid5(self.source_namespace, f"{self.kind}:{parsed}")
            if derived not in self.used:
                self.used.add(derived)
                return derived
        elif parsed is not None and parsed in self.known and parsed not in self.used:
            self.used.add(parsed)
            return parsed
        fresh = uuid4()
        self.used.add(fresh)
        return fresh


@dataclass
class StepIdKeepers:
    steps: IdKeeper = field(default_factory=lambda: IdKeeper(kind="step"))
    lines: IdKeeper = field(default_factory=lambda: IdKeeper(kind="line"))
    equipment: IdKeeper = field(default_factory=lambda: IdKeeper(kind="equipment"))
    # The lines of the recipe's declared ingredient list.
    declared: IdKeeper = field(default_factory=lambda: IdKeeper(kind="declared"))

    def derive_from_source(self, recipe_public_id: UUID) -> None:
        """Treats every requested id as a source id of an import into the
        recipe with this public id."""
        for keeper in (self.steps, self.lines, self.equipment, self.declared):
            keeper.source_namespace = recipe_public_id

    def know_declared(self, lines: Iterable[StepIngredient]) -> None:
        """Accepts the ids of the recipe's current declared lines."""
        self.declared.known.update(line.public_id for line in lines)

    def know_steps(self, steps: Iterable[RecipeStep]) -> None:
        """Accepts the ids of the recipe's current steps and lines."""
        for step in steps:
            self.steps.known.add(step.public_id)
            self.lines.known.update(si.public_id for si in step.ingredients)
            self.equipment.known.update(se.public_id for se in step.equipment)

    def know_snapshot(self, snapshot: Mapping[str, Any]) -> None:
        """Accepts the ids a revision snapshot of the same recipe recorded,
        so a restore brings back the steps and lines it had."""
        for line in snapshot.get("ingredients", []):
            if (found := _parse(line.get("id"))) is not None:
                self.declared.known.add(found)
        for step in snapshot.get("steps", []):
            if (found := _parse(step.get("id"))) is not None:
                self.steps.known.add(found)
            for si in step.get("ingredients", []):
                if (found := _parse(si.get("id"))) is not None:
                    self.lines.known.add(found)
            for se in step.get("equipment", []):
                if (found := _parse(se.get("id"))) is not None:
                    self.equipment.known.add(found)
