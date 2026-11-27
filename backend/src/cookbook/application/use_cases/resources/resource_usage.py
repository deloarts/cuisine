"""
How often the catalogue's items are used, for the resource and ingredient
tables. Tags, units, equipment and ingredients count the recipes that use
them, each recipe once and only the recipes the viewer may see (their own
drafts included, as in the recipe list). Categories and families count the
ingredients in them, which every signed-in user sees.
"""

from dataclasses import dataclass
from uuid import UUID

from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery
from src.cookbook.ports.outbound.repositories.usage_repository import IUsageRepository
from src.cookbook.ports.outbound.repositories.usage_repository import ResourceKind
from src.platform.domain.entities.user import User


@dataclass(frozen=True)
class ResourceUsage:
    """Per kind, every item's public id with its count, zero included."""

    tags: dict[UUID, int]
    units: dict[UUID, int]
    categories: dict[UUID, int]
    families: dict[UUID, int]
    equipment: dict[UUID, int]


class ReadResourceUsage:
    def __init__(self, *, usage_repo: IUsageRepository, viewers: ViewerResolver) -> None:
        self._usage = usage_repo
        self._viewers = viewers

    async def _visible(self, actor: User) -> RecipeQuery:
        viewer = await self._viewers.of(actor)
        return RecipeQuery(
            viewer_id=actor.id,
            viewer_group_ids=sorted(viewer.group_ids),
            viewer_household_member_ids=sorted(viewer.household_member_ids),
        )

    async def _keyed(self, kind: ResourceKind, counts: dict[int, int]) -> dict[UUID, int]:
        return {
            public_id: counts.get(item_id, 0)
            for item_id, public_id in (await self._usage.public_ids(kind)).items()
        }

    async def resources(self, actor: User) -> ResourceUsage:
        query = await self._visible(actor)
        return ResourceUsage(
            tags=await self._keyed("tag", await self._usage.recipe_counts(query, "tag")),
            units=await self._keyed("unit", await self._usage.recipe_counts(query, "unit")),
            categories=await self._keyed(
                "category", await self._usage.ingredient_counts("category")
            ),
            families=await self._keyed("family", await self._usage.ingredient_counts("family")),
            equipment=await self._keyed(
                "equipment", await self._usage.recipe_counts(query, "equipment")
            ),
        )

    async def ingredients(self, actor: User, ids: list[int] | None = None) -> dict[int, int]:
        """Per ingredient, the visible recipes using it in a step or in the
        declared list; `ids` limits the count to those ingredients."""
        return await self._usage.recipe_counts(await self._visible(actor), "ingredient", ids)
