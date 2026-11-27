"""
Version 1 of the `cuisine-catalogue` format, and the catalogue entries that
version 1 of `cuisine-recipes` shares.

Entries are keyed by their public id on the exporting instance. Another
instance matches an entry by its seed key first, then by name or alias in
any language, units by code; it never takes the public id over. Enum values
(unit kinds, tag kinds, allergens, diet markers, equipment kinds) travel as
plain text, so a reader can keep or report a value it does not know.

These dataclasses are a published contract: within version 1 a field may
only be added, with a default, and never renamed, retyped or removed.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Literal

FORMAT: Final = "cuisine-catalogue"
VERSION: Final = 1


def _doc(text: str) -> dict[str, str]:
    return {"doc": text}


@dataclass(frozen=True, kw_only=True)
class NamedRefV1:
    """A category or family an ingredient belongs to, by seed key and names."""

    seed_key: str | None = None
    names: dict[str, str] = field(default_factory=dict, metadata=_doc("Name per locale."))
    id: str | None = field(default=None, metadata=_doc("Its public id on the exporting instance."))


@dataclass(frozen=True, kw_only=True)
class UnitEntryV1:
    seed_key: str | None = None
    code: str = field(metadata=_doc("The stable unit code, such as g or tbsp."))
    names: dict[str, str] = field(default_factory=dict, metadata=_doc("Name per locale."))
    kind: str | None = field(default=None, metadata=_doc("mass, volume, count or other."))
    to_base: float | None = field(
        default=None, metadata=_doc("Grams per unit for mass, millilitres for volume.")
    )
    plural_names: dict[str, str] = field(default_factory=dict)
    abbreviations: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class TagEntryV1:
    seed_key: str | None = None
    kind: str | None = None
    names: dict[str, str] = field(default_factory=dict)
    color: str | None = field(default=None, metadata=_doc("A hex colour such as #d97706."))


@dataclass(frozen=True, kw_only=True)
class CategoryEntryV1:
    seed_key: str | None = None
    names: dict[str, str] = field(default_factory=dict)
    sort_order: int = 0


@dataclass(frozen=True, kw_only=True)
class FamilyEntryV1:
    seed_key: str | None = None
    names: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class IngredientNameV1:
    name: str = ""
    plural_name: str = ""


@dataclass(frozen=True, kw_only=True)
class NutritionV1:
    """Per 100 g: energy in kcal, everything else in grams. Null is unknown."""

    kcal: float | None = None
    protein: float | None = None
    fat: float | None = None
    saturated_fat: float | None = None
    carbohydrates: float | None = None
    sugar: float | None = None
    fibre: float | None = None
    salt: float | None = None


@dataclass(frozen=True, kw_only=True)
class ConversionV1:
    unit_id: str = field(metadata=_doc("A key of the document's units."))
    grams: float


@dataclass(frozen=True, kw_only=True)
class IngredientEntryV1:
    seed_key: str | None = None
    original_locale: str | None = None
    names: dict[str, IngredientNameV1] = field(default_factory=dict)
    aliases: dict[str, list[str]] = field(
        default_factory=dict, metadata=_doc("Other names per locale.")
    )
    category: NamedRefV1 | None = None
    family: NamedRefV1 | None = None
    nutrition: NutritionV1 = field(default_factory=NutritionV1)
    extended_nutrition: dict[str, float] = field(
        default_factory=dict,
        metadata=_doc("Extended nutrients per 100 g by key, such as vitamin_c_mg."),
    )
    season_months: list[int] = field(
        default_factory=list, metadata=_doc("Months 1 to 12 in season; empty is not seasonal.")
    )
    density_g_per_ml: float | None = None
    conversions: list[ConversionV1] = field(default_factory=list)
    allergens: list[str] = field(default_factory=list)
    diet_markers: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class EquipmentEntryV1:
    seed_key: str | None = None
    kind: str | None = field(
        default=None, metadata=_doc("cookware, bakeware, appliance or utensil.")
    )
    names: dict[str, str] = field(default_factory=dict)
    aliases: dict[str, list[str]] = field(default_factory=dict)
    icon: str | None = None
    basic: bool = False


@dataclass(frozen=True, kw_only=True)
class CatalogueSectionV1:
    """The catalogue entries a `cuisine-recipes` document refers to."""

    units: dict[str, UnitEntryV1] = field(default_factory=dict)
    tags: dict[str, TagEntryV1] = field(default_factory=dict)
    ingredients: dict[str, IngredientEntryV1] = field(default_factory=dict)
    equipment: dict[str, EquipmentEntryV1] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class CatalogueDocumentV1:
    """A whole catalogue: units, tags, ingredient categories and families,
    ingredients and equipment. It carries no images."""

    format: Literal["cuisine-catalogue"]
    version: Literal[1]
    exported_at: str = ""
    instance_id: str | None = field(
        default=None, metadata=_doc("The instance id of the exporting instance.")
    )
    units: dict[str, UnitEntryV1] = field(default_factory=dict)
    tags: dict[str, TagEntryV1] = field(default_factory=dict)
    categories: dict[str, CategoryEntryV1] = field(default_factory=dict)
    families: dict[str, FamilyEntryV1] = field(default_factory=dict)
    ingredients: dict[str, IngredientEntryV1] = field(default_factory=dict)
    equipment: dict[str, EquipmentEntryV1] = field(default_factory=dict)
