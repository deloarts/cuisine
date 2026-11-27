"""
The meal plan: recipes or free texts per day and meal. Every user has a
personal plan that only they see. A member of a household also plans in the
household's plan, which every member reads and changes and which stays with
the household when someone leaves. A request names its plan with a scope; a
member without one means the household's, everyone else their own. A range of
a plan can be put on a shopping list in one go, each recipe scaled to the
servings planned.
"""

from datetime import date

from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.application.use_cases.planning.shopping_lists import ManageShoppingLists
from src.cookbook.domain.entities.cooking import MealPlanEntry
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import InvalidPlanError
from src.cookbook.domain.exceptions import MealPlanEntryNotFoundError
from src.cookbook.domain.exceptions import NotInHouseholdError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.value_objects.enums import MealPlanScope
from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.ports.outbound.repositories.cooking_repositories import IMealPlanRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

MAX_RANGE_DAYS = 62


class ManageMealPlan:
    def __init__(
        self,
        *,
        meal_plan_repo: IMealPlanRepository,
        recipe_repo: IRecipeRepository,
        shopping: ManageShoppingLists,
        viewers: ViewerResolver,
        uow: IUnitOfWork,
    ) -> None:
        self._plan = meal_plan_repo
        self._recipes = recipe_repo
        self._shopping = shopping
        self._viewers = viewers
        self._uow = uow

    @staticmethod
    def _range(date_from: date, date_to: date) -> None:
        if date_to < date_from:
            raise InvalidPlanError("The end of the range lies before its start.")
        if (date_to - date_from).days > MAX_RANGE_DAYS:
            raise InvalidPlanError(f"Ask for at most {MAX_RANGE_DAYS} days at once.")

    async def _household_of(self, actor: User, scope: MealPlanScope | None) -> int | None:
        """The household whose plan the scope means, or None for the
        personal plan."""
        household_id = (await self._viewers.of(actor)).household_id
        if scope is MealPlanScope.PERSONAL:
            return None
        if scope is MealPlanScope.HOUSEHOLD and household_id is None:
            raise NotInHouseholdError("You do not belong to a household.")
        return household_id

    async def household_of(self, actor: User, scope: MealPlanScope | None) -> int | None:
        """The household whose plan the scope means for the actor, or None
        for their personal plan."""
        return await self._household_of(actor, scope)

    async def between(
        self,
        actor: User,
        date_from: date,
        date_to: date,
        scope: MealPlanScope | None = None,
    ) -> list[MealPlanEntry]:
        self._range(date_from, date_to)
        household_id = await self._household_of(actor, scope)
        return await self._plan.between(actor.id, household_id, date_from, date_to)

    async def _recipe_id(self, actor: User, public_id: str | None) -> int | None:
        if not public_id:
            return None
        recipe = await self._recipes.get_by_public_id(public_id)
        if recipe is None or not can_view_recipe(await self._viewers.of(actor), recipe):
            raise RecipeNotFoundError("No such recipe.")
        return recipe.id

    @staticmethod
    def _check(recipe_id: int | None, title: str, servings: int) -> None:
        if recipe_id is None and not title.strip():
            raise InvalidPlanError("A planned meal needs a recipe or a text.")
        if len(title) > 255:
            raise InvalidPlanError("The text is too long.")
        if not 1 <= servings <= 100:
            raise InvalidPlanError("The servings must be between 1 and 100.")

    async def add(
        self,
        actor: User,
        *,
        plan_date: date,
        slot: MealSlot,
        recipe_id: str | None,
        title: str,
        servings: int,
        scope: MealPlanScope | None = None,
    ) -> MealPlanEntry:
        household_id = await self._household_of(actor, scope)
        internal = await self._recipe_id(actor, recipe_id)
        self._check(internal, title, servings)
        entry = await self._plan.save(
            MealPlanEntry(
                user_id=actor.id,
                plan_date=plan_date,
                slot=slot,
                servings=servings,
                created=now_utc(),
                recipe_id=internal,
                title=title.strip(),
                household_id=household_id,
            )
        )
        await self._uow.commit()
        return entry

    async def update(
        self,
        actor: User,
        public_id: str,
        *,
        plan_date: date,
        slot: MealSlot,
        recipe_id: str | None,
        title: str,
        servings: int,
    ) -> MealPlanEntry:
        entry = await self._plan.get_accessible(
            actor.id, (await self._viewers.of(actor)).household_id, public_id
        )
        if entry is None:
            raise MealPlanEntryNotFoundError("No such planned meal.")
        internal = await self._recipe_id(actor, recipe_id)
        self._check(internal, title, servings)
        entry.plan_date = plan_date
        entry.slot = slot
        entry.recipe_id = internal
        entry.title = title.strip()
        entry.servings = servings
        saved = await self._plan.save(entry)
        await self._uow.commit()
        return saved

    async def delete(self, actor: User, public_id: str) -> None:
        entry = await self._plan.get_accessible(
            actor.id, (await self._viewers.of(actor)).household_id, public_id
        )
        if entry is None:
            raise MealPlanEntryNotFoundError("No such planned meal.")
        await self._plan.delete(entry)
        await self._uow.commit()

    async def to_shopping_list(
        self,
        actor: User,
        date_from: date,
        date_to: date,
        list_id: str,
        bought_sub_recipe_ids: list[str] | None = None,
        scope: MealPlanScope | None = None,
    ) -> int:
        """Adds every planned recipe of the range of one plan to the list;
        returns how many lines it added or merged."""
        self._range(date_from, date_to)
        viewer = await self._viewers.of(actor)
        household_id = await self._household_of(actor, scope)
        entries = [
            e
            for e in await self._plan.between(actor.id, household_id, date_from, date_to)
            if e.recipe_id
        ]
        recipes = {
            r.id: r
            for r in await self._recipes.get_many([e.recipe_id for e in entries if e.recipe_id])
        }
        wanted: list[tuple[Recipe, int]] = [
            (recipes[e.recipe_id], e.servings)
            for e in entries
            if e.recipe_id in recipes and can_view_recipe(viewer, recipes[e.recipe_id])
        ]
        return await self._shopping.add_recipes(actor, list_id, wanted, bought_sub_recipe_ids)
