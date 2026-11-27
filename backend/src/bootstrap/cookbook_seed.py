"""
First-start seeding of the cookbook's reference data: the units, ingredient
categories, tags, base ingredients with their families and the equipment in
src/bootstrap/data/
(reference_data.py), in both content languages.

One rule for every kind, on every start: a key is inserted once, and never
again. Each inserted key is remembered in `seeded_keys` with the values the
seed wrote (its merge base), so a row an administrator deleted stays
deleted. Existing rows take later seed updates field by field where nobody
edited the field (`seed_merge.py`); edited fields keep the edit and are
listed for an administrator to accept. A row that matches a key but predates the
seed keys (a unit with the key as its code, a category, tag or ingredient
with one of the key's names) is adopted: the key is remembered and nothing
is inserted. Everything happens in one transaction.

An inserted row gets the deterministic public id of its kind and key
(`seed_ids.seeded_public_id`), the same on every instance. An adopted row,
and a row seeded before ids were deterministic, keeps the public id it has:
recipe mentions, revision snapshots and variations name catalogue entries by
public id, so rewriting one would break them. Matching across instances
therefore goes by seed key first, never by public id alone.
"""

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.reference_data import ReferenceData
from src.bootstrap.reference_data import load_reference_data
from src.bootstrap.seed_merge import SeedMerge
from src.bootstrap.seed_merge import seed_fields
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
from src.cookbook.domain.services.seed_ids import seeded_public_id
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import NutritionSource
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrition import NUTRIENTS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.cookbook.ports.outbound.repositories.equipment_repository import EquipmentQuery
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.platform.infrastructure.logging.logger import log
from src.platform.ports.outbound.unit_of_work import ConstraintViolationError
from src.shared_kernel.domain.services.clock import now_utc

UNIT, CATEGORY, TAG, FAMILY, INGREDIENT = "unit", "category", "tag", "family", "ingredient"
EQUIPMENT = "equipment"
# Base ingredients are written in British English first.
INGREDIENT_LOCALE = "en-GB"


def _names(texts: Iterable[str]) -> set[str]:
    return {t.strip().casefold() for t in texts if t and t.strip()}


