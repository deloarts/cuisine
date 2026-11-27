"""
Seed updates: the per-field three-way merge between the values the seed last
wrote into a row (the base, stored next to its key in `seeded_keys`), the
row's current values and the seed's values now.

Per field, on every start: when the seed's value equals the base nothing
happens; when the row still holds the base, the seed's new value is written
and becomes the base; when the row already holds the seed's value, only the
base follows; when the row differs from both, someone edited it and the edit
stays, listed as an overridden seed update that an administrator may accept
(`accept`). Deleted rows stay deleted and rows that left the seed are no
longer updated, since the merge only visits rows that exist and keys the
seed still has. A row seeded before bases were stored gets the seed's
values as its base, so nothing changes silently.

A field is a name such as `names.de-AT`, `aliases.en-GB`, `category`,
`nutrition.kcal`, `extended.iron_mg`, `conversions`, `allergens`,
`diet_markers`, `season_months`, `to_base`, `kind`, `color`, `icon` or
`basic`; its value is plain JSON, so bases compare after a round trip.
"""

from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.reference_data import CategoryData
from src.bootstrap.reference_data import EquipmentData
from src.bootstrap.reference_data import FamilyData
from src.bootstrap.reference_data import IngredientData
from src.bootstrap.reference_data import ReferenceData
from src.bootstrap.reference_data import TagData
from src.bootstrap.reference_data import UnitData
from src.cookbook.adapters.outbound.persistence.models.resource_models import SeededKeyModel
from src.cookbook.adapters.outbound.persistence.repositories.equipment_repository import (
    SqlAlchemyEquipmentRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.ingredient_repository import (
    SqlAlchemyIngredientRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyIngredientCategoryRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyIngredientFamilyRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyTagRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyUnitRepository,
)
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.ingredient import UnitConversion
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.services.names import name_key
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrition import NUTRIENTS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.shared_kernel.domain.services.clock import now_utc

Fields = dict[str, Any]

# Health-relevant fields first in the overridden list.
PRIORITY = ("allergens", "diet_markers")


def _sorted(values: list[str]) -> list[str]:
    return sorted({v.strip() for v in values if v.strip()}, key=str.casefold)


def _num(value: Any) -> float | None:
    return float(value) if value is not None else None


@dataclass
class Context:
    """Key and id lookups across kinds, for fields that name another row."""

    unit_ids: dict[str, int]
    unit_keys: dict[int, str]
    category_ids: dict[str, int]
    category_keys: dict[int, str]
    family_ids: dict[str, int]
    family_keys: dict[int, str]


# ── Fields per kind: from the seed, from a row, and written into a row ──


def unit_seed(d: UnitData) -> Fields:
    return {
        **{f"names.{loc}": list(n) for loc, n in sorted(d.names.items())},
        "to_base": _num(d.to_base),
    }


def unit_current(u: Unit, _ctx: Context) -> Fields:
    return {
        **{
            f"names.{loc}": [t.name, t.plural_name, t.abbreviation]
            for loc, t in sorted(u.translations.items())
        },
        "to_base": _num(u.to_base),
    }


def unit_apply(u: Unit, field: str, value: Any, _ctx: Context) -> None:
    if field.startswith("names."):
        loc = field.removeprefix("names.")
        if value is None:
            u.translations.pop(loc, None)
        else:
            u.translations[loc] = UnitText(*value)
    elif field == "to_base":
        u.to_base = value


def named_seed(d: CategoryData | FamilyData) -> Fields:
    return {f"names.{loc}": n for loc, n in sorted(d.names.items())}


def named_current(row: IngredientCategory | IngredientFamily, _ctx: Context) -> Fields:
    return {f"names.{loc}": t.name for loc, t in sorted(row.translations.items())}


def named_apply(
    row: IngredientCategory | IngredientFamily | Tag, field: str, value: Any, _ctx: Context
) -> None:
    loc = field.removeprefix("names.")
    if value is None:
        row.translations.pop(loc, None)
    else:
        row.translations[loc] = NameText(value)


def tag_seed(d: TagData) -> Fields:
    return {
        **{f"names.{loc}": n for loc, n in sorted(d.names.items())},
        "kind": d.kind,
        "color": d.color,
    }


def tag_current(t: Tag, _ctx: Context) -> Fields:
    return {
        **{f"names.{loc}": x.name for loc, x in sorted(t.translations.items())},
        "kind": t.kind.value,
        "color": t.color,
    }


def tag_apply(t: Tag, field: str, value: Any, ctx: Context) -> None:
    if field == "kind":
        t.kind = TagKind(value)
    elif field == "color":
        t.color = value
    else:
        named_apply(t, field, value, ctx)


def ingredient_seed(d: IngredientData) -> Fields:
    fields: Fields = {f"names.{loc}": list(n) for loc, n in sorted(d.names.items())}
    for loc in sorted(set(d.names) | set(d.aliases)):
        fields[f"aliases.{loc}"] = _sorted(d.aliases.get(loc, []))
    fields["category"] = d.category
    fields["family"] = d.family
    for n in NUTRIENTS:
        fields[f"nutrition.{n}"] = _num(d.nutrition.get(n))
    for k in EXTENDED_KEYS:
        fields[f"extended.{k}"] = _num(d.extended_nutrition.get(k))
    fields["density_g_per_ml"] = _num(d.density_g_per_ml)
    fields["conversions"] = {u: float(g) for u, g in sorted(d.conversions.items())}
    fields["allergens"] = sorted(d.allergens)
    fields["diet_markers"] = sorted(d.diet_markers)
    fields["season_months"] = sorted(d.season_months)
    return fields


def ingredient_current(i: Ingredient, ctx: Context) -> Fields:
    fields: Fields = {
        f"names.{loc}": [t.name, t.plural_name] for loc, t in sorted(i.translations.items())
    }
    for loc in sorted(set(i.translations) | set(i.aliases)):
        fields[f"aliases.{loc}"] = _sorted(i.aliases.get(loc, []))
    fields["category"] = (
        ctx.category_keys.get(i.category_id, f"#{i.category_id}") if i.category_id else None
    )
    fields["family"] = ctx.family_keys.get(i.family_id, f"#{i.family_id}") if i.family_id else None
    for n in NUTRIENTS:
        fields[f"nutrition.{n}"] = _num(getattr(i.nutrition, n))
    for k in EXTENDED_KEYS:
        fields[f"extended.{k}"] = _num(i.extended_nutrition.get(k))
    fields["density_g_per_ml"] = _num(i.density_g_per_ml)
    fields["conversions"] = {
        ctx.unit_keys.get(c.unit_id, f"#{c.unit_id}"): float(c.grams)
        for c in sorted(i.conversions, key=lambda c: ctx.unit_keys.get(c.unit_id, ""))
    }
    fields["allergens"] = sorted(a.value for a in i.allergens)
    fields["diet_markers"] = sorted(m.value for m in i.diet_markers)
    fields["season_months"] = sorted(i.season_months)
    return fields


def ingredient_apply(i: Ingredient, field: str, value: Any, ctx: Context) -> None:
    kind, _, rest = field.partition(".")
    if kind == "names":
        if value is None:
            i.translations.pop(rest, None)
        else:
            i.translations[rest] = IngredientText(name=value[0], plural_name=value[1])
    elif kind == "aliases":
        if value:
            i.aliases[rest] = list(value)
        else:
            i.aliases.pop(rest, None)
    elif kind == "category":
        i.category_id = ctx.category_ids.get(value) if value else None
    elif kind == "family":
        i.family_id = ctx.family_ids.get(value) if value else None
    elif kind == "nutrition":
        i.nutrition = Nutrition(
            **{n: (value if n == rest else getattr(i.nutrition, n)) for n in NUTRIENTS}
        )
    elif kind == "extended":
        extended = dict(i.extended_nutrition)
        if value is None:
            extended.pop(rest, None)
        else:
            extended[rest] = value
        i.extended_nutrition = extended
    elif kind == "density_g_per_ml":
        i.density_g_per_ml = value
    elif kind == "conversions":
        i.conversions = [
            UnitConversion(ctx.unit_ids[u], g)
            for u, g in (value or {}).items()
            if u in ctx.unit_ids
        ]
    elif kind == "allergens":
        i.allergens = [Allergen(a) for a in value]
    elif kind == "diet_markers":
        i.diet_markers = [DietMarker(m) for m in value]
    elif kind == "season_months":
        i.season_months = list(value)
    i.changed = now_utc()


def equipment_seed(d: EquipmentData) -> Fields:
    fields: Fields = {f"names.{loc}": n for loc, n in sorted(d.names.items())}
    for loc in sorted(set(d.names) | set(d.aliases)):
        fields[f"aliases.{loc}"] = _sorted(d.aliases.get(loc, []))
    fields.update({"kind": d.kind, "icon": d.icon, "basic": d.basic})
    return fields


def equipment_current(e: Equipment, _ctx: Context) -> Fields:
    fields: Fields = {f"names.{loc}": t.name for loc, t in sorted(e.translations.items())}
    for loc in sorted(set(e.translations) | set(e.aliases)):
        fields[f"aliases.{loc}"] = _sorted(e.aliases.get(loc, []))
    fields.update({"kind": e.kind.value, "icon": e.icon, "basic": e.basic})
    return fields


def equipment_apply(e: Equipment, field: str, value: Any, _ctx: Context) -> None:
    kind, _, rest = field.partition(".")
    if kind == "names":
        if value is None:
            e.translations.pop(rest, None)
        else:
            e.translations[rest] = NameText(value)
    elif kind == "aliases":
        if value:
            e.aliases[rest] = list(value)
        else:
            e.aliases.pop(rest, None)
    elif kind == "kind":
        e.kind = EquipmentKind(value)
    elif kind == "icon":
        e.icon = value
    elif kind == "basic":
        e.basic = bool(value)
    e.changed = now_utc()


@dataclass(frozen=True)
class Overridden:
    """A seed update that an edit holds back."""

    kind: str
    key: str
    name: str
    field: str
    current: Any
    seed: Any
    base: Any


@dataclass
class _Kind:
    name: str
    seed: Callable[[Any], Fields]
    current: Callable[[Any, Context], Fields]
    apply: Callable[[Any, str, Any, Context], None]
    # Fields whose values are catalogue names sharing one namespace.
    namespaced: bool = False


KINDS: dict[str, _Kind] = {
    "unit": _Kind("unit", unit_seed, unit_current, unit_apply),
    "category": _Kind("category", named_seed, named_current, named_apply),
    "tag": _Kind("tag", tag_seed, tag_current, tag_apply),
    "family": _Kind("family", named_seed, named_current, named_apply, namespaced=True),
    "ingredient": _Kind(
        "ingredient", ingredient_seed, ingredient_current, ingredient_apply, namespaced=True
    ),
    "equipment": _Kind(
        "equipment", equipment_seed, equipment_current, equipment_apply, namespaced=True
    ),
}


def seed_fields(kind: str, data: Any) -> Fields:
    return KINDS[kind].seed(data)


def _display(row: Any) -> str:
    translations = getattr(row, "translations", {})
    for loc in ("en-GB", "de-AT", *sorted(translations)):
        text = translations.get(loc)
        if text is not None:
            return str(getattr(text, "name", ""))
    return ""


class SeedMerge:
    """Loads the seeded rows of every kind and merges or accepts their
    fields, inside the caller's session; the caller commits."""

    def __init__(self, db: AsyncSession, data: ReferenceData) -> None:
        self._db = db
        self._data = data
        self._units = SqlAlchemyUnitRepository(db)
        self._categories = SqlAlchemyIngredientCategoryRepository(db)
        self._tags = SqlAlchemyTagRepository(db)
        self._families = SqlAlchemyIngredientFamilyRepository(db)
        self._ingredients = SqlAlchemyIngredientRepository(db)
        self._equipment = SqlAlchemyEquipmentRepository(db)

    def _data_of(self, kind: str) -> dict[str, Any]:
        sources: dict[str, list[Any]] = {
            "unit": list(self._data.units),
            "category": list(self._data.categories),
            "tag": list(self._data.tags),
            "family": list(self._data.families),
            "ingredient": list(self._data.ingredients),
            "equipment": list(self._data.equipment),
        }
        return {d.key: d for d in sources[kind]}

    async def _context(self) -> Context:
        units = await self._units.list_all()
        categories = await self._categories.list_all()
        families = await self._families.list_all()
        return Context(
            unit_ids={(u.seed_key or u.code): u.id for u in units},
            unit_keys={u.id: (u.seed_key or u.code) for u in units},
            category_ids={c.seed_key: c.id for c in categories if c.seed_key},
            category_keys={c.id: c.seed_key for c in categories if c.seed_key},
            family_ids={f.seed_key: f.id for f in families if f.seed_key},
            family_keys={f.id: f.seed_key for f in families if f.seed_key},
        )

    async def _rows(self, kind: str, keys: list[str]) -> dict[str, Any]:
        if kind == "ingredient":
            return dict(await self._ingredients.by_seed_keys(keys))
        if kind == "equipment":
            return dict(await self._equipment.by_seed_keys(keys))
        listings: dict[str, Callable[[], Awaitable[Sequence[Any]]]] = {
            "unit": self._units.list_all,
            "category": self._categories.list_all,
            "tag": self._tags.list_all,
            "family": self._families.list_all,
        }
        rows = await listings[kind]()
        return {r.seed_key: r for r in rows if r.seed_key in keys}

    async def _save(self, kind: str, row: Any) -> None:
        repo: Any = {
            "unit": self._units,
            "category": self._categories,
            "tag": self._tags,
            "family": self._families,
            "ingredient": self._ingredients,
            "equipment": self._equipment,
        }[kind]
        await repo.save(row)

    async def _bases(self, kind: str) -> dict[str, SeededKeyModel]:
        rows = await self._db.scalars(select(SeededKeyModel).where(SeededKeyModel.kind == kind))
        return {r.key: r for r in rows.all()}

    async def _name_free(self, row: Any, kind: str, field: str, value: Any) -> bool:
        """Whether a seed name or alias would stay unique in its locale."""
        if not KINDS[kind].namespaced or not field.startswith(("names.", "aliases.")):
            return True
        locale = field.partition(".")[2]
        names = value if field.startswith("aliases.") else [value]
        if kind == "ingredient" and value is not None and field.startswith("names."):
            names = [value[0]]
        wanted = {name_key(str(n)) for n in names or [] if n}
        for entry in await self._ingredients.catalogue_names(locale):
            if entry.kind == kind and entry.id == row.id:
                continue
            if name_key(entry.name) in wanted:
                return False
        return True

    async def merge(self) -> int:
        """Applies the seed's updates field by field; returns how many
        fields changed."""
        ctx = await self._context()
        changed = 0
        for kind, spec in KINDS.items():
            data = self._data_of(kind)
            bases = await self._bases(kind)
            rows = await self._rows(kind, sorted(set(data) & set(bases)))
            for key, entry in bases.items():
                if key not in data:
                    continue
                seed = spec.seed(data[key])
                if entry.base is None:
                    entry.base = seed
                    continue
                row = rows.get(key)
                if row is None:
                    continue
                base = dict(entry.base)
                current = spec.current(row, ctx)
                dirty = False
                for field in sorted(set(seed) | set(base)):
                    s, b, c = seed.get(field), base.get(field), current.get(field)
                    if s == b:
                        continue
                    if c == s:
                        base[field] = s
                    elif c == b and await self._name_free(row, kind, field, s):
                        spec.apply(row, field, s, ctx)
                        base[field] = s
                        dirty = True
                        changed += 1
                if dirty:
                    await self._save(kind, row)
                if base != entry.base:
                    entry.base = base
        await self._db.flush()
        return changed

    async def overridden(self) -> list[Overridden]:
        ctx = await self._context()
        found: list[Overridden] = []
        for kind, spec in KINDS.items():
            data = self._data_of(kind)
            bases = await self._bases(kind)
            rows = await self._rows(kind, sorted(set(data) & set(bases)))
            for key, row in rows.items():
                base = bases[key].base
                if base is None:
                    continue
                seed = spec.seed(data[key])
                current = spec.current(row, ctx)
                for field in sorted(set(seed) | set(base)):
                    s, b, c = seed.get(field), base.get(field), current.get(field)
                    if s != b and c not in (s, b):
                        found.append(Overridden(kind, key, _display(row), field, c, s, b))
        return sorted(
            found,
            key=lambda o: (o.field not in PRIORITY, o.kind, o.name.casefold(), o.field),
        )

    async def accept(self, kind: str, key: str, field: str) -> bool:
        """Writes the seed's value of one overridden field; False when the
        field holds no overridden update."""
        if kind not in KINDS:
            return False
        update = next(
            (o for o in await self.overridden() if (o.kind, o.key, o.field) == (kind, key, field)),
            None,
        )
        if update is None:
            return False
        ctx = await self._context()
        row = (await self._rows(kind, [key]))[key]
        KINDS[kind].apply(row, field, update.seed, ctx)
        await self._save(kind, row)
        entry = (await self._bases(kind))[key]
        entry.base = {**(entry.base or {}), field: update.seed}
        await self._db.flush()
        return True
