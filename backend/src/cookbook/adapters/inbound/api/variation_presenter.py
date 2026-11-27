"""
Builds the variation responses: a variation with the names of what its
changes refer to, and the markers that say what differs in the recipe with
the variation applied. It leans on the request's `Presenter` for people,
files and references.
"""

from typing import Any
from uuid import UUID

from src.cookbook.adapters.inbound.api.presenters import Presenter
from src.cookbook.adapters.inbound.api.presenters import equipment_ref
from src.cookbook.adapters.inbound.api.presenters import ingredient_name
from src.cookbook.adapters.inbound.api.presenters import unit_ref
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import OwnRating
from src.cookbook.adapters.inbound.api.schemas.variation_schema import LineMarkerView
from src.cookbook.adapters.inbound.api.schemas.variation_schema import RemovedLineView
from src.cookbook.adapters.inbound.api.schemas.variation_schema import StaleStepView
from src.cookbook.adapters.inbound.api.schemas.variation_schema import StepMarkerView
from src.cookbook.adapters.inbound.api.schemas.variation_schema import VariationChangeView
from src.cookbook.adapters.inbound.api.schemas.variation_schema import VariationEquipmentView
from src.cookbook.adapters.inbound.api.schemas.variation_schema import VariationLineView
from src.cookbook.adapters.inbound.api.schemas.variation_schema import VariationResponse
from src.cookbook.application.services.mirror_facts import mirrored_variation_avatar
from src.cookbook.application.services.variation_resolver import VariationResolver
from src.cookbook.application.use_cases.recipes.manage_variations import VariationInfo
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.variation import RecipeVariation
from src.cookbook.domain.services.variations import StepMarker


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except ValueError:
        return None


async def _change_view(
    presenter: Presenter,
    resolver: VariationResolver,
    raw: dict[str, Any],
    available: bool,
    applies: bool,
) -> VariationChangeView:
    locale = presenter.locale
    ingredient = await resolver.ingredient(raw.get("ingredient_id"))
    target = await resolver.ingredient(raw.get("to_ingredient_id"))
    unit = await resolver.unit(raw.get("unit_id"))
    sub = await resolver.recipe(raw.get("sub_recipe_id"))
    if sub is not None:
        await presenter.files([sub.cover_file_id])
    lines = []
    for line in raw.get("lines", []):
        line_ingredient = await resolver.ingredient(line.get("ingredient_id"))
        line_unit = await resolver.unit(line.get("unit_id"))
        lines.append(
            VariationLineView(
                ingredient_id=_uuid(line.get("ingredient_id")),
                ingredient_name=ingredient_name(line_ingredient, locale),
                amount=line.get("amount"),
                unit=unit_ref(line_unit, locale) if line_unit else None,
                note=str(line.get("note") or ""),
            )
        )
    equipment = []
    for item in raw.get("equipment", []):
        found = await resolver.equipment_item(item.get("equipment_id"))
        equipment.append(
            VariationEquipmentView(
                equipment=equipment_ref(found, locale) if found else None,
                count=item.get("count"),
                note=str(item.get("note") or ""),
            )
        )
    return VariationChangeView(
        id=str(raw.get("id", "")),
        kind=str(raw.get("kind", "")),
        step=raw.get("step"),
        ingredient_id=_uuid(raw.get("ingredient_id")),
        ingredient_name=ingredient_name(ingredient, locale) if raw.get("ingredient_id") else None,
        sub_recipe=presenter.sub_ref(sub) if raw.get("sub_recipe_id") else None,
        to_ingredient_id=_uuid(raw.get("to_ingredient_id")),
        to_ingredient_name=ingredient_name(target, locale) if raw.get("to_ingredient_id") else None,
        amount=raw.get("amount"),
        unit=unit_ref(unit, locale) if unit else None,
        keep_amount=bool(raw.get("keep_amount", True)),
        note=str(raw.get("note") or ""),
        text=str(raw.get("text") or ""),
        duration_minutes=raw.get("duration_minutes"),
        lines=lines,
        equipment=equipment,
        available=available,
        applies=applies,
    )


async def _source_avatar(
    presenter: Presenter, recipe: Recipe, variation: RecipeVariation
) -> UUID | None:
    """The avatar the source sent with a mirrored variation's author name."""
    if not variation.mirrored or variation.origin_public_id is None:
        return None
    mirror = await presenter.cookbook.mirrors.get(recipe.id)
    found = mirrored_variation_avatar(mirror, str(variation.origin_public_id)) if mirror else None
    return UUID(found) if found else None


