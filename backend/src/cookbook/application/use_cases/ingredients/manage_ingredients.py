"""
The ingredient catalogue. Everyone reads it; write:ingredients creates
ingredients and edits the actor's own, manage:ingredients edits anybody's.
An agent's ingredients start as drafts, which are usable in recipes and
wait for a person to activate them. An ingredient a recipe uses cannot be
deleted.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from typing import Any
from typing import Literal

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.ingredient import UnitConversion
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.exceptions import DuplicateNameError
from src.cookbook.domain.exceptions import IngredientCategoryNotFoundError
from src.cookbook.domain.exceptions import IngredientFamilyNotFoundError
from src.cookbook.domain.exceptions import IngredientInUseError
from src.cookbook.domain.exceptions import IngredientMergeError
from src.cookbook.domain.exceptions import IngredientNotFoundError
from src.cookbook.domain.exceptions import InvalidIngredientError
from src.cookbook.domain.exceptions import SeededResourceError
from src.cookbook.domain.exceptions import UnitNotFoundError
from src.cookbook.domain.services.names import is_near
from src.cookbook.domain.services.names import name_key
from src.cookbook.domain.services.names import search_rank
from src.cookbook.domain.services.recipe_rules import assert_can_edit_ingredient
from src.cookbook.domain.services.seasons import clean_months
from src.cookbook.domain.services.translations import LOCALES
from src.cookbook.domain.services.translations import assert_locale
from src.cookbook.domain.services.translations import assert_translations
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import NutritionSource
from src.cookbook.domain.value_objects.nutrients import clean_extended
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IngredientQuery
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

IngredientSort = Literal["name", "usage"]


@dataclass(frozen=True)
class ConversionCommand:
    unit_id: str
    grams: float


@dataclass(frozen=True)
class IngredientCommand:
    original_locale: str
    translations: dict[str, IngredientText]
    category_id: str | None = None
    family_id: str | None = None
    # Other names per locale; each must be free across main names and
    # aliases in its locale.
    aliases: dict[str, list[str]] = field(default_factory=dict)
    nutrition: Nutrition = field(default_factory=Nutrition)
    # Extended nutrients per 100 g by catalogue key; None or absent is unknown.
    extended_nutrition: dict[str, float | None] = field(default_factory=dict)
    # Months 1 to 12 when the ingredient is in season; empty is not seasonal.
    season_months: list[int] = field(default_factory=list)
    density_g_per_ml: float | None = None
    conversions: list[ConversionCommand] = field(default_factory=list)
    allergens: list[Allergen] = field(default_factory=list)
    diet_markers: list[DietMarker] = field(default_factory=list)
    nutrition_source: NutritionSource = NutritionSource.MANUAL
    usda_fdc_id: int | None = None


def _names_of(ingredient: Ingredient) -> list[str]:
    return [
        *(n for t in ingredient.translations.values() for n in (t.name, t.plural_name)),
        *(a for names in ingredient.aliases.values() for a in names),
    ]


class ManageIngredients:
    def __init__(
        self,
        *,
        ingredient_repo: IIngredientRepository,
        unit_repo: IUnitRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        uow: IUnitOfWork,
        mirror_repo: IMirrorRepository | None = None,
    ) -> None:
        self._mirrors = mirror_repo
        self._families = family_repo
        self._ingredients = ingredient_repo
        self._units = unit_repo
        self._categories = category_repo
        self._uow = uow

    async def find(
        self,
        query: IngredientQuery,
        *,
        limit: int,
        offset: int,
        sort: IngredientSort | None = None,
        descending: bool = False,
        usage: Mapping[int, int] | None = None,
        min_usage: int | None = None,
        max_usage: int | None = None,
    ) -> tuple[list[Ingredient], int]:
        """One page of the matches. Without `sort`, a search ranks the best
        matches first and otherwise the order is alphabetical; `name` is
        always alphabetical and `usage` orders by the counts in `usage`
        (ties alphabetical), which the usage bounds filter on as well."""
        found = await self._ingredients.find(query)
        counts = usage or {}
        if min_usage is not None:
            found = [i for i in found if counts.get(i.id, 0) >= min_usage]
        if max_usage is not None:
            found = [i for i in found if counts.get(i.id, 0) <= max_usage]
        if sort == "usage":
            # The repository's order is alphabetical and the sort is stable,
            # so equal counts stay alphabetical in both directions.
            sign = -1 if descending else 1
            found.sort(key=lambda i: sign * counts.get(i.id, 0))
        elif sort == "name":
            if descending:
                found.reverse()
        elif query.search and query.search.strip():
            # Best matches first; the sort is stable, so equally good matches
            # keep the repository's alphabetical order.
            search = query.search
            found.sort(key=lambda i: search_rank(_names_of(i), search))
        return found[offset : offset + limit], len(found)

    async def get(self, public_id: str) -> Ingredient:
        ingredient = await self._ingredients.get_by_public_id(public_id)
        if ingredient is None:
            raise IngredientNotFoundError("No such ingredient.")
        return ingredient

    async def recipe_count(self, ingredient: Ingredient) -> int:
        return await self._ingredients.recipe_count(ingredient.id)

    async def _apply(self, ingredient: Ingredient, cmd: IngredientCommand) -> None:
        translations = {
            locale: IngredientText(
                name=text.name.strip(), plural_name=(text.plural_name or text.name).strip()
            )
            for locale, text in cmd.translations.items()
        }
        assert_translations(translations, cmd.original_locale, "ingredient")
        if any(not t.name for t in translations.values()):
            raise InvalidIngredientError("Every translation of the ingredient needs a name.")
        for f in fields(cmd.nutrition):
            value = getattr(cmd.nutrition, f.name)
            if value is not None and value < 0:
                raise InvalidIngredientError("Nutrition values must not be negative.")
        if cmd.density_g_per_ml is not None and cmd.density_g_per_ml <= 0:
            raise InvalidIngredientError("The density must be positive.")
        try:
            extended = clean_extended(cmd.extended_nutrition)
            season = clean_months(cmd.season_months)
        except ValueError as exc:
            raise InvalidIngredientError(str(exc)) from exc
        category_id: int | None = None
        if cmd.category_id:
            category = await self._categories.get_by_public_id(cmd.category_id)
            if category is None:
                raise IngredientCategoryNotFoundError("No such ingredient category.")
            category_id = category.id
        family_id: int | None = None
        if cmd.family_id:
            family = await self._families.get_by_public_id(cmd.family_id)
            if family is None:
                raise IngredientFamilyNotFoundError("No such ingredient family.")
            family_id = family.id
        else:
            family_id = await self._family_named(translations)
        ingredient.family_id = family_id
        aliases = await self._aliases(ingredient, translations, cmd.aliases)
        conversions: list[UnitConversion] = []
        for c in cmd.conversions:
            unit = await self._units.get_by_public_id(c.unit_id)
            if unit is None:
                raise UnitNotFoundError("A conversion names an unknown unit.")
            if c.grams <= 0:
                raise InvalidIngredientError("A conversion needs a positive weight.")
            conversions.append(UnitConversion(unit.id, c.grams))
        ingredient.original_locale = cmd.original_locale
        ingredient.translations = translations
        ingredient.category_id = category_id
        ingredient.family_id = family_id
        ingredient.aliases = aliases
        ingredient.nutrition = cmd.nutrition
        ingredient.extended_nutrition = extended
        ingredient.season_months = season
        ingredient.density_g_per_ml = cmd.density_g_per_ml
        ingredient.conversions = conversions
        ingredient.allergens = sorted(set(cmd.allergens), key=lambda a: a.value)
        ingredient.diet_markers = sorted(set(cmd.diet_markers), key=lambda m: m.value)
        ingredient.nutrition_source = cmd.nutrition_source
        ingredient.usda_fdc_id = cmd.usda_fdc_id
        ingredient.changed = now_utc()

    async def _aliases(
        self,
        ingredient: Ingredient,
        translations: dict[str, IngredientText],
        wanted: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        """Cleaned aliases, after checking that the main names and aliases
        are free in the shared namespace of their locale: every ingredient
        and family name and alias, compared without case, diacritics or
        extra spaces. A taken name answers 409 naming the existing entry."""
        aliases: dict[str, list[str]] = {}
        for locale, names in wanted.items():
            assert_locale(locale)
            main = translations.get(locale)
            own = {name_key(main.name)} if main else set()
            cleaned: dict[str, str] = {}
            for name in names:
                key = name_key(name)
                if key and key not in own:
                    cleaned.setdefault(key, name.strip())
            if any(len(n) > 128 for n in cleaned.values()):
                raise InvalidIngredientError("An alias has at most 128 characters.")
            if cleaned:
                aliases[locale] = sorted(cleaned.values(), key=str.casefold)
        for locale in sorted(set(translations) | set(aliases)):
            wanted_names = [*aliases.get(locale, [])]
            if locale in translations:
                wanted_names.insert(0, translations[locale].name)
            await self._assert_free(locale, wanted_names, ingredient)
        return aliases

    async def _family_named(self, translations: dict[str, IngredientText]) -> int | None:
        """The family whose name the ingredient takes in one of its
        languages, such as "Essig" or "Öl". An ingredient given no family
        joins that one, since a name is free only within its own family."""
        for locale, text in sorted(translations.items()):
            key = name_key(text.name)
            for entry in await self._ingredients.catalogue_names(locale):
                if entry.kind == "family" and name_key(entry.name) == key:
                    return int(entry.id)
        return None

    async def _assert_free(self, locale: str, names: list[str], ingredient: Ingredient) -> None:
        index: dict[str, Any] = {}
        for entry in await self._ingredients.catalogue_names(locale):
            if entry.kind == "ingredient" and entry.id == ingredient.id:
                continue
            # An ingredient may share a name with its own family.
            if entry.kind == "family" and entry.id == ingredient.family_id:
                continue
            index.setdefault(name_key(entry.name), entry)
        for name in names:
            taken = index.get(name_key(name))
            if taken is not None and taken.kind == "family":
                raise DuplicateNameError(
                    f"{name!r} is the name of the ingredient family {taken.main_name!r}; "
                    "only an ingredient of that family may carry it.",
                    existing_id=taken.public_id,
                    existing_name=taken.main_name,
                    existing_kind="family",
                )
            if taken is not None:
                raise DuplicateNameError(
                    f"{name!r} is already the name or an alias of {taken.main_name!r}.",
                    existing_id=taken.public_id,
                    existing_name=taken.main_name,
                    existing_kind=taken.kind,
                )

    async def near_duplicates(self, name: str, locale: str | None = None) -> list[tuple[Any, bool]]:
        """Catalogue ingredients that probably mean the same food, as
        (entry, exact), for "Did you mean Erdapfel?" before creating one."""
        found: dict[int, tuple[Any, bool]] = {}
        for loc in [locale] if locale else list(LOCALES):
            for entry in await self._ingredients.catalogue_names(loc):
                if entry.kind != "ingredient":
                    continue
                exact = name_key(entry.name) == name_key(name)
                if exact or is_near(name, entry.name, loc):
                    previous = found.get(entry.id)
                    if previous is None or (exact and not previous[1]):
                        found[entry.id] = (entry, exact)
        return sorted(found.values(), key=lambda pair: (not pair[1], pair[0].main_name.casefold()))

    async def create(
        self,
        actor: User,
        cmd: IngredientCommand,
        *,
        status: IngredientStatus = IngredientStatus.ACTIVE,
        commit: bool = True,
    ) -> Ingredient:
        if not actor.has_permission(Permission.WRITE_INGREDIENTS):
            raise PermissionDeniedError("Creating ingredients needs write:ingredients.")
        now = now_utc()
        ingredient = Ingredient(
            owner_id=actor.id or None,
            original_locale=cmd.original_locale,
            created=now,
            changed=now,
            status=status,
        )
        await self._apply(ingredient, cmd)
        saved = await self._ingredients.save(ingredient)
        if commit:
            await self._uow.commit()
        return saved

    async def update(
        self, actor: User, public_id: str, cmd: IngredientCommand, *, commit: bool = True
    ) -> Ingredient:
        ingredient = await self.get(public_id)
        assert_can_edit_ingredient(actor, ingredient)
        await self._apply(ingredient, cmd)
        saved = await self._ingredients.save(ingredient)
        if commit:
            await self._uow.commit()
        return saved

    async def add_translation(
        self,
        actor: User,
        public_id: str,
        locale: str,
        text: IngredientText,
        aliases: list[str] | None = None,
    ) -> Ingredient:
        """Adds or replaces the ingredient's names in one language and leaves
        everything else as it is. Given aliases replace that language's
        aliases; None keeps them. The names must be free as on any edit."""
        ingredient = await self.get(public_id)
        assert_can_edit_ingredient(actor, ingredient)
        assert_locale(locale)
        name = text.name.strip()
        if not name:
            raise InvalidIngredientError("Every translation of the ingredient needs a name.")
        translations = {
            **ingredient.translations,
            locale: IngredientText(name=name, plural_name=(text.plural_name or name).strip()),
        }
        wanted = {k: list(v) for k, v in ingredient.aliases.items()}
        if aliases is not None:
            wanted[locale] = list(aliases)
        ingredient.aliases = await self._aliases(ingredient, translations, wanted)
        ingredient.translations = translations
        ingredient.changed = now_utc()
        saved = await self._ingredients.save(ingredient)
        await self._uow.commit()
        return saved

    async def set_status(self, actor: User, public_id: str, status: IngredientStatus) -> Ingredient:
        ingredient = await self.get(public_id)
        assert_can_edit_ingredient(actor, ingredient)
        ingredient.status = status
        ingredient.changed = now_utc()
        saved = await self._ingredients.save(ingredient)
        await self._uow.commit()
        return saved

    async def recipes_using(self, ingredient: Ingredient) -> list[int]:
        return await self._ingredients.recipe_ids_using(ingredient.id)

    async def delete(self, actor: User, public_id: str) -> None:
        """Seeded ingredients stay; an ingredient a recipe uses is blocked
        (merge it instead). When food restrictions name the ingredient it is
        archived instead of deleted, so those users keep their warnings; the
        answer is the same either way and reveals nothing about them."""
        ingredient = await self.get(public_id)
        assert_can_edit_ingredient(actor, ingredient)
        if ingredient.seed_key:
            raise SeededResourceError("Base ingredients cannot be deleted.")
        if await self._ingredients.recipe_count(ingredient.id):
            raise IngredientInUseError("A recipe uses the ingredient, so it cannot be deleted.")
        await self._ingredients.items_to_text(ingredient.id, self._name(ingredient))
        if await self._ingredients.restriction_count(ingredient.id):
            ingredient.status = IngredientStatus.ARCHIVED
            ingredient.changed = now_utc()
            await self._ingredients.save(ingredient)
        else:
            await self._ingredients.delete(ingredient)
        await self._uow.commit()

    async def merge(self, actor: User, public_id: str, into_public_id: str) -> Ingredient:
        """Repoints recipe lines, shopping items and food restrictions to
        the target, then deletes the duplicate. Needs manage:ingredients."""
        if not actor.has_permission(Permission.MANAGE_INGREDIENTS):
            raise PermissionDeniedError("Merging ingredients needs manage:ingredients.")
        source = await self.get(public_id)
        target = await self.get(into_public_id)
        if source.id == target.id:
            raise IngredientMergeError("An ingredient cannot be merged into itself.")
        if source.seed_key:
            raise SeededResourceError("Base ingredients cannot be merged away.")
        await self._ingredients.repoint(source.id, target.id)
        if self._mirrors is not None:
            # The mappings of paired instances follow the merge.
            await self._mirrors.repoint_mappings(MappingKind.INGREDIENT, source.id, target.id)
        # The source's names live on as aliases of the target.
        moved: dict[str, set[str]] = {}
        for locale, text in source.translations.items():
            moved.setdefault(locale, set()).update({text.name, text.plural_name})
        for locale, names in source.aliases.items():
            moved.setdefault(locale, set()).update(names)
        await self._ingredients.delete(source)
        own = {
            loc: {t.name.casefold(), t.plural_name.casefold()}
            for loc, t in target.translations.items()
        }
        for locale, moved_names in moved.items():
            current = target.aliases.get(locale, [])
            known = {n.casefold() for n in current} | own.get(locale, set())
            owners = await self._ingredients.name_owners(locale, sorted(moved_names))
            extra = [
                n
                for n in sorted(moved_names)
                if n.strip()
                and n.casefold() not in known
                and owners.get(n.lower()) in (None, target.id)
            ]
            if extra:
                target.aliases[locale] = sorted({*current, *extra}, key=str.casefold)
        target.changed = now_utc()
        saved = await self._ingredients.save(target)
        await self._uow.commit()
        return saved

    @staticmethod
    def _name(ingredient: Ingredient) -> str:
        if not ingredient.translations:
            return ""
        return resolve(ingredient.translations, None, ingredient.original_locale)[1].name
