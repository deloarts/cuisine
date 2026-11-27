"""
Units, tags and ingredient categories: everyone reads them, holders of
write:resources change them. A unit that a recipe or an ingredient
conversion uses cannot be deleted; a deleted tag leaves the recipes that
carried it, and a deleted category leaves its ingredients uncategorised.
"""

from dataclasses import dataclass
from dataclasses import field

from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.exceptions import DuplicateNameError
from src.cookbook.domain.exceptions import IngredientCategoryNotFoundError
from src.cookbook.domain.exceptions import IngredientFamilyNotFoundError
from src.cookbook.domain.exceptions import InvalidResourceError
from src.cookbook.domain.exceptions import ResourceInUseError
from src.cookbook.domain.exceptions import SeededResourceError
from src.cookbook.domain.exceptions import TagNotFoundError
from src.cookbook.domain.exceptions import UnitNotFoundError
from src.cookbook.domain.services.names import name_key
from src.cookbook.domain.services.translations import assert_locale
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


def _names(translations: dict[str, NameText], what: str) -> dict[str, NameText]:
    if not translations:
        raise InvalidResourceError(f"The {what} needs a name in at least one language.")
    cleaned: dict[str, NameText] = {}
    for locale, text in translations.items():
        assert_locale(locale)
        if not text.name.strip():
            raise InvalidResourceError(f"The {what} name must not be empty.")
        cleaned[locale] = NameText(name=text.name.strip())
    return cleaned


@dataclass(frozen=True)
class UnitCommand:
    code: str
    kind: UnitKind
    to_base: float | None
    translations: dict[str, UnitText] = field(default_factory=dict)
    sort_order: int = 0


@dataclass(frozen=True)
class TagCommand:
    kind: TagKind
    translations: dict[str, NameText] = field(default_factory=dict)
    color: str | None = None


@dataclass(frozen=True)
class CategoryCommand:
    translations: dict[str, NameText] = field(default_factory=dict)
    sort_order: int = 0


