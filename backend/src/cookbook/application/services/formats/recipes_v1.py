"""
Version 1 of the `cuisine-recipes` format: `recipes.json` inside a `.cui`
file (a zip that also holds the images under `files/`).

Records are named by their public id on the exporting instance: recipes,
steps and lines by their own, ingredients, units, tags and equipment by the
key of their entry in `catalogue`, images by the key of their entry in
`files`. An importer maps every one of them to its own records and never
takes a public id over. The document's `instance_id` and a recipe's `id`
together identify the recipe at its source.

The recipe's content sits under the key `snapshot` for historical reasons:
the first release wrote the internal revision snapshot there. The field
list below is the contract now, independent of that snapshot.

These dataclasses are a published contract: within version 1 a field may
only be added, with a default, and never renamed, retyped or removed.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Literal

from src.cookbook.application.services.formats.catalogue_v1 import CatalogueSectionV1

FORMAT: Final = "cuisine-recipes"
VERSION: Final = 1
MANIFEST: Final = "recipes.json"


def _doc(text: str) -> dict[str, str]:
    return {"doc": text}


@dataclass(frozen=True, kw_only=True)
class RecipeTextV1:
    title: str = ""
    description: str = ""
    tips: str = ""


@dataclass(frozen=True, kw_only=True)
class StepTextV1:
    text: str = field(default="", metadata=_doc("Markdown with mentions such as @[Name](kind:id)."))


@dataclass(frozen=True, kw_only=True)
class NoteV1:
    note: str = ""


@dataclass(frozen=True, kw_only=True)
class IngredientLineV1:
    """A catalogue ingredient or a sub-recipe, exactly one of them."""

    id: str | None = field(default=None, metadata=_doc("The line's public id at the source."))
    ingredient_id: str | None = None
    sub_recipe_id: str | None = field(
        default=None, metadata=_doc("The id of another recipe of the document.")
    )
    amount: float | None = None
    unit_id: str | None = None
    notes: dict[str, NoteV1] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class EquipmentLineV1:
    id: str | None = field(default=None, metadata=_doc("The line's public id at the source."))
    equipment_id: str | None = None
    count: int | None = None
    notes: dict[str, NoteV1] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class StepV1:
    id: str | None = field(default=None, metadata=_doc("The step's public id at the source."))
    translations: dict[str, StepTextV1] = field(default_factory=dict)
    duration_minutes: int | None = None
    image_id: str | None = None
    ingredients: list[IngredientLineV1] = field(default_factory=list)
    equipment: list[EquipmentLineV1] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ReferenceNamesV1:
    """The names per locale of every record the recipe refers to, by id, so
    an importer can name what it could not place."""

    ingredients: dict[str, dict[str, str]] = field(default_factory=dict)
    units: dict[str, dict[str, str]] = field(default_factory=dict)
    tags: dict[str, dict[str, str]] = field(default_factory=dict)
    equipment: dict[str, dict[str, str]] = field(default_factory=dict)
    recipes: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class RecipeContentV1:
    """The recipe's content in every language. Status, visibility, shares and
    the personal layer are never part of it."""

    schema_version: int = field(default=1, metadata=_doc("Always 1; kept for early readers."))
    original_locale: str
    translations: dict[str, RecipeTextV1] = field(default_factory=dict)
    base_servings: int = 4
    prep_minutes: int | None = None
    cook_minutes: int | None = None
    rest_minutes: int | None = None
    difficulty: str = field(default="easy", metadata=_doc("easy, medium or hard."))
    cover_image_id: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    tag_ids: list[str] = field(default_factory=list)
    yield_amount: float | None = None
    yield_unit_id: str | None = None
    steps: list[StepV1] = field(default_factory=list)
    ingredients: list[IngredientLineV1] = field(
        default_factory=list,
        metadata=_doc(
            "The ingredient list declared for the whole recipe, in its order. A reader "
            "derives the recipe's list as the larger of it and what the steps use; "
            "without it the steps alone count."
        ),
    )
    names: ReferenceNamesV1 = field(default_factory=ReferenceNamesV1)


@dataclass(frozen=True, kw_only=True)
class VariationLineV1:
    ingredient_id: str
    amount: float | None = None
    unit_id: str | None = None
    note: str = ""


@dataclass(frozen=True, kw_only=True)
class VariationEquipmentV1:
    equipment_id: str
    count: int | None = None
    note: str = ""


@dataclass(frozen=True, kw_only=True)
class VariationChangeV1:
    """One difference to the recipe. Steps are numbered from 1 as the recipe
    is in this document."""

    id: str = ""
    kind: str = field(metadata=_doc("swap, add_line, remove_line, step_text or extra_step."))
    step: int | None = None
    ingredient_id: str | None = None
    sub_recipe_id: str | None = None
    to_ingredient_id: str | None = None
    amount: float | None = None
    unit_id: str | None = None
    keep_amount: bool = True
    note: str = ""
    text: str = ""
    duration_minutes: int | None = None
    lines: list[VariationLineV1] = field(default_factory=list)
    equipment: list[VariationEquipmentV1] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class VariationV1:
    """A variation of the recipe, written in one locale."""

    id: str = field(metadata=_doc("The variation's public id at the source."))
    name: str
    locale: str
    note: str = ""
    private: bool = field(default=False, metadata=_doc("Only exported to its own author."))
    author_name: str | None = field(
        default=None, metadata=_doc("The author's display name, when the author shows it.")
    )
    author_avatar: str | None = field(
        default=None,
        metadata=_doc(
            "The key in `files` of the author's avatar, under the same rule as `author_name`; "
            "set in peering payloads only."
        ),
    )
    changes: list[VariationChangeV1] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class RecipeEntryV1:
    id: str = field(metadata=_doc("The recipe's public id at the source."))
    title: str = ""
    status: str = "published"
    snapshot: RecipeContentV1
    variations: list[VariationV1] = field(default_factory=list)
    author_name: str | None = field(
        default=None,
        metadata=_doc(
            "The recipe author's display name, when the author shows it to paired instances; "
            "set in peering payloads only."
        ),
    )
    author_avatar: str | None = field(
        default=None,
        metadata=_doc(
            "The key in `files` of the recipe author's avatar, under the same rule as "
            "`author_name`; set in peering payloads only."
        ),
    )


@dataclass(frozen=True, kw_only=True)
class FileEntryV1:
    path: str = field(metadata=_doc("The member of the zip that holds the bytes."))
    name: str = ""
    content_type: str = ""


@dataclass(frozen=True, kw_only=True)
class RecipesDocumentV1:
    """Recipes with the catalogue entries and images they use. A sub-recipe
    comes before the recipes that use it."""

    format: Literal["cuisine-recipes"]
    version: Literal[1]
    exported_at: str = ""
    instance_id: str | None = field(
        default=None, metadata=_doc("The instance id of the exporting instance.")
    )
    recipes: list[RecipeEntryV1]
    catalogue: CatalogueSectionV1 = field(default_factory=CatalogueSectionV1)
    files: dict[str, FileEntryV1] = field(default_factory=dict)
