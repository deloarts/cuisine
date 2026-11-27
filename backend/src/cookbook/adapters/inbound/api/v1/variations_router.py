"""/api/v1/web/recipes/{id}/variations, /co-editors, /copy and /copies:
variations of a recipe and adopting them, the people who edit a recipe with
its owner, and copies made with "Copy as my recipe"."""

from dataclasses import replace

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from src.cookbook.adapters.inbound.api.context import get_presenter
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_manage_recipes
from src.cookbook.adapters.inbound.api.deps import get_manage_variations
from src.cookbook.adapters.inbound.api.deps import get_read_recipes
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.schemas.common_schema import PersonRef
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeEditResponse
from src.cookbook.adapters.inbound.api.schemas.variation_schema import AdoptVariationRequest
from src.cookbook.adapters.inbound.api.schemas.variation_schema import AdoptVariationResponse
from src.cookbook.adapters.inbound.api.schemas.variation_schema import CoEditorsRequest
from src.cookbook.adapters.inbound.api.schemas.variation_schema import RecipeCopyResponse
from src.cookbook.adapters.inbound.api.schemas.variation_schema import VariationRequest
from src.cookbook.adapters.inbound.api.schemas.variation_schema import VariationResponse
from src.cookbook.adapters.inbound.api.schemas.variation_schema import VariationViewResponse
from src.cookbook.adapters.inbound.api.v1.recipes_router import _edit
from src.cookbook.adapters.inbound.api.variation_presenter import step_markers
from src.cookbook.adapters.inbound.api.variation_presenter import variation_response
from src.cookbook.application.services.variation_resolver import VariationChangeCommand
from src.cookbook.application.services.variation_resolver import VariationEquipmentCommand
from src.cookbook.application.services.variation_resolver import VariationLineCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import ManageRecipes
from src.cookbook.application.use_cases.recipes.manage_variations import ManageVariations
from src.cookbook.application.use_cases.recipes.manage_variations import VariationCommand
from src.cookbook.application.use_cases.recipes.read_recipes import ReadRecipes
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.variation import RecipeVariation
from src.cookbook.domain.services.recipe_derivation import scale_factor
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_any_permission
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["recipes"])

_write = require_permission(Permission.WRITE_RECIPES)
_editors = require_any_permission(Permission.WRITE_RECIPES, Permission.MANAGE_RECIPES)


def _command(body: VariationRequest) -> VariationCommand:
    def uid(value: object) -> str | None:
        return str(value) if value else None

    return VariationCommand(
        name=body.name,
        note=body.note,
        locale=body.locale.value,
        private=body.private,
        changes=[
            VariationChangeCommand(
                kind=c.kind,
                id=c.id,
                step=c.step,
                ingredient_id=uid(c.ingredient_id),
                sub_recipe_id=uid(c.sub_recipe_id),
                to_ingredient_id=uid(c.to_ingredient_id),
                amount=c.amount,
                unit_id=uid(c.unit_id),
                keep_amount=c.keep_amount,
                note=c.note,
                text=c.text,
                duration_minutes=c.duration_minutes,
                lines=[
                    VariationLineCommand(
                        ingredient_id=str(line.ingredient_id),
                        amount=line.amount,
                        unit_id=uid(line.unit_id),
                        note=line.note,
                    )
                    for line in c.lines
                ],
                equipment=[
                    VariationEquipmentCommand(
                        equipment_id=str(item.equipment_id), count=item.count, note=item.note
                    )
                    for item in c.equipment
                ],
            )
            for c in body.changes
        ],
    )


async def _responses(
    actor: User,
    recipe: Recipe,
    variations: list[RecipeVariation],
    presenter: Presenter,
    use_case: ManageVariations,
) -> list[VariationResponse]:
    infos = await use_case.infos(actor, recipe, variations)
    return [await variation_response(presenter, use_case.resolver, recipe, i) for i in infos]


# ── Variations ───────────────────────────────────────────────────────


@router.get("/recipes/{recipe_id}/variations", response_model=list[VariationResponse])
async def list_variations(
    recipe_id: str,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageVariations = Depends(get_manage_variations),
) -> list[VariationResponse]:
    """The variations of the recipe the viewer may see, oldest first: every
    shared one and the viewer's own private ones."""
    recipe, variations = await use_case.for_recipe(user, recipe_id)
    return await _responses(user, recipe, variations, presenter, use_case)