class ManageResources:
    def __init__(
        self,
        *,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        ingredient_repo: IIngredientRepository,
        uow: IUnitOfWork,
        mirror_repo: IMirrorRepository | None = None,
    ) -> None:
        self._mirrors = mirror_repo
        self._families = family_repo
        self._ingredients = ingredient_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._categories = category_repo
        self._uow = uow

    # ── Units ─────────────────────────────────────────────────────────

    async def units(self) -> list[Unit]:
        return await self._units.list_all()

    async def _unit(self, public_id: str) -> Unit:
        unit = await self._units.get_by_public_id(public_id)
        if unit is None:
            raise UnitNotFoundError("No such unit.")
        return unit

    async def _check_unit(self, cmd: UnitCommand, exclude_id: int | None) -> None:
        code = cmd.code.strip()
        if not code or len(code) > 32:
            raise InvalidResourceError("The unit code must have 1 to 32 characters.")
        for unit in await self._units.list_all():
            if unit.id == exclude_id:
                continue
            if name_key(unit.code) == name_key(code):
                raise DuplicateNameError(
                    "A unit with this code already exists.",
                    existing_id=str(unit.public_id),
                    existing_name=unit.code,
                    existing_kind="unit",
                )
            for locale, text in cmd.translations.items():
                other = unit.translations.get(locale)
                if other is not None and name_key(other.name) == name_key(text.name):
                    raise DuplicateNameError(
                        f"A unit is already called {other.name!r}.",
                        existing_id=str(unit.public_id),
                        existing_name=other.name,
                        existing_kind="unit",
                    )
        if cmd.kind in (UnitKind.MASS, UnitKind.VOLUME) and not (cmd.to_base and cmd.to_base > 0):
            raise InvalidResourceError("A mass or volume unit needs a positive factor.")
        if not cmd.translations:
            raise InvalidResourceError("The unit needs a name in at least one language.")
        for locale, text in cmd.translations.items():
            assert_locale(locale)
            if not text.name.strip():
                raise InvalidResourceError("The unit name must not be empty.")

    async def create_unit(self, cmd: UnitCommand, *, commit: bool = True) -> Unit:
        await self._check_unit(cmd, None)
        unit = await self._units.save(
            Unit(
                code=cmd.code.strip(),
                kind=cmd.kind,
                to_base=cmd.to_base if cmd.kind in (UnitKind.MASS, UnitKind.VOLUME) else None,
                created=now_utc(),
                translations=dict(cmd.translations),
                sort_order=cmd.sort_order,
            )
        )
        if commit:
            await self._uow.commit()
        return unit

    async def update_unit(self, public_id: str, cmd: UnitCommand, *, commit: bool = True) -> Unit:
        unit = await self._unit(public_id)
        await self._check_unit(cmd, unit.id)
        unit.code = cmd.code.strip()
        unit.kind = cmd.kind
        unit.to_base = cmd.to_base if cmd.kind in (UnitKind.MASS, UnitKind.VOLUME) else None
        unit.translations = dict(cmd.translations)
        unit.sort_order = cmd.sort_order
        saved = await self._units.save(unit)
        if commit:
            await self._uow.commit()
        return saved

    async def unit_impact(self, public_id: str) -> tuple[bool, bool]:
        """Whether the unit is seeded and whether anything uses it."""
        unit = await self._unit(public_id)
        return unit.seed_key is not None, await self._units.in_use(unit.id)

    async def delete_unit(self, public_id: str) -> None:
        unit = await self._unit(public_id)
        if unit.seed_key:
            raise SeededResourceError("Seeded units cannot be deleted.")
        if await self._units.in_use(unit.id):
            raise ResourceInUseError("The unit is in use; merge it into another unit instead.")
        await self._units.delete(unit)
        await self._uow.commit()

    async def merge_unit(self, public_id: str, into_public_id: str) -> Unit:
        unit = await self._unit(public_id)
        target = await self._unit(into_public_id)
        if unit.seed_key:
            raise SeededResourceError("Seeded units cannot be merged away.")
        if unit.id == target.id:
            raise InvalidResourceError("A unit cannot be merged into itself.")
        await self._units.merge_into(unit.id, target.id)
        if self._mirrors is not None:
            await self._mirrors.repoint_mappings(MappingKind.UNIT, unit.id, target.id)
        await self._units.delete(unit)
        await self._uow.commit()
        return target

    # ── Tags ──────────────────────────────────────────────────────────

    async def tags(self) -> list[Tag]:
        return await self._tags.list_all()

    async def _tag(self, public_id: str) -> Tag:
        tag = await self._tags.get_by_public_id(public_id)
        if tag is None:
            raise TagNotFoundError("No such tag.")
        return tag

    @staticmethod
    def _color(color: str | None) -> str | None:
        if color is None or not color.strip():
            return None
        value = color.strip()
        if not (len(value) in (4, 7) and value.startswith("#")):
            raise InvalidResourceError("The colour must be a hex value such as #d97706.")
        return value

    async def _tag_names_free(self, translations: dict[str, NameText], own_id: int) -> None:
        for tag in await self._tags.list_all():
            if tag.id == own_id:
                continue
            for locale, text in translations.items():
                other = tag.translations.get(locale)
                if other is not None and name_key(other.name) == name_key(text.name):
                    raise DuplicateNameError(
                        f"A tag is already called {other.name!r}.",
                        existing_id=str(tag.public_id),
                        existing_name=other.name,
                        existing_kind="tag",
                    )

    async def create_tag(self, cmd: TagCommand, *, commit: bool = True) -> Tag:
        names = _names(cmd.translations, "tag")
        await self._tag_names_free(names, 0)
        tag = await self._tags.save(
            Tag(
                kind=cmd.kind,
                created=now_utc(),
                translations=names,
                color=self._color(cmd.color),
            )
        )
        if commit:
            await self._uow.commit()
        return tag

    async def update_tag(self, public_id: str, cmd: TagCommand, *, commit: bool = True) -> Tag:
        tag = await self._tag(public_id)
        tag.kind = cmd.kind
        tag.translations = _names(cmd.translations, "tag")
        await self._tag_names_free(tag.translations, tag.id)
        tag.color = self._color(cmd.color)
        saved = await self._tags.save(tag)
        if commit:
            await self._uow.commit()
        return saved

    async def delete_tag(self, public_id: str) -> None:
        await self._tags.delete(await self._tag(public_id))
        await self._uow.commit()

    # ── Ingredient families ───────────────────────────────────────────

    async def families(self) -> list[IngredientFamily]:
        return await self._families.list_all()

    async def _family(self, public_id: str) -> IngredientFamily:
        family = await self._families.get_by_public_id(public_id)
        if family is None:
            raise IngredientFamilyNotFoundError("No such ingredient family.")
        return family

    async def _family_names_free(self, translations: dict[str, NameText], own_id: int) -> None:
        """Family names share the namespace of ingredient names and aliases."""
        for locale, text in translations.items():
            for entry in await self._ingredients.catalogue_names(locale):
                if entry.kind == "family" and entry.id == own_id:
                    continue
                # A family may share a name with its own members.
                if entry.kind == "ingredient" and own_id and entry.family_id == own_id:
                    continue
                if name_key(entry.name) == name_key(text.name):
                    raise DuplicateNameError(
                        f"{text.name!r} is already the name or an alias of {entry.main_name!r}.",
                        existing_id=entry.public_id,
                        existing_name=entry.main_name,
                        existing_kind=entry.kind,
                    )

    async def create_family(
        self, translations: dict[str, NameText], *, commit: bool = True
    ) -> IngredientFamily:
        names = _names(translations, "family")
        await self._family_names_free(names, 0)
        family = await self._families.save(IngredientFamily(created=now_utc(), translations=names))
        if commit:
            await self._uow.commit()
        return family

    async def update_family(
        self, public_id: str, translations: dict[str, NameText], *, commit: bool = True
    ) -> IngredientFamily:
        family = await self._family(public_id)
        family.translations = _names(translations, "family")
        await self._family_names_free(family.translations, family.id)
        saved = await self._families.save(family)
        if commit:
            await self._uow.commit()
        return saved

    async def delete_family(self, public_id: str) -> None:
        """Its ingredients stay, without a family; restrictions on it go."""
        await self._families.delete(await self._family(public_id))
        await self._uow.commit()

    # ── Ingredient categories ─────────────────────────────────────────

    async def categories(self) -> list[IngredientCategory]:
        return await self._categories.list_all()

    async def _category(self, public_id: str) -> IngredientCategory:
        category = await self._categories.get_by_public_id(public_id)
        if category is None:
            raise IngredientCategoryNotFoundError("No such ingredient category.")
        return category

    async def create_category(
        self, cmd: CategoryCommand, *, commit: bool = True
    ) -> IngredientCategory:
        category = await self._categories.save(
            IngredientCategory(
                created=now_utc(),
                translations=_names(cmd.translations, "category"),
                sort_order=cmd.sort_order,
            )
        )
        if commit:
            await self._uow.commit()
        return category

    async def update_category(
        self, public_id: str, cmd: CategoryCommand, *, commit: bool = True
    ) -> IngredientCategory:
        category = await self._category(public_id)
        category.translations = _names(cmd.translations, "category")
        category.sort_order = cmd.sort_order
        saved = await self._categories.save(category)
        if commit:
            await self._uow.commit()
        return saved

    async def delete_category(self, public_id: str, replacement_id: str | None) -> None:
        """Ingredients move to the replacement (or to none); shopping items
        of the category fall into "Other"."""
        category = await self._category(public_id)
        replacement = await self._category(replacement_id) if replacement_id else None
        if replacement is not None and replacement.id == category.id:
            raise InvalidResourceError("A category cannot replace itself.")
        other = next(
            (
                c
                for c in await self._categories.list_all()
                if c.seed_key == "other" and c.id != category.id
            ),
            None,
        )
        await self._categories.move_contents(
            category.id,
            replacement.id if replacement else None,
            other.id if other else None,
        )
        await self._categories.delete(category)
        await self._uow.commit()
