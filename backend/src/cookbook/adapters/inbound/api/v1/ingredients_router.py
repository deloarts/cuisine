"""/api/v1/web/ingredients: the ingredient catalogue, and the USDA lookup
that prefills nutrition."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from src.cookbook.adapters.inbound.api.context import get_presenter
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_lookup_nutrition
from src.cookbook.adapters.inbound.api.deps import get_manage_ingredients
from src.cookbook.adapters.inbound.api.deps import get_read_resource_usage
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.presenters import food_match
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import IngredientDeletionImpact
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import MergeRequest
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import DuplicateCandidate
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import ExtendedNutrientResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import FoodMatchResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import IngredientDetailResponse
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import IngredientListItem
from src.cookbook.adapters.inbound.api.schemas.ingredient_schema import IngredientRequest
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ConversionCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import IngredientCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import IngredientSort
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ManageIngredients
from src.cookbook.application.use_cases.ingredients.nutrition_lookup import LookupNutrition
from src.cookbook.application.use_cases.resources.resource_usage import ReadResourceUsage
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.exceptions import IngredientCategoryNotFoundError
from src.cookbook.domain.exceptions import IngredientFamilyNotFoundError
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.value_objects.enums import ContentLocale
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.nutrients import EXTENDED_NUTRIENTS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.ports.outbound.repositories.ingredient_repository import IngredientQuery
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_any_permission
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.schemas.base import Page
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import NotFoundError
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["ingredients"])

SortOrder = Literal["asc", "desc"]

_write = require_permission(Permission.WRITE_INGREDIENTS)
_editors = require_any_permission(Permission.WRITE_INGREDIENTS, Permission.MANAGE_INGREDIENTS)
_managers = require_permission(Permission.MANAGE_INGREDIENTS)


def matched_alias(ingredient: Ingredient, search: str) -> str | None:
    """The alias a search matched when no main name did, so a picker can
    show "Tomate → Paradeiser"."""
    wanted = search.strip().casefold()
    if any(
        wanted in t.name.casefold() or wanted in t.plural_name.casefold()
        for t in ingredient.translations.values()
    ):
        return None
    return next(
        (a for names in ingredient.aliases.values() for a in names if wanted in a.casefold()),
        None,
    )


def command(body: IngredientRequest) -> IngredientCommand:
    return IngredientCommand(
        original_locale=body.original_locale.value,
        translations={
            k.value: IngredientText(name=v.name, plural_name=v.plural_name)
            for k, v in body.translations.items()
        },
        category_id=str(body.category_id) if body.category_id else None,
        family_id=str(body.family_id) if body.family_id else None,
        aliases={k.value: list(v) for k, v in body.aliases.items()},
        nutrition=Nutrition(**body.nutrition.model_dump()),
        extended_nutrition=dict(body.extended_nutrition),
        season_months=list(body.season_months),
        density_g_per_ml=body.density_g_per_ml,
        conversions=[ConversionCommand(str(c.unit_id), c.grams) for c in body.conversions],
        allergens=list(body.allergens),
        diet_markers=list(body.diet_markers),
        nutrition_source=body.nutrition_source,
        usda_fdc_id=body.usda_fdc_id,
    )


async def _detail(
    ingredient: Ingredient, presenter: Presenter, c: Cookbook, use_case: ManageIngredients
) -> IngredientDetailResponse:
    lookups = await c.lookups().load()
    return await presenter.ingredient_detail(
        ingredient, lookups, await use_case.recipe_count(ingredient)
    )


@router.get("/ingredients", response_model=Page[IngredientListItem])
async def list_ingredients(
    search: str | None = Query(None, max_length=128),
    category_id: str | None = Query(None),
    family_id: str | None = Query(None),
    status_filter: IngredientStatus | None = Query(None, alias="status"),
    mine: bool = Query(False),
    min_usage: int | None = Query(None, ge=0, description="At least this many recipes use it."),
    max_usage: int | None = Query(None, ge=0, description="At most this many recipes use it."),
    sort: IngredientSort | None = Query(
        None,
        description="`name` alphabetical or `usage` by usage count; without it a search "
        "ranks the best matches first and otherwise the order is alphabetical.",
    ),
    order: SortOrder = Query("asc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
    usage_case: ReadResourceUsage = Depends(get_read_resource_usage),
) -> Page[IngredientListItem]:
    """The catalogue, paged. `usage_count` counts the recipes the viewer may
    see that use the ingredient; filtering or sorting by it counts the whole
    catalogue, otherwise only the page is counted."""
    internal_category: int | None = None
    if category_id:
        category = await c.categories.get_by_public_id(category_id)
        if category is None:
            raise IngredientCategoryNotFoundError("No such ingredient category.")
        internal_category = category.id
    internal_family: int | None = None
    if family_id:
        family = await c.families.get_by_public_id(family_id)
        if family is None:
            raise IngredientFamilyNotFoundError("No such ingredient family.")
        internal_family = family.id
    by_usage = sort == "usage" or min_usage is not None or max_usage is not None
    usage = await usage_case.ingredients(user) if by_usage else None
    found, total = await use_case.find(
        IngredientQuery(
            search=search,
            category_id=internal_category,
            family_id=internal_family,
            status=status_filter,
            owner_id=user.id if mine else None,
        ),
        limit=limit,
        offset=offset,
        sort=sort,
        descending=order == "desc",
        usage=usage,
        min_usage=min_usage,
        max_usage=max_usage,
    )
    if usage is None:
        usage = await usage_case.ingredients(user, [i.id for i in found])
    lookups = await c.lookups().load()
    items = await presenter.ingredient_list(found, lookups, usage)
    if search and search.strip():
        for item, ingredient in zip(items, found, strict=True):
            item.matched_alias = matched_alias(ingredient, search)
    return Page(items=items, total=total)


@router.get("/ingredients/duplicates", response_model=list[DuplicateCandidate])
async def ingredient_duplicates(
    name: str = Query(min_length=1, max_length=128),
    locale: ContentLocale | None = Query(
        None, description="Compare in this language only; both by default."
    ),
    _user: User = Depends(get_current_user),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> list[DuplicateCandidate]:
    """Ingredients that probably mean the same food as `name`: the same
    name or alias without case, diacritics and spacing (`exact`, which
    creating would refuse with 409), or one that differs by a plural ending
    or a letter, for "Did you mean Erdapfel?"."""
    found = await use_case.near_duplicates(name, locale.value if locale else None)
    return [
        DuplicateCandidate(
            id=UUID(entry.public_id), name=entry.main_name, matched=entry.name, exact=exact
        )
        for entry, exact in found
    ]


@router.get("/ingredients/{ingredient_id}", response_model=IngredientDetailResponse)
async def read_ingredient(
    ingredient_id: str,
    _user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> IngredientDetailResponse:
    return await _detail(await use_case.get(ingredient_id), presenter, c, use_case)


@router.post(
    "/ingredients", response_model=IngredientDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_ingredient(
    body: IngredientRequest,
    actor: User = Depends(_write),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> IngredientDetailResponse:
    return await _detail(await use_case.create(actor, command(body)), presenter, c, use_case)


@router.put("/ingredients/{ingredient_id}", response_model=IngredientDetailResponse)
async def update_ingredient(
    ingredient_id: str,
    body: IngredientRequest,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> IngredientDetailResponse:
    saved = await use_case.update(actor, ingredient_id, command(body))
    return await _detail(saved, presenter, c, use_case)


@router.post("/ingredients/{ingredient_id}/activate", response_model=IngredientDetailResponse)
async def activate_ingredient(
    ingredient_id: str,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> IngredientDetailResponse:
    """Marks an agent's draft ingredient as reviewed."""
    saved = await use_case.set_status(actor, ingredient_id, IngredientStatus.ACTIVE)
    return await _detail(saved, presenter, c, use_case)


