"""
Recipes and their variations as `cuisine-recipes` entries
(`recipes_v1.py`). The mapping names every field it writes and does not go
through the revision snapshot, so the snapshot can change without changing
what another instance receives.

`SnapshotRefs` serves only as the lookup from internal ids to public ids
and names; a record missing from it is left out, as in a revision.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from src.cookbook.application.services.formats.recipes_v1 import EquipmentLineV1
from src.cookbook.application.services.formats.recipes_v1 import IngredientLineV1
from src.cookbook.application.services.formats.recipes_v1 import NoteV1
from src.cookbook.application.services.formats.recipes_v1 import RecipeContentV1
from src.cookbook.application.services.formats.recipes_v1 import RecipeTextV1
from src.cookbook.application.services.formats.recipes_v1 import ReferenceNamesV1
from src.cookbook.application.services.formats.recipes_v1 import StepTextV1
from src.cookbook.application.services.formats.recipes_v1 import StepV1
from src.cookbook.application.services.formats.recipes_v1 import VariationChangeV1
from src.cookbook.application.services.formats.recipes_v1 import VariationEquipmentV1
from src.cookbook.application.services.formats.recipes_v1 import VariationLineV1
from src.cookbook.application.services.formats.recipes_v1 import VariationV1
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.variation import RecipeVariation
from src.cookbook.domain.services.revisions import Reference
from src.cookbook.domain.services.revisions import SnapshotRefs


@dataclass
class UsedRecords:
    """The public ids of the catalogue records and recipes a set of entries
    names, which decides what goes into the document's catalogue."""

    ingredients: set[str] = field(default_factory=set)
    units: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    equipment: set[str] = field(default_factory=set)
    recipes: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)


def recipe_content(recipe: Recipe, refs: SnapshotRefs) -> RecipeContentV1:
    names: dict[str, dict[str, dict[str, str]]] = {
        "ingredients": {},
        "units": {},
        "tags": {},
        "equipment": {},
        "recipes": {},
    }

    def ref(kind: str, source: Mapping[int, Reference], internal: int | None) -> str | None:
        found = source.get(internal) if internal is not None else None
        if found is None:
            return None
        names[kind][found.public_id] = dict(sorted(found.names.items()))
        return found.public_id

    def file(internal: int | None) -> str | None:
        return refs.files.get(internal) if internal is not None else None

    def line(si: StepIngredient) -> IngredientLineV1:
        return IngredientLineV1(
            id=str(si.public_id),
            ingredient_id=ref("ingredients", refs.ingredients, si.ingredient_id),
            sub_recipe_id=ref("recipes", refs.recipes, si.sub_recipe_id),
            amount=si.amount,
            unit_id=ref("units", refs.units, si.unit_id),
            notes={k: NoteV1(note=v.note) for k, v in sorted(si.translations.items())},
        )

    def step(s: RecipeStep) -> StepV1:
        return StepV1(
            id=str(s.public_id),
            translations={k: StepTextV1(text=v.text) for k, v in sorted(s.translations.items())},
            duration_minutes=s.duration_minutes,
            image_id=file(s.image_file_id),
            ingredients=[line(si) for si in s.ingredients],
            equipment=[
                EquipmentLineV1(
                    id=str(se.public_id),
                    equipment_id=ref("equipment", refs.equipment, se.equipment_id),
                    count=se.count,
                    notes={k: NoteV1(note=v.note) for k, v in sorted(se.translations.items())},
                )
                for se in s.equipment
            ],
        )

    steps = [step(s) for s in recipe.steps]
    tag_ids = [t for t in (ref("tags", refs.tags, t) for t in recipe.tag_ids) if t]
    yield_unit = ref("units", refs.units, recipe.yield_unit_id)
    return RecipeContentV1(
        original_locale=recipe.original_locale,
        translations={
            k: RecipeTextV1(title=v.title, description=v.description, tips=v.tips)
            for k, v in sorted(recipe.translations.items())
        },
        base_servings=recipe.base_servings,
        prep_minutes=recipe.prep_minutes,
        cook_minutes=recipe.cook_minutes,
        rest_minutes=recipe.rest_minutes,
        difficulty=recipe.difficulty.value,
        cover_image_id=file(recipe.cover_file_id),
        source_url=recipe.source_url,
        source_name=recipe.source_name,
        tag_ids=tag_ids,
        yield_amount=recipe.yield_amount,
        yield_unit_id=yield_unit,
        steps=steps,
        ingredients=[line(si) for si in recipe.ingredients],
        names=ReferenceNamesV1(**names),
    )


def _text(value: Any) -> str:
    return str(value) if value is not None else ""


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def _whole(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _id(value: Any) -> str | None:
    return str(value) if value else None


def variation_change(stored: Mapping[str, Any]) -> VariationChangeV1:
    """A change as the variation stores it (`variation_resolver.stored`)."""
    return VariationChangeV1(
        id=_text(stored.get("id")),
        kind=_text(stored.get("kind")),
        step=_whole(stored.get("step")),
        ingredient_id=_id(stored.get("ingredient_id")),
        sub_recipe_id=_id(stored.get("sub_recipe_id")),
        to_ingredient_id=_id(stored.get("to_ingredient_id")),
        amount=_number(stored.get("amount")),
        unit_id=_id(stored.get("unit_id")),
        keep_amount=bool(stored.get("keep_amount", True)),
        note=_text(stored.get("note")),
        text=_text(stored.get("text")),
        duration_minutes=_whole(stored.get("duration_minutes")),
        lines=[
            VariationLineV1(
                ingredient_id=_text(line.get("ingredient_id")),
                amount=_number(line.get("amount")),
                unit_id=_id(line.get("unit_id")),
                note=_text(line.get("note")),
            )
            for line in stored.get("lines") or []
        ],
        equipment=[
            VariationEquipmentV1(
                equipment_id=_text(item.get("equipment_id")),
                count=_whole(item.get("count")),
                note=_text(item.get("note")),
            )
            for item in stored.get("equipment") or []
        ],
    )


def variation_entry(variation: RecipeVariation, author_name: str | None) -> VariationV1:
    return VariationV1(
        id=str(variation.public_id),
        name=variation.name,
        locale=variation.locale,
        note=variation.note,
        private=variation.private,
        author_name=author_name,
        changes=[variation_change(c) for c in variation.changes],
    )


def collect_used(
    used: UsedRecords, content: RecipeContentV1, variations: list[VariationV1]
) -> None:
    """Adds every record the content and the variations name to `used`."""
    used.ingredients |= set(content.names.ingredients)
    used.units |= set(content.names.units)
    used.tags |= set(content.names.tags)
    used.equipment |= set(content.names.equipment)
    used.recipes |= set(content.names.recipes)
    used.files |= {f for f in [content.cover_image_id, *(s.image_id for s in content.steps)] if f}
    for variation in variations:
        for change in variation.changes:
            used.ingredients |= {i for i in (change.ingredient_id, change.to_ingredient_id) if i}
            used.ingredients |= {line.ingredient_id for line in change.lines if line.ingredient_id}
            used.units |= {u for u in (change.unit_id, *(ln.unit_id for ln in change.lines)) if u}
            used.equipment |= {e.equipment_id for e in change.equipment if e.equipment_id}
            if change.sub_recipe_id:
                used.recipes.add(change.sub_recipe_id)
