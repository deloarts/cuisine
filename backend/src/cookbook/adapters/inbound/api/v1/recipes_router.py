"""/api/v1/web/recipes: browsing, reading, editing and publishing recipes,
and the viewer's favourite, rating and private note on each."""

from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from src.cookbook.adapters.inbound.api.context import get_presenter
from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.deps import get_cookbook
from src.cookbook.adapters.inbound.api.deps import get_manage_cook_events
from src.cookbook.adapters.inbound.api.deps import get_manage_personal
from src.cookbook.adapters.inbound.api.deps import get_manage_recipes
from src.cookbook.adapters.inbound.api.deps import get_read_recipes
from src.cookbook.adapters.inbound.api.deps import manage_recipes
from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.schemas.cooking_schema import CookEventResponse
from src.cookbook.adapters.inbound.api.schemas.deletion_schema import RecipeDeletionImpact
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import FavouriteRequest
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import NoteRequest
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import NoteResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RatingRequest
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RatingResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RatingStatsResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeDetailResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeEditResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeRequest
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeRevisionResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeRevisionSummary
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import RecipeSummaryResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepImageResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import StepIngredientRequest
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import TranslationRequest
from src.cookbook.application.use_cases.cooking.cook_events import ManageCookEvents
from src.cookbook.application.use_cases.personal.manage_personal import ManagePersonal
from src.cookbook.application.use_cases.recipes.manage_recipes import ManageRecipes
from src.cookbook.application.use_cases.recipes.manage_recipes import RecipeCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepEquipmentCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepIngredientCommand
from src.cookbook.application.use_cases.recipes.read_recipes import ReadRecipes
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.revision import RecipeRevision
from src.cookbook.domain.exceptions import IngredientNotFoundError
from src.cookbook.domain.services.recipe_rules import can_edit_recipe
from src.cookbook.domain.services.recipe_rules import narrower
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.ports.outbound.repositories.recipe_repository import StepImageQuery
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_any_permission
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.schemas.base import Page
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["recipes"])

_write = require_permission(Permission.WRITE_RECIPES)
_editors = require_any_permission(Permission.WRITE_RECIPES, Permission.MANAGE_RECIPES)


def _line(si: StepIngredientRequest) -> StepIngredientCommand:
    return StepIngredientCommand(
        id=str(si.id) if si.id else None,
        ingredient_id=str(si.ingredient_id) if si.ingredient_id else None,
        sub_recipe_id=str(si.sub_recipe_id) if si.sub_recipe_id else None,
        amount=si.amount,
        unit_id=str(si.unit_id) if si.unit_id else None,
        notes={k.value: NoteText(v.note) for k, v in si.notes.items()},
    )


def command(body: RecipeRequest) -> RecipeCommand:
    return RecipeCommand(
        original_locale=body.original_locale.value,
        translations={
            k.value: RecipeText(v.title, v.description, v.tips)
            for k, v in body.translations.items()
        },
        base_servings=body.base_servings,
        prep_minutes=body.prep_minutes,
        cook_minutes=body.cook_minutes,
        rest_minutes=body.rest_minutes,
        difficulty=body.difficulty,
        cover_file_id=str(body.cover_image_id) if body.cover_image_id else None,
        source_url=body.source_url,
        source_name=body.source_name,
        tag_ids=[str(t) for t in body.tag_ids],
        yield_amount=body.yield_amount,
        yield_unit_id=str(body.yield_unit_id) if body.yield_unit_id else None,
        visibility=body.visibility,
        revision_note=body.revision_note,
        shared_user_ids=(
            [str(u) for u in body.shared_user_ids] if body.shared_user_ids is not None else None
        ),
        shared_group_ids=(
            [str(g) for g in body.shared_group_ids] if body.shared_group_ids is not None else None
        ),
        shared_peer_ids=(
            [str(p) for p in body.shared_peer_ids] if body.shared_peer_ids is not None else None
        ),
        steps=[
            StepCommand(
                id=str(s.id) if s.id else None,
                translations={k.value: StepText(v.text) for k, v in s.translations.items()},
                duration_minutes=s.duration_minutes,
                image_file_id=str(s.image_id) if s.image_id else None,
                ingredients=[_line(si) for si in s.ingredients],
                equipment=[
                    StepEquipmentCommand(
                        id=str(se.id) if se.id else None,
                        equipment_id=str(se.equipment_id),
                        count=se.count,
                        notes={k.value: NoteText(v.note) for k, v in se.notes.items()},
                    )
                    for se in s.equipment
                ],
            )
            for s in body.steps
        ],
        ingredients=[_line(si) for si in body.ingredients],
    )