@router.get("/ingredients/{ingredient_id}/deletion-impact", response_model=IngredientDeletionImpact)
async def ingredient_deletion_impact(
    ingredient_id: str,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> IngredientDeletionImpact:
    """What the deletion dialog needs. Nothing here says whether food
    restrictions name the ingredient."""
    ingredient = await use_case.get(ingredient_id)
    recipe_ids = await use_case.recipes_using(ingredient)
    recipes = [
        r for r in await c.recipes.get_many(recipe_ids) if can_view_recipe(presenter.viewer, r)
    ]
    refs = await presenter.recipe_refs(recipes)
    return IngredientDeletionImpact(
        seeded=ingredient.seed_key is not None,
        recipe_count=len(recipe_ids),
        recipes=[refs[r.id] for r in recipes if r.id in refs],
        can_merge=actor.has_permission(Permission.MANAGE_INGREDIENTS)
        and ingredient.seed_key is None,
    )


@router.post("/ingredients/{ingredient_id}/merge", response_model=IngredientDetailResponse)
async def merge_ingredient(
    ingredient_id: str,
    body: MergeRequest,
    actor: User = Depends(_managers),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> IngredientDetailResponse:
    """Repoints recipe lines, shopping items and food restrictions to the
    target and deletes this ingredient. Answers with the target."""
    target = await use_case.merge(actor, ingredient_id, str(body.into_id))
    return await _detail(target, presenter, c, use_case)


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingredient(
    ingredient_id: str,
    actor: User = Depends(_editors),
    use_case: ManageIngredients = Depends(get_manage_ingredients),
) -> None:
    await use_case.delete(actor, ingredient_id)


@router.get(
    "/nutrition/nutrients", response_model=list[ExtendedNutrientResponse], tags=["nutrition"]
)
async def list_extended_nutrients(
    _user: User = Depends(get_current_user),
) -> list[ExtendedNutrientResponse]:
    """The extended nutrient catalogue in display order: the keys
    `extended_nutrition` takes, each with its unit and label key."""
    return [
        ExtendedNutrientResponse(
            key=n.key, unit=n.unit, label_key=n.label_key, usda_nutrient_id=n.usda_nutrient_id
        )
        for n in EXTENDED_NUTRIENTS
    ]


@router.get("/nutrition/usda/search", response_model=list[FoodMatchResponse], tags=["nutrition"])
async def search_usda(
    query: str = Query(min_length=2, max_length=128),
    limit: int = Query(10, ge=1, le=25),
    _user: User = Depends(_editors),
    use_case: LookupNutrition = Depends(get_lookup_nutrition),
) -> list[FoodMatchResponse]:
    """Generic foods from USDA FoodData Central (public domain, CC0), with
    nutrition per 100 g."""
    return [food_match(m) for m in await use_case.search(query, limit=limit)]


@router.get("/nutrition/usda/{fdc_id}", response_model=FoodMatchResponse, tags=["nutrition"])
async def read_usda_food(
    fdc_id: int,
    _user: User = Depends(_editors),
    use_case: LookupNutrition = Depends(get_lookup_nutrition),
) -> FoodMatchResponse:
    match = await use_case.get(fdc_id)
    if match is None:
        raise NotFoundError("No such food in the USDA database.")
    return food_match(match)
