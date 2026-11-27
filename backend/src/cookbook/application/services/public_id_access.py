"""
The read rules and pages of the cookbook's kinds for Platform's public id
resolver (`IPublicIdAccess`), registered from the composition root
(src/bootstrap/public_ids.py). Each applies the rule the kind's own reads
apply, and answers None for whatever the user may not open, which the
resolver answers like an unknown id.
"""

from uuid import UUID

from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.ports.outbound.repositories.cooking_repositories import IShoppingListRepository
from src.cookbook.ports.outbound.repositories.equipment_repository import IKitchenRepository
from src.cookbook.ports.outbound.repositories.household_repository import IHouseholdRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.user import User


class RecipeAccess:
    """A recipe opens for whoever may see it (`can_view_recipe`)."""

    def __init__(self, *, recipe_repo: IRecipeRepository, viewers: ViewerResolver) -> None:
        self._recipes = recipe_repo
        self._viewers = viewers

    async def route(self, actor: User, public_id: UUID) -> str | None:
        recipe = await self._recipes.get_by_public_id(str(public_id))
        if recipe is None or not can_view_recipe(await self._viewers.of(actor), recipe):
            return None
        return f"/recipes/{recipe.public_id}"


class VariationAccess:
    """A variation opens on its recipe's page for whoever may see it
    (`can_view_variation`)."""

    def __init__(
        self,
        *,
        variation_repo: IRecipeVariationRepository,
        recipe_repo: IRecipeRepository,
        viewers: ViewerResolver,
    ) -> None:
        self._variations = variation_repo
        self._recipes = recipe_repo
        self._viewers = viewers

    async def route(self, actor: User, public_id: UUID) -> str | None:
        variation = await self._variations.get_by_public_id(str(public_id))
        recipe = await self._recipes.get(variation.recipe_id) if variation else None
        if variation is None or recipe is None:
            return None
        if not can_view_variation(await self._viewers.of(actor), recipe, variation):
            return None
        return f"/recipes/{recipe.public_id}?variation={variation.public_id}"


class IngredientAccess:
    """Every signed-in user reads the catalogue; an archived ingredient is
    gone from every response, so it does not open either."""

    def __init__(self, *, ingredient_repo: IIngredientRepository) -> None:
        self._ingredients = ingredient_repo

    async def route(self, actor: User, public_id: UUID) -> str | None:
        ingredient = await self._ingredients.get_by_public_id(str(public_id))
        if ingredient is None or ingredient.status is IngredientStatus.ARCHIVED:
            return None
        return f"/ingredients/{ingredient.public_id}"


class ShoppingListAccess:
    """A list opens for the people on it (`ShoppingList.can_access`)."""

    def __init__(self, *, list_repo: IShoppingListRepository, viewers: ViewerResolver) -> None:
        self._lists = list_repo
        self._viewers = viewers

    async def route(self, actor: User, public_id: UUID) -> str | None:
        found = await self._lists.get_by_public_id(str(public_id))
        viewer = await self._viewers.of(actor)
        if found is None or not found.can_access(actor.id, viewer.household_id):
            return None
        return f"/shopping/{found.public_id}"


class KitchenAccess:
    """A kitchen opens for its cook or the members of its household, on the
    kitchen page, which always shows the user's own kitchen."""

    def __init__(self, *, kitchen_repo: IKitchenRepository, viewers: ViewerResolver) -> None:
        self._kitchens = kitchen_repo
        self._viewers = viewers

    async def route(self, actor: User, public_id: UUID) -> str | None:
        viewer = await self._viewers.of(actor)
        own = (
            await self._kitchens.of_household(viewer.household_id)
            if viewer.household_id is not None
            else await self._kitchens.of_user(actor.id)
        )
        return "/kitchen" if own is not None and own.public_id == public_id else None


class HouseholdAccess:
    """A household opens for its members only."""

    def __init__(self, *, household_repo: IHouseholdRepository) -> None:
        self._households = household_repo

    async def route(self, actor: User, public_id: UUID) -> str | None:
        own = await self._households.of_user(actor.id) if actor.id else None
        return "/household" if own is not None and own.public_id == public_id else None
