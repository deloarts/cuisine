"""/api/v1/web: the cooking calendar, the meal plan, the home page and the
viewer's private food restrictions."""

from datetime import date

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from src.cookbook.adapters.inbound.api.context import get_presenter
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_manage_cook_events
from src.cookbook.adapters.inbound.api.deps import get_manage_meal_plan
from src.cookbook.adapters.inbound.api.deps import get_manage_personal
from src.cookbook.adapters.inbound.api.deps import get_read_food_fact
from src.cookbook.adapters.inbound.api.deps import get_read_recipes
from src.cookbook.adapters.inbound.api.deps import get_suggest_meals
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.presenters import food_fact
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import AddedResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import CookEventRequest
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import CookEventResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import CookEventUpdate
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import FoodRestrictionRequest
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import FoodRestrictionResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import HomeResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import MealPlanEntryResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import MealPlanRequest
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import MealPlanSuggestionResponse
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import MealPlanToListRequest
from src.cookbook.application.use_cases.cooking.cook_events import ManageCookEvents
from src.cookbook.application.use_cases.cooking.food_facts import ReadFoodFact
from src.cookbook.application.use_cases.personal.manage_personal import ManagePersonal
from src.cookbook.application.use_cases.personal.manage_personal import RestrictionCommand
from src.cookbook.application.use_cases.planning.meal_plan import ManageMealPlan
from src.cookbook.application.use_cases.planning.meal_suggestions import MAX_SUGGESTIONS
from src.cookbook.application.use_cases.planning.meal_suggestions import SuggestMeals
from src.cookbook.application.use_cases.recipes.read_recipes import ReadRecipes
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.value_objects.enums import MealPlanScope
from src.cookbook.domain.value_objects.enums import MealSlot
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import UserNotFoundError
from src.shared_kernel.domain.services.clock import now_utc

router = APIRouter()

HOME_LIST_SIZE = 8


async def _user_id(c: Cookbook, public_id: str | None) -> int | None:
    if not public_id:
        return None
    user = await c.platform.users.get_by_public_id(public_id)
    if user is None:
        raise UserNotFoundError("No such user.")
    return user.id


# ── Cook events ──────────────────────────────────────────────────────


@router.get("/cook-events", response_model=list[CookEventResponse], tags=["cooking"])
async def cooking_calendar(
    date_from: date = Query(),
    date_to: date = Query(),
    user_id: str | None = Query(None),
    recipe_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageCookEvents = Depends(get_manage_cook_events),
) -> list[CookEventResponse]:
    """Everyone's cook events in a date range, at most 400 days."""
    internal_recipe: int | None = None
    if recipe_id:
        recipe = await c.recipes.get_by_public_id(recipe_id)
        if recipe is None or not can_view_recipe(presenter.viewer, recipe):
            raise RecipeNotFoundError("No such recipe.")
        internal_recipe = recipe.id
    events = await use_case.calendar(
        user, date_from, date_to, user_id=await _user_id(c, user_id), recipe_id=internal_recipe
    )
    return await presenter.cook_events(events)


@router.get("/cook-events/recent", response_model=list[CookEventResponse], tags=["cooking"])
async def recent_cook_events(
    limit: int = Query(20, ge=1, le=100),
    user_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageCookEvents = Depends(get_manage_cook_events),
) -> list[CookEventResponse]:
    events = await use_case.recent(user, limit=limit, user_id=await _user_id(c, user_id))
    return await presenter.cook_events(events)


@router.get("/cook-events/on-this-day", response_model=list[CookEventResponse], tags=["cooking"])
async def on_this_day(
    day: date | None = Query(None, alias="date"),
    mine: bool = Query(False),
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageCookEvents = Depends(get_manage_cook_events),
) -> list[CookEventResponse]:
    """What was cooked around this day in earlier years."""
    events = await use_case.on_this_day(
        user, day or now_utc().date(), user_id=user.id if mine else None
    )
    return await presenter.cook_events(events)


