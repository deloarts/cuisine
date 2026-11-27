"""
Turns what `ReadPublicRecipes` read into the responses of the public recipe
pages. Only what the page shows leaves here (`public_recipe_schema.py`):
sub-recipes and mentions the visitor may not see lose their title and id,
step text mentions carry names instead of catalogue ids, and the author is
the display name the owner chose to show, or nothing.
"""

import re
from collections.abc import Iterable
from uuid import UUID

from src.cookbook.adapters.inbound.api.deps import Cookbook
from src.cookbook.adapters.inbound.api.presenters import equipment_ref
from src.cookbook.adapters.inbound.api.presenters import ingredient_name
from src.cookbook.adapters.inbound.api.presenters import name_amount
from src.cookbook.adapters.inbound.api.presenters import nutrition
from src.cookbook.adapters.inbound.api.presenters import tag_ref
from src.cookbook.adapters.inbound.api.presenters import unit_ref
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicEquipmentNeed
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicIngredientLine
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicNutrition
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import (
    PublicRecipeDetailResponse,
)
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import (
    PublicRecipeSummaryResponse,
)
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicStep
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicStepEquipment
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicSubRecipe
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicSubRecipeNeed
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicTag
from src.cookbook.adapters.inbound.api.schemas.public_recipe_schema import PublicUnit
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import ExtendedNutrientAmount
from src.cookbook.application.dto.views import Lookups
from src.cookbook.application.use_cases.recipes.read_public_recipes import PublicRecipeSummary
from src.cookbook.application.use_cases.recipes.read_public_recipes import PublicRecipeView
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.services.equipment_rules import needed_equipment
from src.cookbook.domain.services.markdown import plain_text
from src.cookbook.domain.services.mentions import MENTION
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.value_objects.nutrients import BY_KEY as EXTENDED_BY_KEY
from src.cookbook.domain.value_objects.viewer import Viewer

# The id a rewritten mention carries instead of a catalogue id.
ZERO_ID = "00000000-0000-0000-0000-000000000000"
# The name of a mention of a sub-recipe the visitor may not see; the page
# shows its own placeholder instead.
HIDDEN_NAME = "?"
_NOT_IN_NAME = re.compile(r"[\[\]\n\r]+")


def public_tag(tag: Tag, locale: str) -> PublicTag:
    ref = tag_ref(tag, locale)
    return PublicTag(id=ref.id, kind=ref.kind, name=ref.name, color=ref.color)


def public_unit(unit: Unit | None, locale: str) -> PublicUnit | None:
    if unit is None:
        return None
    ref = unit_ref(unit, locale)
    return PublicUnit(
        kind=ref.kind, name=ref.name, plural_name=ref.plural_name, abbreviation=ref.abbreviation
    )


def _mention_name(name: str) -> str:
    """A name a mention can hold: no brackets or line breaks, never empty."""
    return " ".join(_NOT_IN_NAME.sub(" ", name).split()) or HIDDEN_NAME


