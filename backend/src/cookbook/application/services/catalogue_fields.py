"""
Catalogue entries as named fields, the comparison of two such field sets and
the writing of accepted values, shared by the catalogue file import and the
suggestions from paired instances.

Every kind (unit, tag, category, family, ingredient, equipment) is turned
into a flat dict of fields with the names of the reference data updates:
`names.<locale>`, `aliases.<locale>`, `category`, `family`,
`nutrition.<nutrient>`, `extended.<key>`, `density_g_per_ml`, `conversions`,
`allergens`, `diet_markers`, `season_months`, `to_base`, `kind`, `color`,
`icon` and `basic`. Both sides of a comparison are built from format entries
(the local side through the catalogue mapper), so they compare like for
like. A record a field points at (a category, a family, the unit of a
conversion) is a `Ref`, compared by identity and shown by name.

An incoming value that is empty is a gap, never a proposal to clear the
value here, except for allergens, diet markers and season months, where an
empty list is a statement. Allergens and diet markers drive the allergy and
diet warnings, so they are listed first.

`CatalogueWriter` writes accepted values through the normal use cases, so
every rule of an edit applies (a taken name raises `DuplicateNameError`).
"""

import hashlib
import json
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import Any
from typing import Final

from src.cookbook.application.services.formats.catalogue_mapper import category_entry
from src.cookbook.application.services.formats.catalogue_mapper import equipment_entry
from src.cookbook.application.services.formats.catalogue_mapper import family_entry
from src.cookbook.application.services.formats.catalogue_mapper import ingredient_entry
from src.cookbook.application.services.formats.catalogue_mapper import tag_entry
from src.cookbook.application.services.formats.catalogue_mapper import unit_entry
from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import TagEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import UnitEntryV1
from src.cookbook.application.use_cases.equipment.manage_equipment import EquipmentCommand
from src.cookbook.application.use_cases.equipment.manage_equipment import ManageEquipment
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ConversionCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import IngredientCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ManageIngredients
from src.cookbook.application.use_cases.resources.manage_resources import CategoryCommand
from src.cookbook.application.use_cases.resources.manage_resources import ManageResources
from src.cookbook.application.use_cases.resources.manage_resources import TagCommand
from src.cookbook.application.use_cases.resources.manage_resources import UnitCommand
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.services.translations import LOCALES
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrition import NUTRIENTS
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.platform.domain.entities.user import User

# Fields that drive the allergy and diet warnings, listed first.
SAFETY_FIELDS: Final = ("allergens", "diet_markers")
# Fields whose empty incoming value is a statement (no allergens, not
# seasonal) rather than a gap, so it is compared like any other value.
EMPTY_COUNTS: Final = frozenset({"allergens", "diet_markers", "season_months"})

type Fields = dict[str, Any]
type Local = Unit | Tag | IngredientCategory | IngredientFamily | Ingredient | Equipment


@dataclass(frozen=True)
class Ref:
    """A record a field points at (a category, a family, a unit), compared
    by identity and shown by name. The key is `local:<public id>` for a
    record here, or another key the caller resolves, such as
    `new:<kind>:<source id>` for an entry an import creates."""

    key: str
    label: str = field(compare=False)


# Turns a reference into the public id of a record here, or None when the
# record does not exist (yet).
type Resolver = Callable[[Ref | None], str | None]


@dataclass(frozen=True)
class FieldDifference:
    field: str
    current: Any
    incoming: Any


@dataclass(frozen=True)
class CatalogueLookups:
    """The records ingredients refer to, by internal id."""

    categories: Mapping[int, IngredientCategory]
    families: Mapping[int, IngredientFamily]
    units: Mapping[int, Unit]


def first_name(names: Mapping[str, str], preferred: str | None = None) -> str:
    for locale in (preferred, "en-GB", "de-AT", *sorted(names)):
        if locale and names.get(locale):
            return str(names[locale])
    return ""


def in_locales[V](values: Mapping[str, V]) -> dict[str, V]:
    return {k: v for k, v in sorted(values.items()) if k in LOCALES}


def clean_list(values: list[str]) -> list[str]:
    return sorted({v.strip() for v in values if v.strip()}, key=str.casefold)