class _Seeder:
    def __init__(self, db: AsyncSession, data: ReferenceData) -> None:
        self._db = db
        self._data = data
        self._units = SqlAlchemyUnitRepository(db)
        self._categories = SqlAlchemyIngredientCategoryRepository(db)
        self._tags = SqlAlchemyTagRepository(db)
        self._families = SqlAlchemyIngredientFamilyRepository(db)
        self._ingredients = SqlAlchemyIngredientRepository(db)
        self._equipment = SqlAlchemyEquipmentRepository(db)
        self._seeded: set[tuple[str, str]] = set()
        self.added = 0

    async def load_seeded(self) -> None:
        rows = await self._db.execute(select(SeededKeyModel.kind, SeededKeyModel.key))
        self._seeded = {(kind, key) for kind, key in rows.all()}

    def _remember(self, kind: str, key: str, data: Any) -> None:
        """Remembers the key with the seed's values as the merge base, also
        for an adopted row, so nothing it holds changes silently."""
        self._db.add(
            SeededKeyModel(kind=kind, key=key, seeded_at=now_utc(), base=seed_fields(kind, data))
        )
        self._seeded.add((kind, key))

    def _due(self, kind: str, key: str) -> bool:
        return (kind, key) not in self._seeded

    async def units(self) -> dict[str, int]:
        existing = await self._units.list_all()
        by_key = {u.seed_key: u.id for u in existing if u.seed_key}
        by_code = {u.code: u.id for u in existing}
        for order, data in enumerate(self._data.units):
            if not self._due(UNIT, data.key):
                continue
            if data.key in by_key or data.key in by_code:
                self._remember(UNIT, data.key, data)
                continue
            unit = await self._units.save(
                Unit(
                    public_id=seeded_public_id(UNIT, data.key),
                    code=data.key,
                    kind=UnitKind(data.kind),
                    to_base=data.to_base,
                    created=now_utc(),
                    sort_order=order,
                    translations={locale: UnitText(*n) for locale, n in data.names.items()},
                    seed_key=data.key,
                )
            )
            by_key[data.key] = unit.id
            self._remember(UNIT, data.key, data)
            self.added += 1
        return {**by_code, **by_key}

    async def categories(self) -> dict[str, int]:
        existing = await self._categories.list_all()
        by_key = {c.seed_key: c.id for c in existing if c.seed_key}
        resolved: dict[str, int] = dict(by_key)
        for order, data in enumerate(self._data.categories):
            wanted = _names(data.names.values())
            match = next(
                (c for c in existing if _names(t.name for t in c.translations.values()) & wanted),
                None,
            )
            if data.key not in resolved and match is not None:
                resolved[data.key] = match.id
            if not self._due(CATEGORY, data.key):
                continue
            if data.key in by_key or match is not None:
                self._remember(CATEGORY, data.key, data)
                continue
            category = await self._categories.save(
                IngredientCategory(
                    public_id=seeded_public_id(CATEGORY, data.key),
                    created=now_utc(),
                    sort_order=order,
                    translations={locale: NameText(n) for locale, n in data.names.items()},
                    seed_key=data.key,
                )
            )
            resolved[data.key] = category.id
            self._remember(CATEGORY, data.key, data)
            self.added += 1
        return resolved

    async def tags(self) -> None:
        existing = await self._tags.list_all()
        keys = {t.seed_key for t in existing if t.seed_key}
        for data in self._data.tags:
            if not self._due(TAG, data.key):
                continue
            wanted = _names(data.names.values())
            if data.key in keys or any(
                _names(t.name for t in tag.translations.values()) & wanted for tag in existing
            ):
                self._remember(TAG, data.key, data)
                continue
            await self._tags.save(
                Tag(
                    public_id=seeded_public_id(TAG, data.key),
                    kind=TagKind(data.kind),
                    created=now_utc(),
                    color=data.color,
                    translations={locale: NameText(n) for locale, n in data.names.items()},
                    seed_key=data.key,
                )
            )
            self._remember(TAG, data.key, data)
            self.added += 1

    async def equipment(self) -> None:
        existing = await self._equipment.find(EquipmentQuery())
        keys = {e.seed_key for e in existing if e.seed_key}
        for data in self._data.equipment:
            if not self._due(EQUIPMENT, data.key):
                continue
            wanted = _names(data.names.values())
            if data.key in keys or any(
                _names(t.name for t in item.translations.values()) & wanted for item in existing
            ):
                self._remember(EQUIPMENT, data.key, data)
                continue
            now = now_utc()
            await self._equipment.save(
                Equipment(
                    public_id=seeded_public_id(EQUIPMENT, data.key),
                    kind=EquipmentKind(data.kind),
                    created=now,
                    changed=now,
                    translations={locale: NameText(n) for locale, n in data.names.items()},
                    aliases={locale: list(n) for locale, n in data.aliases.items()},
                    icon=data.icon,
                    basic=data.basic,
                    seed_key=data.key,
                )
            )
            self._remember(EQUIPMENT, data.key, data)
            self.added += 1

    async def families(self) -> dict[str, int]:
        existing = await self._families.list_all()
        resolved = {f.seed_key: f.id for f in existing if f.seed_key}
        for data in self._data.families:
            wanted = _names(data.names.values())
            match = next(
                (f for f in existing if _names(t.name for t in f.translations.values()) & wanted),
                None,
            )
            if data.key not in resolved and match is not None:
                resolved[data.key] = match.id
            if not self._due(FAMILY, data.key):
                continue
            if data.key in resolved:
                self._remember(FAMILY, data.key, data)
                continue
            family = await self._families.save(
                IngredientFamily(
                    public_id=seeded_public_id(FAMILY, data.key),
                    created=now_utc(),
                    translations={locale: NameText(n) for locale, n in data.names.items()},
                    seed_key=data.key,
                )
            )
            resolved[data.key] = family.id
            self._remember(FAMILY, data.key, data)
            self.added += 1
        return resolved

    async def ingredients(
        self, units: dict[str, int], categories: dict[str, int], families: dict[str, int]
    ) -> None:
        due = [i for i in self._data.ingredients if self._due(INGREDIENT, i.key)]
        if not due:
            return
        existing = await self._ingredients.find_seeded_or_named()
        allergens = {a.value for a in Allergen}
        markers = {m.value for m in DietMarker}
        now = now_utc()
        for data in due:
            names = _names(n for pair in data.names.values() for n in pair)
            if data.key in existing.keys or names & existing.names:
                self._remember(INGREDIENT, data.key, data)
                continue
            source = (
                NutritionSource(data.nutrition_source)
                if data.nutrition_source in {s.value for s in NutritionSource}
                else NutritionSource.MANUAL
            )
            await self._ingredients.save(
                Ingredient(
                    public_id=seeded_public_id(INGREDIENT, data.key),
                    owner_id=None,
                    original_locale=INGREDIENT_LOCALE,
                    created=now,
                    changed=now,
                    translations={
                        locale: IngredientText(name=n[0], plural_name=n[1])
                        for locale, n in data.names.items()
                    },
                    category_id=categories.get(data.category),
                    family_id=families.get(data.family) if data.family else None,
                    # An alias someone already uses elsewhere stays theirs.
                    aliases={
                        locale: [a for a in names if a.strip().casefold() not in existing.names]
                        for locale, names in data.aliases.items()
                    },
                    nutrition=Nutrition(**{n: data.nutrition.get(n) for n in NUTRIENTS}),
                    extended_nutrition={
                        k: v for k, v in data.extended_nutrition.items() if k in EXTENDED_KEYS
                    },
                    season_months=list(data.season_months),
                    density_g_per_ml=data.density_g_per_ml,
                    conversions=[
                        UnitConversion(units[unit], grams)
                        for unit, grams in data.conversions.items()
                        if unit in units
                    ],
                    allergens=[Allergen(a) for a in data.allergens if a in allergens],
                    diet_markers=[DietMarker(m) for m in data.diet_markers if m in markers],
                    status=IngredientStatus.ACTIVE,
                    nutrition_source=source,
                    usda_fdc_id=data.usda_fdc_id,
                    seed_key=data.key,
                )
            )
            self._remember(INGREDIENT, data.key, data)
            self.added += 1