@router.post(
    "/recipes/{recipe_id}/variations",
    response_model=VariationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_variation(
    recipe_id: str,
    body: VariationRequest,
    actor: User = Depends(_write),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageVariations = Depends(get_manage_variations),
) -> VariationResponse:
    """Adds a variation to a recipe the actor can see. 422
    `InvalidVariationError` when a change names a step or line the recipe
    lacks; 422 `InvalidMentionError` for a mention outside its step."""
    recipe, variation = await use_case.create(actor, recipe_id, _command(body))
    return (await _responses(actor, recipe, [variation], presenter, use_case))[0]


@router.get("/recipes/{recipe_id}/variations/{variation_id}", response_model=VariationResponse)
async def read_variation(
    recipe_id: str,
    variation_id: str,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageVariations = Depends(get_manage_variations),
) -> VariationResponse:
    recipe, variation = await use_case.get(user, recipe_id, variation_id)
    return (await _responses(user, recipe, [variation], presenter, use_case))[0]


@router.put("/recipes/{recipe_id}/variations/{variation_id}", response_model=VariationResponse)
async def update_variation(
    recipe_id: str,
    variation_id: str,
    body: VariationRequest,
    actor: User = Depends(_write),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageVariations = Depends(get_manage_variations),
) -> VariationResponse:
    """Replaces the variation as a whole; its author only. The step numbers
    refer to the recipe as it is now, and the variation moves onto the
    recipe's latest revision."""
    recipe, variation = await use_case.update(actor, recipe_id, variation_id, _command(body))
    return (await _responses(actor, recipe, [variation], presenter, use_case))[0]


@router.delete(
    "/recipes/{recipe_id}/variations/{variation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_variation(
    recipe_id: str,
    variation_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageVariations = Depends(get_manage_variations),
) -> None:
    """Its author, or manage:recipes."""
    await use_case.delete(user, recipe_id, variation_id)


@router.get(
    "/recipes/{recipe_id}/variations/{variation_id}/view", response_model=VariationViewResponse
)
async def view_variation(
    recipe_id: str,
    variation_id: str,
    servings: int | None = Query(None, ge=1, le=100),
    guests: list[str] = Query(
        default_factory=list,
        description="User ids of dinner guests; sets recipe.unsuitable_for_guests.",
    ),
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageVariations = Depends(get_manage_variations),
    read: ReadRecipes = Depends(get_read_recipes),
) -> VariationViewResponse:
    """The recipe with the variation applied, in the shape of the recipe
    detail, everything derived from the applied recipe, plus a marker per
    step for what differs."""
    recipe, variation = await use_case.get(user, recipe_id, variation_id)
    applied, _ = await use_case.applied(recipe, variation)
    info = (await use_case.infos(user, recipe, [variation]))[0]
    view = await read.view_of(
        user, applied.recipe, servings=servings, guest_ids=await read.resolve_guests(guests)
    )
    view = replace(
        view,
        rating_average=info.rating_average,
        rating_count=info.rating_count,
        own_rating=info.own_rating,
    )
    _, factor = scale_factor(applied.recipe, servings)
    return VariationViewResponse(
        recipe=await presenter.detail(view),
        variation=await variation_response(presenter, use_case.resolver, recipe, info),
        steps=await step_markers(presenter, applied.steps, factor),
    )


@router.post(
    "/recipes/{recipe_id}/variations/{variation_id}/adopt",
    response_model=AdoptVariationResponse,
)
async def adopt_variation(
    recipe_id: str,
    variation_id: str,
    body: AdoptVariationRequest,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageVariations = Depends(get_manage_variations),
) -> AdoptVariationResponse:
    """Writes all changes (`change_ids` null) or the chosen ones into the
    original as an `adopted` revision crediting the variation's author; the
    recipe's editors only. The adopted changes leave the variation."""
    recipe, variation = await use_case.adopt(
        actor, recipe_id, variation_id, body.change_ids, body.revision_note
    )
    return AdoptVariationResponse(
        recipe=await _edit(recipe, actor, c, presenter),
        variation=(await _responses(actor, recipe, [variation], presenter, use_case))[0],
    )


# ── Co-editors ───────────────────────────────────────────────────────


@router.get("/recipes/{recipe_id}/co-editors", response_model=list[PersonRef])
async def list_co_editors(
    recipe_id: str,
    actor: User = Depends(_editors),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> list[PersonRef]:
    """For whoever may edit the recipe."""
    ids = await use_case.co_editors(actor, recipe_id)
    people = await presenter.people(ids)
    return [p for i in ids if (p := people.get(i))]


@router.put("/recipes/{recipe_id}/co-editors", response_model=list[PersonRef])
async def set_co_editors(
    recipe_id: str,
    body: CoEditorsRequest,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> list[PersonRef]:
    """Replaces the co-editors; the owner only (403 otherwise). 422
    `CoEditorError` for the owner, an inactive or service account, or
    someone who cannot see the recipe."""
    saved = await use_case.set_co_editors(user, recipe_id, [str(u) for u in body.user_ids])
    people = await presenter.people(saved.co_editor_ids)
    return [p for i in saved.co_editor_ids if (p := people.get(i))]


# ── Copies ───────────────────────────────────────────────────────────


@router.post(
    "/recipes/{recipe_id}/copy",
    response_model=RecipeEditResponse,
    status_code=status.HTTP_201_CREATED,
)
async def copy_recipe(
    recipe_id: str,
    actor: User = Depends(_write),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    """ "Copy as my recipe": an independent draft of the actor's, linked to
    the original (`based_on`)."""
    return await _edit(await use_case.copy(actor, recipe_id), actor, c, presenter)


@router.get("/recipes/{recipe_id}/copies", response_model=list[RecipeCopyResponse])
async def list_copies(
    recipe_id: str,
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> list[RecipeCopyResponse]:
    """The copies of the recipe the viewer may see, newest first."""
    copies = await use_case.copies(user, recipe_id)
    refs = await presenter.recipe_refs(copies)
    return [
        RecipeCopyResponse(
            recipe=refs[r.id], owner=await presenter.person(r.owner_id), created=r.created
        )
        for r in copies
        if r.id in refs
    ]