async def _edit(
    recipe: Recipe, actor: User, c: Cookbook, presenter: Presenter
) -> RecipeEditResponse:
    lookups = await c.lookups().load_for([recipe])
    switches = await presenter.switches()
    less_visible = [
        lookups.recipes[s]
        for s in recipe.sub_recipe_ids
        if s in lookups.recipes
        and narrower(
            lookups.recipes[s],
            recipe,
            public_allowed=switches.public_allowed,
            peering=switches.peering,
        )
    ]
    peer_hidden = await manage_recipes(c).peer_hidden_sub_recipes(recipe)
    return await presenter.edit(
        recipe, lookups, can_edit_recipe(presenter.viewer, recipe), less_visible, peer_hidden
    )


@router.get("/recipes", response_model=Page[RecipeSummaryResponse])
async def list_recipes(
    search: str | None = Query(None, max_length=128),
    tag_id: list[str] = Query(default_factory=list),
    status_filter: Literal["published", "drafts"] | None = Query(None, alias="status"),
    mine: bool = Query(False),
    favourites: bool = Query(False),
    max_minutes: int | None = Query(None, ge=1),
    difficulty: Difficulty | None = Query(None),
    ingredient_id: str | None = Query(None),
    diets: list[Diet] = Query(
        default_factory=list, description="Only recipes that fit every one of these diets."
    ),
    guests: list[str] = Query(
        default_factory=list,
        description="User ids of dinner guests; sets unsuitable_for_guests on every recipe.",
    ),
    hide_unsuitable_for_guests: bool = Query(False),
    in_season: bool = Query(
        False, description="Only recipes in season this month (see season_months)."
    ),
    only_kitchen_ready: bool = Query(
        False,
        description="Only recipes the viewer's kitchen has every item for; ignored before the "
        "kitchen is set up.",
    ),
    sort: Literal["newest", "title", "changed"] = Query("newest"),
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ReadRecipes = Depends(get_read_recipes),
) -> Page[RecipeSummaryResponse]:
    tag_ids: list[int] = []
    for public_id in tag_id:
        tag = await c.tags.get_by_public_id(public_id)
        # An unknown tag matches nothing rather than everything.
        tag_ids.append(tag.id if tag else -1)
    internal_ingredient: int | None = None
    if ingredient_id:
        ingredient = await c.ingredients.get_by_public_id(ingredient_id)
        if ingredient is None:
            raise IngredientNotFoundError("No such ingredient.")
        internal_ingredient = ingredient.id
    query = await use_case.query_for(
        user,
        status=status_filter,
        search=search,
        tag_ids=tag_ids,
        owner_id=user.id if mine else None,
        favourites_of=user.id if favourites else None,
        max_total_minutes=max_minutes,
        difficulty=difficulty,
        ingredient_id=internal_ingredient,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    summaries, total, lookups = await use_case.list(
        user,
        query,
        guest_ids=await use_case.resolve_guests(guests),
        diets=diets,
        hide_unsuitable_for_guests=hide_unsuitable_for_guests,
        in_season=in_season,
        only_kitchen_ready=only_kitchen_ready,
    )
    return Page(items=await presenter.summaries(summaries, lookups), total=total)


@router.get("/step-images", response_model=Page[StepImageResponse])
async def list_step_images(
    ingredient_id: list[str] = Query(
        default_factory=list,
        max_length=50,
        description="Ingredients of the step being edited; steps sharing them rank first.",
    ),
    equipment_id: list[str] = Query(
        default_factory=list,
        max_length=50,
        description="Equipment of the step being edited; steps sharing it rank first.",
    ),
    search: str | None = Query(None, max_length=128),
    limit: int = Query(24, ge=1, le=60),
    offset: int = Query(0, ge=0),
    user: User = Depends(_write),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ReadRecipes = Depends(get_read_recipes),
) -> Page[StepImageResponse]:
    """The step image library for the editor: one entry per image that a
    step of a recipe the viewer may see shows, mirrors left out. Unknown
    ingredient and equipment ids are ignored, since they only rank."""
    ingredient_ids = [
        found.id
        for public_id in dict.fromkeys(ingredient_id)
        if (found := await c.ingredients.get_by_public_id(public_id)) is not None
    ]
    equipment_ids = [
        item.id
        for public_id in dict.fromkeys(equipment_id)
        if (item := await c.equipment.get_by_public_id(public_id)) is not None
    ]
    images, total = await use_case.step_images(
        user,
        StepImageQuery(
            ingredient_ids=ingredient_ids,
            equipment_ids=equipment_ids,
            search=search,
            limit=limit,
            offset=offset,
        ),
    )
    return Page(items=await presenter.step_images(images), total=total)


@router.get("/recipes/{recipe_id}", response_model=RecipeDetailResponse)
async def read_recipe(
    recipe_id: str,
    servings: int | None = Query(None, ge=1, le=100),
    guests: list[str] = Query(
        default_factory=list,
        description="User ids of dinner guests; sets unsuitable_for_guests.",
    ),
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    use_case: ReadRecipes = Depends(get_read_recipes),
) -> RecipeDetailResponse:
    """The recipe in the viewer's language, its amounts scaled to `servings`
    (the recipe's own servings by default), with nutrition, allergens and
    the viewer's own warnings, favourite, rating and note."""
    view = await use_case.view(
        user, recipe_id, servings=servings, guest_ids=await use_case.resolve_guests(guests)
    )
    return await presenter.detail(view)


@router.get("/recipes/{recipe_id}/edit", response_model=RecipeEditResponse)
async def read_recipe_for_editing(
    recipe_id: str,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    return await _edit(await use_case.get_editable(actor, recipe_id), actor, c, presenter)


@router.post("/recipes", response_model=RecipeEditResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    body: RecipeRequest,
    actor: User = Depends(_write),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    """Creates the recipe as a draft."""
    return await _edit(await use_case.create(actor, command(body)), actor, c, presenter)


@router.put("/recipes/{recipe_id}", response_model=RecipeEditResponse)
async def update_recipe(
    recipe_id: str,
    body: RecipeRequest,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    return await _edit(await use_case.update(actor, recipe_id, command(body)), actor, c, presenter)


@router.put("/recipes/{recipe_id}/translation", response_model=RecipeEditResponse)
async def save_recipe_translation(
    recipe_id: str,
    body: TranslationRequest,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    """Adds or replaces one language of the recipe."""
    saved = await use_case.add_translation(
        actor,
        recipe_id,
        body.locale.value,
        RecipeText(body.text.title, body.text.description, body.text.tips),
        [StepText(s.text) for s in body.steps],
        [[NoteText(n.note) for n in step] for step in body.notes] if body.notes else None,
        [NoteText(n.note) for n in body.ingredient_notes]
        if body.ingredient_notes is not None
        else None,
    )
    return await _edit(saved, actor, c, presenter)


@router.post("/recipes/{recipe_id}/publish", response_model=RecipeEditResponse)
async def publish_recipe(
    recipe_id: str,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    return await _edit(await use_case.publish(actor, recipe_id), actor, c, presenter)


@router.post("/recipes/{recipe_id}/unpublish", response_model=RecipeEditResponse)
async def unpublish_recipe(
    recipe_id: str,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    return await _edit(await use_case.unpublish(actor, recipe_id), actor, c, presenter)


@router.get("/recipes/{recipe_id}/deletion-impact", response_model=RecipeDeletionImpact)
async def recipe_deletion_impact(
    recipe_id: str,
    actor: User = Depends(_editors),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeDeletionImpact:
    """Whether the recipe can be deleted: recipes using it as a sub-recipe
    block it; the dialog lists those the viewer can see."""
    visible, hidden = await use_case.deletion_impact(actor, recipe_id)
    refs = await presenter.recipe_refs(visible)
    return RecipeDeletionImpact(
        blocked=bool(visible) or hidden > 0,
        used_by=[refs[r.id] for r in visible if r.id in refs],
        used_by_hidden_count=hidden,
    )


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
    recipe_id: str,
    actor: User = Depends(_editors),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> None:
    await use_case.delete(actor, recipe_id)


# ── Personal ─────────────────────────────────────────────────────────


@router.put("/recipes/{recipe_id}/favourite", status_code=status.HTTP_204_NO_CONTENT)
async def set_favourite(
    recipe_id: str,
    body: FavouriteRequest,
    user: User = Depends(get_current_user),
    use_case: ManagePersonal = Depends(get_manage_personal),
) -> None:
    await use_case.set_favourite(user, recipe_id, body.favourite)


@router.put("/recipes/{recipe_id}/rating", response_model=RatingResponse)
async def rate_recipe(
    recipe_id: str,
    body: RatingRequest,
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    use_case: ManagePersonal = Depends(get_manage_personal),
) -> RatingResponse:
    """Rates the recipe, or with `variation_id` one of its variations; the
    average and count answered are of what was rated."""
    rating = await use_case.rate(
        user,
        recipe_id,
        body.stars,
        body.comment,
        str(body.variation_id) if body.variation_id else None,
    )
    if rating.variation_id is not None:
        average, count = (await c.ratings.variation_stats([rating.variation_id])).get(
            rating.variation_id, (None, 0)
        )
    else:
        average, count = (await c.ratings.stats([rating.recipe_id])).get(
            rating.recipe_id, (None, 0)
        )
    return RatingResponse(
        stars=rating.stars, comment=rating.comment, rating_average=average, rating_count=count
    )


@router.delete("/recipes/{recipe_id}/rating", response_model=RatingStatsResponse)
async def remove_rating(
    recipe_id: str,
    variation_id: str | None = Query(None, description="Removes the rating of this variation."),
    user: User = Depends(get_current_user),
    c: Cookbook = Depends(get_cookbook),
    use_case: ManagePersonal = Depends(get_manage_personal),
    recipes: ManageRecipes = Depends(get_manage_recipes),
) -> RatingStatsResponse:
    """Removes the viewer's rating and answers with the new average."""
    await use_case.unrate(user, recipe_id, variation_id)
    recipe = await recipes.get_visible(user, recipe_id)
    if variation_id:
        variation = await c.variations.get_by_public_id(variation_id)
        internal = variation.id if variation else 0
        average, count = (await c.ratings.variation_stats([internal])).get(internal, (None, 0))
    else:
        average, count = (await c.ratings.stats([recipe.id])).get(recipe.id, (None, 0))
    return RatingStatsResponse(rating_average=average, rating_count=count)


@router.put("/recipes/{recipe_id}/note", response_model=NoteResponse)
async def save_note(
    recipe_id: str,
    body: NoteRequest,
    user: User = Depends(get_current_user),
    use_case: ManagePersonal = Depends(get_manage_personal),
) -> NoteResponse:
    """The viewer's private note; nobody else ever sees it. An empty text
    deletes it."""
    note = await use_case.save_note(user, recipe_id, body.text)
    return NoteResponse(text=note.text if note else None, changed=note.changed if note else None)


@router.get("/recipes/{recipe_id}/cook-events", response_model=list[CookEventResponse])
async def recipe_cook_events(
    recipe_id: str,
    mine: bool = Query(False, description="Only the viewer's own cook events."),
    limit: int = Query(100, ge=1, le=500, description="At most this many, the newest."),
    user: User = Depends(get_current_user),
    presenter: Presenter = Depends(get_presenter),
    recipes: ManageRecipes = Depends(get_manage_recipes),
    events: ManageCookEvents = Depends(get_manage_cook_events),
) -> list[CookEventResponse]:
    """Who cooked this recipe when, newest first, at most `limit` of them."""
    recipe = await recipes.get_visible(user, recipe_id)
    found = await events.for_recipe(recipe.id, user_id=user.id if mine else None, limit=limit)
    return await presenter.cook_events(found)


# ── Revisions ────────────────────────────────────────────────────────


async def _revision_summary(
    revision: RecipeRevision, presenter: Presenter
) -> RecipeRevisionSummary:
    return RecipeRevisionSummary(
        number=revision.number,
        kind=revision.kind.value,
        created=revision.created,
        created_via=revision.created_via.value,
        author=await presenter.person(revision.author_id),
        note=revision.note,
        restored_from=revision.restored_from,
        credited_author=await presenter.person(revision.credited_author_id),
    )


@router.get("/recipes/{recipe_id}/revisions", response_model=Page[RecipeRevisionSummary])
async def list_recipe_revisions(
    recipe_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    actor: User = Depends(_editors),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> Page[RecipeRevisionSummary]:
    """The recipe's history, newest first; for whoever may edit it."""
    found, total = await use_case.revisions(actor, recipe_id, limit=limit, offset=offset)
    return Page(items=[await _revision_summary(r, presenter) for r in found], total=total)


@router.get("/recipes/{recipe_id}/revisions/{number}", response_model=RecipeRevisionResponse)
async def read_recipe_revision(
    recipe_id: str,
    number: int,
    actor: User = Depends(_editors),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeRevisionResponse:
    revision = await use_case.revision(actor, recipe_id, number)
    summary = await _revision_summary(revision, presenter)
    return RecipeRevisionResponse(**summary.model_dump(), snapshot=revision.snapshot)


@router.post("/recipes/{recipe_id}/revisions/{number}/restore", response_model=RecipeEditResponse)
async def restore_recipe_revision(
    recipe_id: str,
    number: int,
    actor: User = Depends(_editors),
    c: Cookbook = Depends(get_cookbook),
    presenter: Presenter = Depends(get_presenter),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> RecipeEditResponse:
    """Makes the revision's content the current recipe and records a
    `restored` revision; the status and visibility stay. 409
    `RevisionRestoreError` names an ingredient, unit, tag, equipment item
    or sub-recipe that no longer exists; vanished images are dropped."""
    return await _edit(await use_case.restore(actor, recipe_id, number), actor, c, presenter)