class PublicPresenter:
    def __init__(self, c: Cookbook, viewer: Viewer, locale: str) -> None:
        self._c = c
        self.viewer = viewer
        self.locale = locale
        self._files: dict[int, UUID] = {}

    async def _load_files(self, ids: Iterable[int | None]) -> None:
        wanted = [i for i in ids if i is not None and i not in self._files]
        if wanted:
            self._files.update(await self._c.platform.files.public_ids(wanted))

    def _file(self, file_id: int | None) -> UUID | None:
        return self._files.get(file_id) if file_id is not None else None

    def _summary_fields(
        self,
        recipe: Recipe,
        summary: PublicRecipeSummary | None,
        lookups: Lookups,
        **derived: object,
    ) -> dict[str, object]:
        locale, text = resolve(recipe.translations, self.locale, recipe.original_locale)
        fields: dict[str, object] = {
            "id": recipe.public_id,
            "title": text.title,
            "description_text": plain_text(self.step_text(text.description, lookups)),
            "locale": locale,
            "available_locales": sorted(recipe.translations),
            "cover_image_id": self._file(recipe.cover_file_id),
            "base_servings": recipe.base_servings,
            "prep_minutes": recipe.prep_minutes,
            "cook_minutes": recipe.cook_minutes,
            "rest_minutes": recipe.rest_minutes,
            "total_minutes": recipe.total_minutes,
            "difficulty": recipe.difficulty.value,
            "tags": [
                public_tag(lookups.tags[t], self.locale)
                for t in recipe.tag_ids
                if t in lookups.tags
            ],
            "published_at": recipe.published_at,
        }
        if summary is not None:
            fields.update(
                allergens=[a.value for a in summary.allergens],
                diets=[d.value for d in summary.diets],
                season_months=list(summary.season_months),
                in_season=summary.in_season,
                author=summary.author,
                author_avatar=summary.author_avatar,
            )
        fields.update(derived)
        return fields

    async def summaries(
        self, summaries: list[PublicRecipeSummary], lookups: Lookups
    ) -> list[PublicRecipeSummaryResponse]:
        await self._load_files(s.recipe.cover_file_id for s in summaries)
        return [
            PublicRecipeSummaryResponse(**self._summary_fields(s.recipe, s, lookups))
            for s in summaries
        ]

    def sub_recipe(self, recipe: Recipe | None) -> PublicSubRecipe:
        """A sub-recipe with link and title when the visitor may see it, a
        placeholder without either otherwise."""
        if recipe is None or not can_view_recipe(self.viewer, recipe):
            return PublicSubRecipe(id=None, title=None, accessible=False, cover_image_id=None)
        _, text = resolve(recipe.translations, self.locale, recipe.original_locale)
        return PublicSubRecipe(
            id=recipe.public_id,
            title=text.title,
            accessible=True,
            cover_image_id=self._file(recipe.cover_file_id),
        )

    def _note(self, si: StepIngredient, original: str) -> str:
        if not si.translations:
            return ""
        return resolve(si.translations, self.locale, original)[1].note

    def _line(
        self, si: StepIngredient, factor: float, lookups: Lookups, original: str
    ) -> PublicIngredientLine:
        amount = round(si.amount * factor, 3) if si.amount is not None else None
        unit = lookups.units.get(si.unit_id) if si.unit_id is not None else None
        note = self._note(si, original)
        if si.sub_recipe_id is not None:
            ref = self.sub_recipe(lookups.recipes.get(si.sub_recipe_id))
            return PublicIngredientLine(
                name=ref.title or "",
                amount=amount,
                unit=public_unit(unit, self.locale),
                note=note,
                sub_recipe=ref,
            )
        return PublicIngredientLine(
            name=ingredient_name(
                lookups.ingredients.get(si.ingredient_id or 0),
                self.locale,
                name_amount(amount, unit),
            ),
            amount=amount,
            unit=public_unit(unit, self.locale),
            note=note,
        )

    def step_text(self, text: str, lookups: Lookups) -> str:
        """The step text with every mention rewritten for the visitor, so it
        names no catalogue entry by id and no hidden sub-recipe at all."""
        ingredients = {str(i.public_id): i for i in lookups.ingredients.values()}
        equipment = {str(e.public_id): e for e in lookups.equipment.values()}
        recipes = {str(r.public_id): r for r in lookups.recipes.values()}

        def rewrite(match: re.Match[str]) -> str:
            stored, kind, public_id = match.group(1), match.group(2), match.group(3).lower()
            if kind == "recipe":
                sub = recipes.get(public_id)
                if sub is None or not can_view_recipe(self.viewer, sub):
                    return f"@[{HIDDEN_NAME}](recipe:{ZERO_ID})"
                _, text = resolve(sub.translations, self.locale, sub.original_locale)
                return f"@[{_mention_name(text.title)}](recipe:{sub.public_id})"
            if kind == "equipment":
                item = equipment.get(public_id)
                name = equipment_ref(item, self.locale).name if item else stored
                return f"@[{_mention_name(name)}](equipment:{ZERO_ID})"
            ingredient = ingredients.get(public_id)
            name = ingredient_name(ingredient, self.locale) if ingredient else stored
            return f"@[{_mention_name(name)}](ingredient:{ZERO_ID})"

        return MENTION.sub(rewrite, text)

    async def detail(self, view: PublicRecipeView) -> PublicRecipeDetailResponse:
        recipe, derived, lookups = view.recipe, view.derived, view.lookups
        await self._load_files(
            [
                recipe.cover_file_id,
                *(s.image_file_id for s in recipe.steps),
                *(
                    r.cover_file_id
                    for r in lookups.recipes.values()
                    if can_view_recipe(self.viewer, r)
                ),
            ]
        )
        _, text = resolve(recipe.translations, self.locale, recipe.original_locale)
        steps = []
        for position, step in enumerate(recipe.steps, start=1):
            step_text = (
                resolve(step.translations, self.locale, recipe.original_locale)[1].text
                if step.translations
                else ""
            )
            steps.append(
                PublicStep(
                    position=position,
                    text=self.step_text(step_text, lookups),
                    duration_minutes=step.duration_minutes,
                    image_id=self._file(step.image_file_id),
                    ingredients=[
                        self._line(si, derived.factor, lookups, recipe.original_locale)
                        for si in step.ingredients
                    ],
                    equipment=[
                        PublicStepEquipment(
                            name=equipment_ref(
                                lookups.equipment[se.equipment_id], self.locale
                            ).name,
                            count=se.count,
                            note=(
                                resolve(se.translations, self.locale, recipe.original_locale)[
                                    1
                                ].note
                                if se.translations
                                else ""
                            ),
                        )
                        for se in step.equipment
                        if se.equipment_id in lookups.equipment
                    ],
                )
            )
        summary = PublicRecipeSummary(
            recipe=recipe,
            allergens=derived.allergens,
            diets=derived.diets,
            season_months=view.season_months,
            in_season=view.in_season,
            author=view.author,
            author_avatar=view.author_avatar,
        )
        return PublicRecipeDetailResponse(
            **self._summary_fields(
                recipe,
                summary,
                lookups,
                # Only step text holds mentions, but the rewrite costs
                # nothing and keeps a stray one from naming a hidden recipe.
                description=self.step_text(text.description, lookups),
                tips=self.step_text(text.tips, lookups),
                yield_amount=recipe.yield_amount,
                yield_unit=public_unit(lookups.units.get(recipe.yield_unit_id or 0), self.locale),
                servings=derived.servings,
                ingredients=[
                    PublicIngredientLine(
                        name=ingredient_name(
                            lookups.ingredients.get(line.ingredient_id),
                            self.locale,
                            name_amount(line.amount, lookups.units.get(line.unit_id or 0)),
                        ),
                        amount=round(line.amount, 3) if line.amount is not None else None,
                        unit=public_unit(lookups.units.get(line.unit_id or 0), self.locale),
                        note=(
                            resolve(line.notes, self.locale, recipe.original_locale)[1].note
                            if line.notes
                            else ""
                        ),
                    )
                    for line in derived.lines
                ],
                needs=[
                    PublicSubRecipeNeed(
                        sub_recipe=self.sub_recipe(lookups.recipes.get(need.recipe_id)),
                        amount=round(need.amount, 3) if need.amount is not None else None,
                        unit=public_unit(lookups.units.get(need.unit_id or 0), self.locale),
                        batches=round(need.batches, 3),
                    )
                    for need in derived.needs
                ],
                equipment=[
                    PublicEquipmentNeed(
                        name=equipment_ref(lookups.equipment[n.equipment_id], self.locale).name,
                        count=n.count,
                    )
                    for n in needed_equipment(recipe, lookups.recipes)
                    if n.equipment_id in lookups.equipment
                ],
                steps=steps,
                nutrition=PublicNutrition(
                    total=nutrition(derived.nutrition_total),
                    per_serving=nutrition(derived.nutrition_per_serving),
                    complete=derived.nutrition_complete,
                    extended=[
                        ExtendedNutrientAmount(
                            key=e.key,
                            unit=EXTENDED_BY_KEY[e.key].unit,
                            total=e.total,
                            per_serving=e.per_serving,
                            complete=e.complete,
                        )
                        for e in derived.extended
                    ],
                ),
                source_name=recipe.source_name,
                source_url=recipe.source_url,
            )
        )
