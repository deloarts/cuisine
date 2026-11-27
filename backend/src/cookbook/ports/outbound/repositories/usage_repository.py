from typing import Literal
from typing import Protocol
from uuid import UUID

from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery

# What a recipe uses: its tags, the units and ingredients of its step and
# declared lines, and the equipment of its steps.
RecipeUsageKind = Literal["tag", "unit", "ingredient", "equipment"]
# The resources whose ids `public_ids` maps.
ResourceKind = Literal["tag", "unit", "category", "family", "equipment"]


class IUsageRepository(Protocol):
    async def recipe_counts(
        self, query: RecipeQuery, kind: RecipeUsageKind, ids: list[int] | None = None
    ) -> dict[int, int]:
        """Per item of `kind`, how many of the recipes the query matches use
        it, each recipe once. Items without a use are left out; `ids`
        limits the count to those items."""
        ...

    async def ingredient_counts(self, by: Literal["category", "family"]) -> dict[int, int]:
        """Per category or family, how many ingredients of the catalogue
        (every one but the archived) belong to it."""
        ...

    async def public_ids(self, kind: ResourceKind) -> dict[int, UUID]:
        """Every item of `kind`, internal id to public id."""
        ...