async def variation_response(
    presenter: Presenter, resolver: VariationResolver, recipe: Recipe, info: VariationInfo
) -> VariationResponse:
    variation = info.variation
    unavailable = set(info.unavailable_change_ids)
    skipped = set(info.skipped_change_ids)
    return VariationResponse(
        id=variation.public_id,
        recipe_id=recipe.public_id,
        name=variation.name,
        note=variation.note,
        locale=variation.locale,
        private=variation.private,
        author=await presenter.person(variation.author_id),
        mirrored=variation.mirrored,
        source_author_name=variation.source_author_name,
        source_author_avatar_id=await _source_avatar(presenter, recipe, variation),
        based_on_revision=variation.based_on_revision,
        current_revision=info.staleness.current_revision,
        is_stale=bool(info.staleness.steps),
        base_revision_available=info.staleness.base_available,
        stale_steps=[
            StaleStepView(
                step=s.step, state=s.state, old_text=s.old_text, current_text=s.current_text
            )
            for s in info.staleness.steps
        ],
        changes=[
            await _change_view(
                presenter,
                resolver,
                raw,
                available=str(raw.get("id")) not in unavailable,
                applies=str(raw.get("id")) not in unavailable | skipped,
            )
            for raw in variation.changes
        ],
        rating_average=info.rating_average,
        rating_count=info.rating_count,
        own_rating=(
            OwnRating(stars=info.own_rating.stars, comment=info.own_rating.comment)
            if info.own_rating
            else None
        ),
        can_edit=info.can_edit,
        can_delete=info.can_delete,
        can_adopt=info.can_adopt,
        created=variation.created,
        changed=variation.changed,
    )


async def step_markers(
    presenter: Presenter, markers: list[StepMarker], factor: float
) -> list[StepMarkerView]:
    """The markers of the applied recipe; removed amounts are scaled like
    the recipe's own (`factor`)."""
    c = presenter.cookbook
    wanted = {
        i
        for m in markers
        for i in (
            *(line.swapped_from_ingredient_id for line in m.lines),
            *(r.ingredient_id for r in m.removed),
        )
        if i is not None
    }
    ingredients = {i.id: i for i in await c.ingredients.get_many(sorted(wanted))}
    units = {u.id: u for u in await c.units.list_all()}
    subs = {
        r.id: r
        for r in await c.recipes.get_many(
            sorted({r.sub_recipe_id for m in markers for r in m.removed if r.sub_recipe_id})
        )
    }
    await presenter.files(r.cover_file_id for r in subs.values())
    locale = presenter.locale
    views = []
    for marker in markers:
        removed = []
        for line in marker.removed:
            unit = units.get(line.unit_id) if line.unit_id is not None else None
            if line.sub_recipe_id is not None:
                ref = presenter.sub_ref(subs.get(line.sub_recipe_id))
                name = ref.title or ""
            else:
                ref = None
                name = ingredient_name(ingredients.get(line.ingredient_id or 0), locale)
            removed.append(
                RemovedLineView(
                    change_id=line.change_id,
                    ingredient_id=(
                        ingredients[line.ingredient_id].public_id
                        if line.ingredient_id in ingredients
                        else None
                    ),
                    sub_recipe=ref,
                    name=name,
                    amount=round(line.amount * factor, 3) if line.amount is not None else None,
                    unit=unit_ref(unit, locale) if unit else None,
                )
            )
        views.append(
            StepMarkerView(
                position=marker.position,
                origin_step=marker.origin_step,
                added=marker.added,
                text_changed=marker.text_changed,
                changed=marker.changed,
                change_ids=list(marker.change_ids),
                lines=[
                    LineMarkerView(
                        index=line.index,
                        kind=line.kind,
                        change_id=line.change_id,
                        swapped_from_ingredient_id=(
                            ingredients[line.swapped_from_ingredient_id].public_id
                            if line.swapped_from_ingredient_id in ingredients
                            else None
                        ),
                        swapped_from_name=(
                            ingredient_name(ingredients[line.swapped_from_ingredient_id], locale)
                            if line.swapped_from_ingredient_id in ingredients
                            else None
                        ),
                    )
                    for line in marker.lines
                ],
                removed=removed,
            )
        )
    return views