async def ensure_reference_data(*, ingredients: bool = True, equipment: bool | None = None) -> bool:
    """Adds the reference rows whose keys were never seeded. Returns whether
    it added anything. `ingredients=False` leaves out the base ingredients
    and their families, and unless `equipment` says otherwise the equipment
    too, which the test suite uses to keep its catalogue small."""
    data = load_reference_data()
    async with SessionLocal() as db:
        seeder = _Seeder(db, data)
        await seeder.load_seeded()
        units = await seeder.units()
        categories = await seeder.categories()
        await seeder.tags()
        if ingredients:
            # Families come with the base ingredients they group.
            families = await seeder.families()
            await seeder.ingredients(units, categories, families)
        if ingredients if equipment is None else equipment:
            await seeder.equipment()
        await db.flush()
        updated = await SeedMerge(db, data).merge()
        try:
            await SqlAlchemyUnitOfWork(db).commit()
        except ConstraintViolationError:
            # Another worker seeded at the same moment.
            return False
    if seeder.added:
        log.info("Seeded %s reference rows.", seeder.added)
    if updated:
        log.info("Applied %s reference data updates.", updated)
    return seeder.added > 0 or updated > 0


async def ensure_cookbook_resources() -> bool:
    """The startup seed: every kind of reference data."""
    return await ensure_reference_data()
