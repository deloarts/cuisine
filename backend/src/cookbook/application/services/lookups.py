"""Loads the units, tags, categories, ingredients, equipment and sub-recipes
a set of records refers to, once per request, so derivation and presentation never
query per row."""

from collections.abc import Iterable

from src.cookbook.application.dto.views import Lookups
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.sub_recipes import MAX_DEPTH
from src.cookbook.domain.services.sub_recipes import all_ingredient_ids
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository


class LookupLoader:
    def __init__(
        self,
        *,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        ingredient_repo: IIngredientRepository,
        recipe_repo: IRecipeRepository,
        family_repo: IIngredientFamilyRepository,
        equipment_repo: IEquipmentRepository,
    ) -> None:
        self._equipment = equipment_repo
        self._families = family_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._categories = category_repo
        self._ingredients = ingredient_repo
        self._recipes = recipe_repo

    async def load(self, ingredient_ids: Iterable[int] = ()) -> Lookups:
        return Lookups(
            units={u.id: u for u in await self._units.list_all()},
            tags={t.id: t for t in await self._tags.list_all()},
            categories={c.id: c for c in await self._categories.list_all()},
            families={f.id: f for f in await self._families.list_all()},
            ingredients={
                i.id: i for i in await self._ingredients.get_many(sorted(set(ingredient_ids)))
            },
        )

    async def sub_recipes(self, recipes: Iterable[Recipe]) -> dict[int, Recipe]:
        """Every sub-recipe below `recipes`, one query per level."""
        found: dict[int, Recipe] = {}
        frontier = {s for r in recipes for s in r.sub_recipe_ids}
        for _ in range(MAX_DEPTH + 1):
            wanted = sorted(frontier - set(found))
            if not wanted:
                break
            loaded = await self._recipes.get_many(wanted)
            found.update({r.id: r for r in loaded})
            frontier = {s for r in loaded for s in r.sub_recipe_ids}
        return found

    async def load_for(self, recipes: Iterable[Recipe]) -> Lookups:
        """Everything `recipes` and their sub-recipes refer to."""
        given = list(recipes)
        tree = await self.sub_recipes(given)
        everything = {**tree, **{r.id: r for r in given}}
        ingredient_ids = {i for r in given for i in all_ingredient_ids(r, everything)}
        lookups = await self.load(ingredient_ids)
        lookups.recipes = tree
        equipment_ids = {e for r in everything.values() for e in r.equipment_ids}
        lookups.equipment = {e.id: e for e in await self._equipment.get_many(sorted(equipment_ids))}
        return lookups
