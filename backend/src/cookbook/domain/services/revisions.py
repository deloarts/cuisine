"""
The snapshot a recipe revision stores: the editable recipe in the shape of
the editor's response (`RecipeEditResponse`), by public id, plus the display
names of every ingredient, unit, tag, equipment item and sub-recipe it
refers to at that moment, so an old revision stays readable after a rename
or a deletion. Status, visibility, shares, the personal layer, cook events
and everything derived are never part of it.

Each step, ingredient line and equipment line carries its own public id
(`id`), so a restore keeps them. Snapshots written before lines had ids lack
the key; reading treats that like a line seen for the first time. The
recipe's declared ingredient list is under `ingredients`, in the shape of a
step's lines; snapshots written before it existed lack the key and restore
without one.

`schema_version` lets a later recipe shape upgrade older snapshots on read
(`upgrade_snapshot`).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Reference:
    """A referenced record: its public id and its names per locale."""

    public_id: str
    names: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SnapshotRefs:
    """Every record a recipe refers to, by internal id. A record missing
    here is left out of the snapshot."""

    ingredients: Mapping[int, Reference] = field(default_factory=dict)
    units: Mapping[int, Reference] = field(default_factory=dict)
    tags: Mapping[int, Reference] = field(default_factory=dict)
    equipment: Mapping[int, Reference] = field(default_factory=dict)
    recipes: Mapping[int, Reference] = field(default_factory=dict)
    files: Mapping[int, str] = field(default_factory=dict)


def build_snapshot(recipe: Recipe, refs: SnapshotRefs) -> dict[str, Any]:
    used: dict[str, dict[str, dict[str, str]]] = {
        "ingredients": {},
        "units": {},
        "tags": {},
        "equipment": {},
        "recipes": {},
    }

    def name(kind: str, source: Mapping[int, Reference], internal: int | None) -> str | None:
        found = source.get(internal) if internal is not None else None
        if found is None:
            return None
        used[kind][found.public_id] = dict(found.names)
        return found.public_id

    def step_of(step: RecipeStep) -> dict[str, Any]:
        return {
            "id": str(step.public_id),
            "translations": {k: {"text": v.text} for k, v in sorted(step.translations.items())},
            "duration_minutes": step.duration_minutes,
            "image_id": refs.files.get(step.image_file_id)
            if step.image_file_id is not None
            else None,
            "ingredients": [
                {
                    "id": str(si.public_id),
                    "ingredient_id": name("ingredients", refs.ingredients, si.ingredient_id),
                    "sub_recipe_id": name("recipes", refs.recipes, si.sub_recipe_id),
                    "amount": si.amount,
                    "unit_id": name("units", refs.units, si.unit_id),
                    "notes": {k: {"note": v.note} for k, v in sorted(si.translations.items())},
                }
                for si in step.ingredients
            ],
            "equipment": [
                {
                    "id": str(se.public_id),
                    "equipment_id": name("equipment", refs.equipment, se.equipment_id),
                    "count": se.count,
                    "notes": {k: {"note": v.note} for k, v in sorted(se.translations.items())},
                }
                for se in step.equipment
            ],
        }

    steps = [step_of(step) for step in recipe.steps]
    declared = [
        {
            "id": str(line.public_id),
            "ingredient_id": name("ingredients", refs.ingredients, line.ingredient_id),
            "sub_recipe_id": name("recipes", refs.recipes, line.sub_recipe_id),
            "amount": line.amount,
            "unit_id": name("units", refs.units, line.unit_id),
            "notes": {k: {"note": v.note} for k, v in sorted(line.translations.items())},
        }
        for line in recipe.ingredients
    ]
    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "original_locale": recipe.original_locale,
        "translations": {
            k: {"title": v.title, "description": v.description, "tips": v.tips}
            for k, v in sorted(recipe.translations.items())
        },
        "base_servings": recipe.base_servings,
        "prep_minutes": recipe.prep_minutes,
        "cook_minutes": recipe.cook_minutes,
        "rest_minutes": recipe.rest_minutes,
        "difficulty": recipe.difficulty.value,
        "cover_image_id": refs.files.get(recipe.cover_file_id)
        if recipe.cover_file_id is not None
        else None,
        "source_url": recipe.source_url,
        "source_name": recipe.source_name,
        "tag_ids": [t for t in (name("tags", refs.tags, t) for t in recipe.tag_ids) if t],
        "yield_amount": recipe.yield_amount,
        "yield_unit_id": name("units", refs.units, recipe.yield_unit_id),
        "steps": steps,
        "ingredients": declared,
    }
    snapshot["names"] = used
    return snapshot


def upgrade_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """The snapshot in the current shape. Version 1 is the only one so far;
    a later version adds its upgrade step here."""
    return {**snapshot, "schema_version": snapshot.get("schema_version", SCHEMA_VERSION)}


def display_name(snapshot: dict[str, Any], kind: str, public_id: str, locale: str) -> str:
    """The name a snapshot recorded for a referenced record, in `locale`
    when it has one, else any; the id when it recorded none."""
    names: dict[str, str] = snapshot.get("names", {}).get(kind, {}).get(public_id, {})
    return names.get(locale) or next(iter(names.values()), public_id)


def snapshot_image_ids(snapshot: Mapping[str, Any]) -> set[str]:
    """The public ids of the stored files a snapshot refers to, lower case:
    the cover and every step image. Restoring the revision puts them back on
    the recipe, so the files must stay while the revision does."""
    found = {snapshot.get("cover_image_id")}
    for step in snapshot.get("steps") or []:
        if isinstance(step, Mapping):
            found.add(step.get("image_id"))
    return {str(f).lower() for f in found if f}
