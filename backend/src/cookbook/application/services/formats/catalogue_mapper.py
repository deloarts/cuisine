"""
Catalogue records as format entries (`catalogue_v1.py`). Each function
names every field it writes, so a change to an entity or a column never
changes a document by accident.
"""

from collections.abc import Iterable
from collections.abc import Mapping

from src.cookbook.application.services.formats.catalogue_v1 import FORMAT
from src.cookbook.application.services.formats.catalogue_v1 import VERSION
from src.cookbook.application.services.formats.catalogue_v1 import CatalogueDocumentV1
from src.cookbook.application.services.formats.catalogue_v1 import CategoryEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import ConversionV1
from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import FamilyEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientNameV1
from src.cookbook.application.services.formats.catalogue_v1 import NamedRefV1
from src.cookbook.application.services.formats.catalogue_v1 import NutritionV1
from src.cookbook.application.services.formats.catalogue_v1 import TagEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import UnitEntryV1
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import NameText


def _names(translations: Mapping[str, NameText]) -> dict[str, str]:
    return {k: v.name for k, v in sorted(translations.items())}


def unit_entry(unit: Unit) -> UnitEntryV1:
    texts = sorted(unit.translations.items())
    return UnitEntryV1(
        seed_key=unit.seed_key,
        code=unit.code,
        names={k: v.name for k, v in texts},
        kind=unit.kind.value,
        to_base=unit.to_base,
        plural_names={k: v.plural_name for k, v in texts},
        abbreviations={k: v.abbreviation for k, v in texts},
    )


def tag_entry(tag: Tag) -> TagEntryV1:
    return TagEntryV1(
        seed_key=tag.seed_key,
        kind=tag.kind.value,
        names=_names(tag.translations),
        color=tag.color,
    )


def category_entry(category: IngredientCategory) -> CategoryEntryV1:
    return CategoryEntryV1(
        seed_key=category.seed_key,
        names=_names(category.translations),
        sort_order=category.sort_order,
    )


def family_entry(family: IngredientFamily) -> FamilyEntryV1:
    return FamilyEntryV1(seed_key=family.seed_key, names=_names(family.translations))


def _ref(record: IngredientCategory | IngredientFamily | None) -> NamedRefV1 | None:
    if record is None:
        return None
    return NamedRefV1(
        seed_key=record.seed_key, names=_names(record.translations), id=str(record.public_id)
    )


def nutrition_entry(nutrition: Nutrition) -> NutritionV1:
    return NutritionV1(
        kcal=nutrition.kcal,
        protein=nutrition.protein,
        fat=nutrition.fat,
        saturated_fat=nutrition.saturated_fat,
        carbohydrates=nutrition.carbohydrates,
        sugar=nutrition.sugar,
        fibre=nutrition.fibre,
        salt=nutrition.salt,
    )


def ingredient_entry(
    ingredient: Ingredient,
    *,
    categories: Mapping[int, IngredientCategory],
    families: Mapping[int, IngredientFamily],
    unit_ids: Mapping[int, str],
) -> IngredientEntryV1:
    """The ingredient with its category and family named by seed key and
    names, and its conversions by the public id of their unit. A conversion
    whose unit is not in `unit_ids` is left out."""
    return IngredientEntryV1(
        seed_key=ingredient.seed_key,
        original_locale=ingredient.original_locale,
        names={
            k: IngredientNameV1(name=v.name, plural_name=v.plural_name)
            for k, v in sorted(ingredient.translations.items())
        },
        aliases={k: list(v) for k, v in sorted(ingredient.aliases.items())},
        category=_ref(categories.get(ingredient.category_id) if ingredient.category_id else None),
        family=_ref(families.get(ingredient.family_id) if ingredient.family_id else None),
        nutrition=nutrition_entry(ingredient.nutrition),
        extended_nutrition=dict(sorted(ingredient.extended_nutrition.items())),
        season_months=sorted(ingredient.season_months),
        density_g_per_ml=ingredient.density_g_per_ml,
        conversions=[
            ConversionV1(unit_id=unit_ids[c.unit_id], grams=c.grams)
            for c in ingredient.conversions
            if c.unit_id in unit_ids
        ],
        allergens=[a.value for a in ingredient.allergens],
        diet_markers=[m.value for m in ingredient.diet_markers],
    )


def equipment_entry(item: Equipment) -> EquipmentEntryV1:
    return EquipmentEntryV1(
        seed_key=item.seed_key,
        kind=item.kind.value,
        names=_names(item.translations),
        aliases={k: list(v) for k, v in sorted(item.aliases.items())},
        icon=item.icon,
        basic=item.basic,
    )


def catalogue_document(
    *,
    exported_at: str,
    instance_id: str | None,
    units: Iterable[Unit],
    tags: Iterable[Tag],
    categories: Iterable[IngredientCategory],
    families: Iterable[IngredientFamily],
    ingredients: Iterable[Ingredient],
    equipment: Iterable[Equipment],
) -> CatalogueDocumentV1:
    """The whole catalogue as one `cuisine-catalogue` document, every entry
    keyed by its public id."""
    units = list(units)
    categories = list(categories)
    families = list(families)
    unit_ids = {u.id: str(u.public_id) for u in units}
    by_category = {c.id: c for c in categories}
    by_family = {f.id: f for f in families}
    return CatalogueDocumentV1(
        format=FORMAT,
        version=VERSION,
        exported_at=exported_at,
        instance_id=instance_id,
        units={str(u.public_id): unit_entry(u) for u in units},
        tags={str(t.public_id): tag_entry(t) for t in tags},
        categories={str(c.public_id): category_entry(c) for c in categories},
        families={str(f.public_id): family_entry(f) for f in families},
        ingredients={
            str(i.public_id): ingredient_entry(
                i, categories=by_category, families=by_family, unit_ids=unit_ids
            )
            for i in ingredients
        },
        equipment={str(e.public_id): equipment_entry(e) for e in equipment},
    )
