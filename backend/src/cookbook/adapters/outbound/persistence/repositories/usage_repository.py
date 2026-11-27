"""How often the catalogue's items are used: by the recipes a viewer may
see, or for categories and families by the ingredients in them. Each count
is one grouped query."""

from typing import Any
from typing import Literal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import union
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.equipment_models import EquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import StepEquipmentModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeStepModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeTagModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import StepIngredientModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientCategoryModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import IngredientFamilyModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import TagModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import UnitModel
from src.cookbook.adapters.outbound.persistence.repositories.recipe_repository import (
    SqlAlchemyRecipeRepository,
)
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery
from src.cookbook.ports.outbound.repositories.usage_repository import RecipeUsageKind
from src.cookbook.ports.outbound.repositories.usage_repository import ResourceKind

_RESOURCES: dict[ResourceKind, Any] = {
    "tag": TagModel,
    "unit": UnitModel,
    "category": IngredientCategoryModel,
    "family": IngredientFamilyModel,
    "equipment": EquipmentModel,
}


def _lines(column: str) -> Any:
    """Pairs of (item id, recipe id) from the step lines and the declared
    lines, for the ingredient or unit column both share. A unit also counts
    for the recipes whose yield is given in it."""
    in_steps = (
        select(getattr(StepIngredientModel, column).label("item_id"), RecipeStepModel.recipe_id)
        .join(RecipeStepModel, RecipeStepModel.id == StepIngredientModel.step_id)
        .where(getattr(StepIngredientModel, column).is_not(None))
    )
    declared = select(
        getattr(RecipeIngredientModel, column).label("item_id"), RecipeIngredientModel.recipe_id
    ).where(getattr(RecipeIngredientModel, column).is_not(None))
    if column != "unit_id":
        return union(in_steps, declared).subquery()
    yields = select(
        RecipeModel.yield_unit_id.label("item_id"), RecipeModel.id.label("recipe_id")
    ).where(RecipeModel.yield_unit_id.is_not(None))
    return union(in_steps, declared, yields).subquery()


def _pairs(kind: RecipeUsageKind) -> Any:
    if kind == "tag":
        return select(RecipeTagModel.tag_id.label("item_id"), RecipeTagModel.recipe_id).subquery()
    if kind == "equipment":
        return (
            select(StepEquipmentModel.equipment_id.label("item_id"), RecipeStepModel.recipe_id)
            .join(RecipeStepModel, RecipeStepModel.id == StepEquipmentModel.step_id)
            .subquery()
        )
    return _lines("unit_id" if kind == "unit" else "ingredient_id")


class SqlAlchemyUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session
        self._recipes = SqlAlchemyRecipeRepository(session)

    async def recipe_counts(
        self, query: RecipeQuery, kind: RecipeUsageKind, ids: list[int] | None = None
    ) -> dict[int, int]:
        if ids is not None and not ids:
            return {}
        pairs = _pairs(kind)
        stmt = (
            select(pairs.c.item_id, func.count(func.distinct(pairs.c.recipe_id)))
            .where(pairs.c.recipe_id.in_(self._recipes.visible_ids(query)))
            .group_by(pairs.c.item_id)
        )
        if ids is not None:
            stmt = stmt.where(pairs.c.item_id.in_(sorted(set(ids))))
        return {int(item): int(n) for item, n in (await self._db.execute(stmt)).all()}

    async def ingredient_counts(self, by: Literal["category", "family"]) -> dict[int, int]:
        column = IngredientModel.category_id if by == "category" else IngredientModel.family_id
        stmt = (
            select(column, func.count(IngredientModel.id))
            .where(
                column.is_not(None),
                IngredientModel.status != IngredientStatus.ARCHIVED.value,
            )
            .group_by(column)
        )
        return {int(item): int(n) for item, n in (await self._db.execute(stmt)).all()}

    async def public_ids(self, kind: ResourceKind) -> dict[int, UUID]:
        model = _RESOURCES[kind]
        rows = await self._db.execute(select(model.id, model.public_id))
        return {int(i): p for i, p in rows.all()}