@router.post(
    "/cook-events",
    response_model=CookEventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["cooking"],
)
async def create_cook_event(
    body: CookEventRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageCookEvents = Depends(get_manage_cook_events),
) -> CookEventResponse:
    """ "I cooked this": records the viewer cooking a recipe on a day."""
    event = await use_case.create(
        user,
        str(body.recipe_id),
        body.cooked_on,
        body.servings,
        body.note,
        str(body.variation_id) if body.variation_id else None,
    )
    return (await presenter.cook_events([event]))[0]


@router.put("/cook-events/{event_id}", response_model=CookEventResponse, tags=["cooking"])
async def update_cook_event(
    event_id: str,
    body: CookEventUpdate,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageCookEvents = Depends(get_manage_cook_events),
) -> CookEventResponse:
    event = await use_case.update(user, event_id, body.cooked_on, body.servings, body.note)
    return (await presenter.cook_events([event]))[0]


@router.delete("/cook-events/{event_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["cooking"])
async def delete_cook_event(
    event_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageCookEvents = Depends(get_manage_cook_events),
) -> None:
    await use_case.delete(user, event_id)


# ── Meal plan ────────────────────────────────────────────────────────


@router.get("/meal-plan", response_model=list[MealPlanEntryResponse], tags=["meal-plan"])
async def read_meal_plan(
    date_from: date = Query(),
    date_to: date = Query(),
    scope: MealPlanScope | None = Query(default=None),
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageMealPlan = Depends(get_manage_meal_plan),
) -> list[MealPlanEntryResponse]:
    """The planned meals of one plan in a range of at most 62 days: the
    household's for a member and the viewer's personal plan otherwise,
    unless `scope` names one."""
    return await presenter.meal_plan(await use_case.between(user, date_from, date_to, scope))


@router.get(
    "/meal-plan/suggestions",
    response_model=list[MealPlanSuggestionResponse],
    tags=["meal-plan"],
)
async def suggest_meals(
    date_from: date = Query(),
    date_to: date = Query(),
    scope: MealPlanScope | None = Query(default=None),
    slot: MealSlot | None = Query(default=None),
    limit: int = Query(12, ge=1, le=MAX_SUGGESTIONS),
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: SuggestMeals = Depends(get_suggest_meals),
) -> list[MealPlanSuggestionResponse]:
    """Published recipes worth planning in the range of one plan, best
    first, each with the reason that carried it. Ranked from the plan's
    cooking history (every member's for the household's plan, the viewer's
    own for the personal one), favourites, the season and, with `slot`, the
    meal tags; recipes already planned in the range are left out."""
    suggestions, lookups = await use_case.suggest(
        user, date_from, date_to, scope=scope, slot=slot, limit=limit
    )
    recipes = await presenter.summaries([s.summary for s in suggestions], lookups)
    return [
        MealPlanSuggestionResponse(recipe=recipe, reason=s.reason)
        for recipe, s in zip(recipes, suggestions, strict=True)
    ]


@router.post(
    "/meal-plan",
    response_model=MealPlanEntryResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["meal-plan"],
)
async def add_meal(
    body: MealPlanRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageMealPlan = Depends(get_manage_meal_plan),
) -> MealPlanEntryResponse:
    entry = await use_case.add(
        user,
        plan_date=body.plan_date,
        slot=body.slot,
        recipe_id=str(body.recipe_id) if body.recipe_id else None,
        title=body.title,
        servings=body.servings,
        scope=body.scope,
    )
    return (await presenter.meal_plan([entry]))[0]


@router.put("/meal-plan/{entry_id}", response_model=MealPlanEntryResponse, tags=["meal-plan"])
async def update_meal(
    entry_id: str,
    body: MealPlanRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageMealPlan = Depends(get_manage_meal_plan),
) -> MealPlanEntryResponse:
    entry = await use_case.update(
        user,
        entry_id,
        plan_date=body.plan_date,
        slot=body.slot,
        recipe_id=str(body.recipe_id) if body.recipe_id else None,
        title=body.title,
        servings=body.servings,
    )
    return (await presenter.meal_plan([entry]))[0]


@router.delete("/meal-plan/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["meal-plan"])
async def delete_meal(
    entry_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageMealPlan = Depends(get_manage_meal_plan),
) -> None:
    await use_case.delete(user, entry_id)


@router.post("/meal-plan/shopping-list", response_model=AddedResponse, tags=["meal-plan"])
async def meal_plan_to_shopping_list(
    body: MealPlanToListRequest,
    user: User = Depends(get_current_user),
    use_case: ManageMealPlan = Depends(get_manage_meal_plan),
) -> AddedResponse:
    """Puts every planned recipe of the range on a shopping list, each
    scaled to its planned servings."""
    added = await use_case.to_shopping_list(
        user,
        body.date_from,
        body.date_to,
        str(body.list_id),
        [str(s) for s in body.bought_sub_recipe_ids],
        body.scope,
    )
    return AddedResponse(added=added)


# ── Home ─────────────────────────────────────────────────────────────


@router.get("/home", response_model=HomeResponse, tags=["home"])
async def home(
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    events: ManageCookEvents = Depends(get_manage_cook_events),
    recipes: ReadRecipes = Depends(get_read_recipes),
    facts: ReadFoodFact = Depends(get_read_food_fact),
) -> HomeResponse:
    """The start page: the food fact of the day, what was cooked on this day in earlier years, what
    everyone cooked lately, the viewer's favourites, the newest recipes and
    recipes in season this month."""
    favourites, _, fav_lookups = await recipes.list(
        user,
        await recipes.query_for(
            user, status="published", favourites_of=user.id, sort="changed", limit=HOME_LIST_SIZE
        ),
    )
    newest, _, new_lookups = await recipes.list(
        user, await recipes.query_for(user, status="published", limit=HOME_LIST_SIZE)
    )
    seasonal, _, season_lookups = await recipes.list(
        user,
        await recipes.query_for(user, status="published", sort="changed", limit=HOME_LIST_SIZE),
        in_season=True,
    )
    today = now_utc().date()
    daily = await facts.for_day(today)
    return HomeResponse(
        food_fact=food_fact(daily, presenter.locale) if daily else None,
        on_this_day=await presenter.cook_events(await events.on_this_day(user, today)),
        recently_cooked=await presenter.cook_events(
            await events.recent(user, limit=HOME_LIST_SIZE)
        ),
        favourites=await presenter.summaries(favourites, fav_lookups),
        newest=await presenter.summaries(newest, new_lookups),
        in_season=await presenter.summaries(seasonal, season_lookups),
    )


# ── Food restrictions (private) ──────────────────────────────────────


@router.get(
    "/users/me/food-restrictions", response_model=list[FoodRestrictionResponse], tags=["me"]
)
async def list_food_restrictions(
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManagePersonal = Depends(get_manage_personal),
) -> list[FoodRestrictionResponse]:
    """The viewer's own allergies and intolerances. There is no way to read
    another user's."""
    return await presenter.restrictions(await use_case.restrictions(user))


@router.post(
    "/users/me/food-restrictions",
    response_model=FoodRestrictionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["me"],
)
async def add_food_restriction(
    body: FoodRestrictionRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManagePersonal = Depends(get_manage_personal),
) -> FoodRestrictionResponse:
    restriction = await use_case.add_restriction(
        user,
        RestrictionCommand(
            kind=body.kind,
            allergen=body.allergen,
            ingredient_id=str(body.ingredient_id) if body.ingredient_id else None,
            ingredient_name=body.ingredient_name,
            diet=body.diet,
            family_id=str(body.family_id) if body.family_id else None,
            note=body.note,
        ),
    )
    return (await presenter.restrictions([restriction]))[0]


@router.delete(
    "/users/me/food-restrictions/{restriction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["me"],
)
async def remove_food_restriction(
    restriction_id: str,
    user: User = Depends(get_current_user),
    use_case: ManagePersonal = Depends(get_manage_personal),
) -> None:
    await use_case.remove_restriction(user, restriction_id)
