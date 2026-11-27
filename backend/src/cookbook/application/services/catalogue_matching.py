"""
Matching catalogue entries of an exchange document (a `.cui` file or a
catalogue file) to this instance's catalogue. Every kind is matched by its
seed key first; then units by code, tags, categories and families by a name
in any language, and ingredients and equipment by a name or alias in any
language. The source's public id is never used for matching, since every
instance gives its rows ids of its own.

The matcher only finds; what happens to an entry without a match (a draft
for the review queue, an active entry, a conflict) is up to the import that
uses it. It loads each kind's list once, so it belongs to one import run.
"""

from collections.abc import Iterable
from collections.abc import Mapping

from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import TagEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import UnitEntryV1
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository


def _named[T: (IngredientCategory, IngredientFamily)](
    rows: list[T], seed_key: str | None, names: Mapping[str, str]
) -> T | None:
    if seed_key:
        for row in rows:
            if row.seed_key == seed_key:
                return row
    wanted = {n.casefold() for n in names.values() if n}
    for row in rows:
        if {t.name.casefold() for t in row.translations.values()} & wanted:
            return row
    return None


class CatalogueMatcher:
    def __init__(
        self,
        *,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
    ) -> None:
        self._unit_repo = unit_repo
        self._tag_repo = tag_repo
        self._category_repo = category_repo
        self._family_repo = family_repo
        self._ingredient_repo = ingredient_repo
        self._equipment_repo = equipment_repo
        self._units: list[Unit] | None = None
        self._tags: list[Tag] | None = None
        self._categories: list[IngredientCategory] | None = None
        self._families: list[IngredientFamily] | None = None
        self._ingredient_keys: dict[str, Ingredient] = {}
        self._equipment_keys: dict[str, Equipment] = {}

    async def prime(
        self, *, ingredient_keys: Iterable[str] = (), equipment_keys: Iterable[str] = ()
    ) -> None:
        """Loads the ingredients and equipment with these seed keys in one
        query each, so matching many entries does not look them up one by
        one."""
        keys = sorted({k for k in ingredient_keys if k} - set(self._ingredient_keys))
        self._ingredient_keys |= await self._ingredient_repo.by_seed_keys(keys)
        keys = sorted({k for k in equipment_keys if k} - set(self._equipment_keys))
        self._equipment_keys |= await self._equipment_repo.by_seed_keys(keys)

    async def unit(self, entry: UnitEntryV1) -> Unit | None:
        if self._units is None:
            self._units = await self._unit_repo.list_all()
        if entry.seed_key:
            for unit in self._units:
                if unit.seed_key == entry.seed_key:
                    return unit
        code = entry.code.casefold()
        return next((u for u in self._units if u.code.casefold() == code), None)

    async def tag(self, entry: TagEntryV1) -> Tag | None:
        if self._tags is None:
            self._tags = await self._tag_repo.list_all()
        if entry.seed_key:
            for tag in self._tags:
                if tag.seed_key == entry.seed_key:
                    return tag
        wanted = [n.casefold() for n in entry.names.values() if n]
        for name in wanted:
            for tag in self._tags:
                if any(t.name.casefold() == name for t in tag.translations.values()):
                    return tag
        return None

    async def category(
        self, seed_key: str | None, names: Mapping[str, str]
    ) -> IngredientCategory | None:
        if self._categories is None:
            self._categories = await self._category_repo.list_all()
        return _named(self._categories, seed_key, names)

    async def family(
        self, seed_key: str | None, names: Mapping[str, str]
    ) -> IngredientFamily | None:
        if self._families is None:
            self._families = await self._family_repo.list_all()
        return _named(self._families, seed_key, names)

    async def ingredient(self, entry: IngredientEntryV1) -> Ingredient | None:
        if entry.seed_key:
            await self.prime(ingredient_keys=[entry.seed_key])
            found = self._ingredient_keys.get(entry.seed_key)
            if found is not None:
                return found
        names = [n for text in entry.names.values() for n in (text.name, text.plural_name) if n]
        names += [a for aliases in entry.aliases.values() for a in aliases]
        return await self._ingredient_repo.find_by_names(names)

    async def equipment(self, entry: EquipmentEntryV1) -> Equipment | None:
        if entry.seed_key:
            await self.prime(equipment_keys=[entry.seed_key])
            found = self._equipment_keys.get(entry.seed_key)
            if found is not None:
                return found
        names = [n for n in entry.names.values() if n]
        names += [a for aliases in entry.aliases.values() for a in aliases]
        return await self._equipment_repo.find_by_names(names)
