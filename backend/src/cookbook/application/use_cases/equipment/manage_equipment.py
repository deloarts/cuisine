"""
The equipment catalogue. Every signed-in user reads it; write:resources
creates, edits, activates, merges and deletes items. Names and aliases share
the per-locale namespace of ingredient and family names, compared without
case, diacritics or extra spaces. An agent that names unknown equipment in a
recipe draft creates a draft item, which a person reviews. Seeded items are
never deleted, and an item a recipe step names can only be merged away.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.exceptions import DuplicateNameError
from src.cookbook.domain.exceptions import EquipmentInUseError
from src.cookbook.domain.exceptions import EquipmentNotFoundError
from src.cookbook.domain.exceptions import InvalidResourceError
from src.cookbook.domain.exceptions import SeededResourceError
from src.cookbook.domain.services.names import is_near
from src.cookbook.domain.services.names import name_key
from src.cookbook.domain.services.translations import LOCALES
from src.cookbook.domain.services.translations import assert_locale
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import EquipmentStatus
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.ports.outbound.repositories.equipment_repository import EquipmentQuery
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

MAX_NAME = 128
MAX_ICON = 64


@dataclass(frozen=True)
class EquipmentCommand:
    kind: EquipmentKind
    translations: dict[str, NameText]
    aliases: dict[str, list[str]] = field(default_factory=dict)
    icon: str | None = None
    basic: bool = False


class ManageEquipment:
    def __init__(
        self,
        *,
        equipment_repo: IEquipmentRepository,
        ingredient_repo: IIngredientRepository,
        recipe_repo: IRecipeRepository,
        uow: IUnitOfWork,
        mirror_repo: IMirrorRepository | None = None,
    ) -> None:
        self._mirrors = mirror_repo
        self._equipment = equipment_repo
        self._ingredients = ingredient_repo
        self._recipes = recipe_repo
        self._uow = uow

    @staticmethod
    def _assert_writer(actor: User) -> None:
        if not actor.has_permission(Permission.WRITE_RESOURCES):
            raise PermissionDeniedError("Changing equipment needs write:resources.")

    async def find(self, query: EquipmentQuery) -> list[Equipment]:
        return await self._equipment.find(query)

    async def get(self, public_id: str) -> Equipment:
        found = await self._equipment.get_by_public_id(public_id)
        if found is None:
            raise EquipmentNotFoundError("No such equipment.")
        return found

    async def _clean(
        self, cmd: EquipmentCommand, own_id: int
    ) -> tuple[dict[str, NameText], dict[str, list[str]]]:
        if not cmd.translations:
            raise InvalidResourceError("The equipment needs a name in at least one language.")
        names: dict[str, NameText] = {}
        for locale, text in cmd.translations.items():
            assert_locale(locale)
            name = text.name.strip()
            if not name or len(name) > MAX_NAME:
                raise InvalidResourceError("An equipment name has 1 to 128 characters.")
            names[locale] = NameText(name)
        aliases: dict[str, list[str]] = {}
        for locale, wanted in cmd.aliases.items():
            assert_locale(locale)
            own = {name_key(names[locale].name)} if locale in names else set()
            cleaned: dict[str, str] = {}
            for alias in wanted:
                key = name_key(alias)
                if key and key not in own:
                    cleaned.setdefault(key, alias.strip())
            if any(len(a) > MAX_NAME for a in cleaned.values()):
                raise InvalidResourceError("An alias has at most 128 characters.")
            if cleaned:
                aliases[locale] = sorted(cleaned.values(), key=str.casefold)
        for locale in sorted(set(names) | set(aliases)):
            wanted_names = [*aliases.get(locale, [])]
            if locale in names:
                wanted_names.insert(0, names[locale].name)
            await self._assert_free(locale, wanted_names, own_id)
        return names, aliases

    async def _assert_free(self, locale: str, names: list[str], own_id: int) -> None:
        index: dict[str, Any] = {}
        for entry in await self._ingredients.catalogue_names(locale):
            if entry.kind == "equipment" and entry.id == own_id:
                continue
            index.setdefault(name_key(entry.name), entry)
        seen: set[str] = set()
        for name in names:
            key = name_key(name)
            taken = index.get(key)
            if taken is not None:
                raise DuplicateNameError(
                    f"{name!r} is already the name or an alias of {taken.main_name!r}.",
                    existing_id=taken.public_id,
                    existing_name=taken.main_name,
                    existing_kind=taken.kind,
                )
            if key in seen:
                raise InvalidResourceError(f"{name!r} is named twice.")
            seen.add(key)

    @staticmethod
    def _icon(icon: str | None) -> str | None:
        cleaned = (icon or "").strip().removeprefix("mdi-")
        if len(cleaned) > MAX_ICON or (cleaned and not cleaned.replace("-", "").isalnum()):
            raise InvalidResourceError("The icon is an @mdi/font name such as 'pot'.")
        return cleaned or None

    async def near_duplicates(self, name: str, locale: str | None = None) -> list[tuple[Any, bool]]:
        """Equipment that probably means the same thing, as (entry, exact),
        for "Did you mean Schneebesen?" before creating one."""
        found: dict[int, tuple[Any, bool]] = {}
        for loc in [locale] if locale else list(LOCALES):
            for entry in await self._ingredients.catalogue_names(loc):
                if entry.kind != "equipment":
                    continue
                exact = name_key(entry.name) == name_key(name)
                if exact or is_near(name, entry.name, loc):
                    previous = found.get(entry.id)
                    if previous is None or (exact and not previous[1]):
                        found[entry.id] = (entry, exact)
        return sorted(found.values(), key=lambda pair: (not pair[1], pair[0].main_name.casefold()))

    async def create(self, actor: User, cmd: EquipmentCommand, *, commit: bool = True) -> Equipment:
        self._assert_writer(actor)
        names, aliases = await self._clean(cmd, 0)
        now = now_utc()
        saved = await self._equipment.save(
            Equipment(
                kind=cmd.kind,
                created=now,
                changed=now,
                translations=names,
                aliases=aliases,
                icon=self._icon(cmd.icon),
                basic=cmd.basic,
            )
        )
        if commit:
            await self._uow.commit()
        return saved

    async def create_draft(
        self, name: str, locale: str, *, kind: EquipmentKind = EquipmentKind.UTENSIL
    ) -> Equipment:
        """A draft item for a name an agent or a recipe import used that the
        catalogue lacks. The caller commits with the recipe it belongs to."""
        assert_locale(locale)
        names, _ = await self._clean(
            EquipmentCommand(kind=kind, translations={locale: NameText(name)}), 0
        )
        now = now_utc()
        return await self._equipment.save(
            Equipment(
                kind=kind,
                created=now,
                changed=now,
                translations=names,
                status=EquipmentStatus.DRAFT,
            )
        )

    async def update(
        self, actor: User, public_id: str, cmd: EquipmentCommand, *, commit: bool = True
    ) -> Equipment:
        self._assert_writer(actor)
        item = await self.get(public_id)
        item.translations, item.aliases = await self._clean(cmd, item.id)
        item.kind = cmd.kind
        item.icon = self._icon(cmd.icon)
        item.basic = cmd.basic
        item.changed = now_utc()
        saved = await self._equipment.save(item)
        if commit:
            await self._uow.commit()
        return saved

    async def activate(self, actor: User, public_id: str) -> Equipment:
        self._assert_writer(actor)
        item = await self.get(public_id)
        item.status = EquipmentStatus.ACTIVE
        item.changed = now_utc()
        saved = await self._equipment.save(item)
        await self._uow.commit()
        return saved

    async def recipe_ids_using(self, item: Equipment) -> list[int]:
        return await self._equipment.recipe_ids_using(item.id)

    async def delete(self, actor: User, public_id: str) -> None:
        self._assert_writer(actor)
        item = await self.get(public_id)
        if item.seed_key:
            raise SeededResourceError("Equipment of the reference catalogue cannot be deleted.")
        if await self._equipment.recipe_ids_using(item.id):
            raise EquipmentInUseError(
                "Recipes name this equipment; merge it into another item instead."
            )
        await self._equipment.delete(item)
        await self._uow.commit()

    async def merge(self, actor: User, public_id: str, into_public_id: str) -> Equipment:
        """Moves every step and kitchen from the source to the target, makes
        the source's names aliases of the target and deletes the source."""
        self._assert_writer(actor)
        source = await self.get(public_id)
        target = await self.get(into_public_id)
        if source.id == target.id:
            raise InvalidResourceError("An item cannot be merged into itself.")
        if source.seed_key:
            raise SeededResourceError("Equipment of the reference catalogue cannot be merged away.")
        await self._equipment.repoint(source.id, target.id)
        if self._mirrors is not None:
            await self._mirrors.repoint_mappings(MappingKind.EQUIPMENT, source.id, target.id)
        aliases = {k: list(v) for k, v in target.aliases.items()}
        for locale in set(source.translations) | set(source.aliases):
            moved = list(source.aliases.get(locale, []))
            if locale in source.translations:
                moved.insert(0, source.translations[locale].name)
            aliases.setdefault(locale, []).extend(moved)
        await self._equipment.delete(source)
        names, cleaned = await self._clean(
            EquipmentCommand(kind=target.kind, translations=target.translations, aliases=aliases),
            target.id,
        )
        target.translations, target.aliases = names, cleaned
        target.changed = now_utc()
        saved = await self._equipment.save(target)
        await self._uow.commit()
        return saved