def _num(value: Any) -> float | None:
    return float(value) if value is not None else None


def differs(name: str, current: Any, incoming: Any) -> bool:
    """Whether the field is listed: the values differ and the incoming side
    states a value. An absent name, alias list, nutrient or reference is a
    gap, never a proposal to clear the value here."""
    if incoming is None:
        return False
    if incoming in ("", [], {}, ()) and name.partition(".")[0] not in EMPTY_COUNTS:
        return False
    return bool(current != incoming)


def find_differences(incoming: Fields, current: Fields) -> list[FieldDifference]:
    """Every listed difference, allergens and diet markers first."""
    found = [
        FieldDifference(field=name, current=current.get(name), incoming=value)
        for name, value in incoming.items()
        if differs(name, current.get(name), value)
    ]
    return sorted(found, key=lambda d: (not is_safety(d.field), d.field))


def is_safety(name: str) -> bool:
    return name in SAFETY_FIELDS


def plain(value: Any) -> Any:
    """A field value as JSON: references by name, conversions as unit
    code to grams."""
    if isinstance(value, Ref):
        return value.label
    if isinstance(value, tuple):
        return {ref.label: grams for ref, grams in value}
    return value


def value_hash(value: Any) -> str:
    """A stable digest of a field value, references by identity, so a
    value that only changes its display name keeps its digest."""
    if isinstance(value, Ref):
        canonical: Any = {"ref": value.key}
    elif isinstance(value, tuple):
        canonical = [[ref.key, grams] for ref, grams in value]
    else:
        canonical = value
    data = json.dumps(canonical, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(data.encode()).hexdigest()


def row_names(row: Local) -> dict[str, str]:
    return {k: t.name for k, t in row.translations.items()}


def local_ref(row: IngredientCategory | IngredientFamily | Unit, locale: str) -> Ref:
    label = row.code if isinstance(row, Unit) else first_name(row_names(row), locale)
    return Ref(f"local:{row.public_id}", label)


def resolve_local(ref: Ref | None) -> str | None:
    """A resolver that knows only records here."""
    if ref is None or not ref.key.startswith("local:"):
        return None
    return ref.key.removeprefix("local:")


# ── Fields per kind, from format entries ─────────────────────────────


def named_fields(names: Mapping[str, str]) -> Fields:
    return {f"names.{loc}": n for loc, n in in_locales(names).items() if n}


def unit_fields(e: UnitEntryV1) -> Fields:
    fields: Fields = {
        f"names.{loc}": [name, e.plural_names.get(loc) or "", e.abbreviations.get(loc) or ""]
        for loc, name in in_locales(e.names).items()
        if name
    }
    fields["kind"] = e.kind if e.kind in UnitKind else None
    fields["to_base"] = _num(e.to_base)
    return fields


def tag_fields(e: TagEntryV1) -> Fields:
    return {
        **named_fields(e.names),
        "kind": e.kind if e.kind in TagKind else None,
        "color": e.color,
    }


def equipment_fields(e: EquipmentEntryV1) -> Fields:
    fields = named_fields(e.names)
    for loc, aliases in in_locales(e.aliases).items():
        fields[f"aliases.{loc}"] = clean_list(aliases)
    fields.update(
        {
            "kind": e.kind if e.kind in EquipmentKind else None,
            "icon": e.icon,
            "basic": e.basic,
        }
    )
    return fields


def ingredient_fields(
    e: IngredientEntryV1,
    category: Ref | None,
    family: Ref | None,
    conversions: tuple[tuple[Ref, float], ...],
) -> Fields:
    fields: Fields = {
        f"names.{loc}": [text.name, text.plural_name or text.name]
        for loc, text in in_locales(e.names).items()
        if text.name
    }
    for loc, aliases in in_locales(e.aliases).items():
        fields[f"aliases.{loc}"] = clean_list(aliases)
    fields["category"] = category
    fields["family"] = family
    for n in NUTRIENTS:
        fields[f"nutrition.{n}"] = _num(getattr(e.nutrition, n))
    for k in EXTENDED_KEYS:
        fields[f"extended.{k}"] = _num(e.extended_nutrition.get(k))
    fields["density_g_per_ml"] = _num(e.density_g_per_ml)
    fields["conversions"] = conversions
    fields["allergens"] = sorted({a for a in e.allergens if a in Allergen})
    fields["diet_markers"] = sorted({m for m in e.diet_markers if m in DietMarker})
    fields["season_months"] = sorted(set(e.season_months))
    return fields


def sorted_conversions(pairs: list[tuple[Ref, float]]) -> tuple[tuple[Ref, float], ...]:
    return tuple(sorted(pairs, key=lambda pair: pair[0].key))


def current_fields(kind: str, local: Any, lookups: CatalogueLookups, locale: str) -> Fields:
    """The fields of an entry here, built the same way as incoming ones."""
    match kind:
        case "category":
            return named_fields(category_entry(local).names)
        case "family":
            return named_fields(family_entry(local).names)
        case "unit":
            return unit_fields(unit_entry(local))
        case "tag":
            return tag_fields(tag_entry(local))
        case "ingredient":
            ingredient: Ingredient = local
            category = lookups.categories.get(ingredient.category_id or 0)
            family = lookups.families.get(ingredient.family_id or 0)
            conversions = sorted_conversions(
                [
                    (local_ref(lookups.units[c.unit_id], locale), float(c.grams))
                    for c in ingredient.conversions
                    if c.unit_id in lookups.units
                ]
            )
            entry = ingredient_entry(
                ingredient, categories=lookups.categories, families=lookups.families, unit_ids={}
            )
            return ingredient_fields(
                entry,
                local_ref(category, locale) if category is not None else None,
                local_ref(family, locale) if family is not None else None,
                conversions,
            )
        case _:
            return equipment_fields(equipment_entry(local))


# ── Writing accepted values ──────────────────────────────────────────


class CatalogueWriter:
    """Writes accepted field values into an entry here: the full command is
    built from the entry as it is plus the accepted values, and goes through
    the use case of a normal edit without committing."""

    def __init__(
        self,
        *,
        resources: ManageResources,
        ingredients: ManageIngredients,
        equipment: ManageEquipment,
    ) -> None:
        self._resources = resources
        self._ingredients = ingredients
        self._equipment = equipment

    async def write(
        self,
        actor: User,
        kind: str,
        local: Any,
        values: Fields,
        lookups: CatalogueLookups,
        resolve: Resolver,
    ) -> None:
        public_id = str(local.public_id)
        match kind:
            case "category":
                category: IngredientCategory = local
                translations = dict(category.translations)
                for name, value in values.items():
                    translations[name.removeprefix("names.")] = NameText(value)
                await self._resources.update_category(
                    public_id,
                    CategoryCommand(translations=translations, sort_order=category.sort_order),
                    commit=False,
                )
            case "family":
                family: IngredientFamily = local
                translations = dict(family.translations)
                for name, value in values.items():
                    translations[name.removeprefix("names.")] = NameText(value)
                await self._resources.update_family(public_id, translations, commit=False)
            case "unit":
                unit: Unit = local
                unit_cmd = UnitCommand(
                    code=unit.code,
                    kind=unit.kind,
                    to_base=unit.to_base,
                    translations=dict(unit.translations),
                    sort_order=unit.sort_order,
                )
                for name, value in values.items():
                    if name.startswith("names."):
                        unit_cmd.translations[name.removeprefix("names.")] = UnitText(*value)
                    elif name == "kind":
                        unit_cmd = replace(unit_cmd, kind=UnitKind(value))
                    elif name == "to_base":
                        unit_cmd = replace(unit_cmd, to_base=value)
                await self._resources.update_unit(public_id, unit_cmd, commit=False)
            case "tag":
                tag: Tag = local
                tag_cmd = TagCommand(
                    kind=tag.kind, translations=dict(tag.translations), color=tag.color
                )
                for name, value in values.items():
                    if name.startswith("names."):
                        tag_cmd.translations[name.removeprefix("names.")] = NameText(value)
                    elif name == "kind":
                        tag_cmd = replace(tag_cmd, kind=TagKind(value))
                    elif name == "color":
                        tag_cmd = replace(tag_cmd, color=value)
                await self._resources.update_tag(public_id, tag_cmd, commit=False)
            case "ingredient":
                await self._ingredients.update(
                    actor,
                    public_id,
                    self._ingredient_command(local, values, lookups, resolve),
                    commit=False,
                )
            case _:
                item: Equipment = local
                equipment_cmd = EquipmentCommand(
                    kind=item.kind,
                    translations=dict(item.translations),
                    aliases=dict(item.aliases),
                    icon=item.icon,
                    basic=item.basic,
                )
                for name, value in values.items():
                    base, _, rest = name.partition(".")
                    if base == "names":
                        equipment_cmd.translations[rest] = NameText(value)
                    elif base == "aliases":
                        equipment_cmd.aliases[rest] = list(value)
                    elif base == "kind":
                        equipment_cmd = replace(equipment_cmd, kind=EquipmentKind(value))
                    elif base == "icon":
                        equipment_cmd = replace(equipment_cmd, icon=value)
                    elif base == "basic":
                        equipment_cmd = replace(equipment_cmd, basic=bool(value))
                await self._equipment.update(actor, public_id, equipment_cmd, commit=False)

    @staticmethod
    def conversions(
        conversions: tuple[tuple[Ref, float], ...], resolve: Resolver
    ) -> list[ConversionCommand]:
        """The conversions whose unit resolves to a unit here."""
        found: list[ConversionCommand] = []
        for ref, grams in conversions:
            unit_id = resolve(ref)
            if unit_id is not None:
                found.append(ConversionCommand(unit_id=unit_id, grams=grams))
        return found

    def _ingredient_command(
        self,
        ingredient: Ingredient,
        values: Fields,
        lookups: CatalogueLookups,
        resolve: Resolver,
    ) -> IngredientCommand:
        """The ingredient as it is, with the accepted values."""
        category = lookups.categories.get(ingredient.category_id or 0)
        family = lookups.families.get(ingredient.family_id or 0)
        translations = dict(ingredient.translations)
        aliases = {k: list(v) for k, v in ingredient.aliases.items()}
        nutrition = ingredient.nutrition
        extended: dict[str, float | None] = dict(ingredient.extended_nutrition)
        cmd = IngredientCommand(
            original_locale=ingredient.original_locale,
            translations=translations,
            category_id=str(category.public_id) if category is not None else None,
            family_id=str(family.public_id) if family is not None else None,
            aliases=aliases,
            nutrition=nutrition,
            extended_nutrition=extended,
            season_months=list(ingredient.season_months),
            density_g_per_ml=ingredient.density_g_per_ml,
            conversions=[
                ConversionCommand(unit_id=str(lookups.units[c.unit_id].public_id), grams=c.grams)
                for c in ingredient.conversions
                if c.unit_id in lookups.units
            ],
            allergens=list(ingredient.allergens),
            diet_markers=list(ingredient.diet_markers),
            nutrition_source=ingredient.nutrition_source,
            usda_fdc_id=ingredient.usda_fdc_id,
        )
        for name, value in values.items():
            base, _, rest = name.partition(".")
            match base:
                case "names":
                    translations[rest] = IngredientText(name=value[0], plural_name=value[1])
                case "aliases":
                    aliases[rest] = list(value)
                case "category" | "family":
                    target = resolve(value)
                    if target is None:
                        raise ValueError(f"The {base} was not created here.")
                    if base == "category":
                        cmd = replace(cmd, category_id=target)
                    else:
                        cmd = replace(cmd, family_id=target)
                case "nutrition":
                    nutrition = replace(nutrition, **{rest: value})
                    cmd = replace(cmd, nutrition=nutrition)
                case "extended":
                    extended[rest] = value
                case "density_g_per_ml":
                    cmd = replace(cmd, density_g_per_ml=value)
                case "conversions":
                    cmd = replace(cmd, conversions=self.conversions(value, resolve))
                case "allergens":
                    cmd = replace(cmd, allergens=[Allergen(a) for a in value])
                case "diet_markers":
                    cmd = replace(cmd, diet_markers=[DietMarker(m) for m in value])
                case "season_months":
                    cmd = replace(cmd, season_months=list(value))
        return cmd
