"""
Building mirrors: read-only local copies of the recipes paired instances
share with this one.

Every catalogue entry a received recipe names (units, tags, ingredients,
equipment, in the recipe and in its variations) is matched for its peer:
by seed key first, then by the saved mapping of that peer (an
administrator's earlier decision), else it needs a decision. A name or alias
in either language is only offered as a suggestion, never taken silently.
A unit that only the conversions of those ingredients name gets a mapping
too, matched by seed key or left undecided, but never needs a decision.
The decisions are `map` (to a local entry), `create` (a new local entry
prefilled from the peer's data: ingredients and equipment as drafts for the
review queue, tags active), `plain` (an ingredient or equipment line kept as
text with the peer's allergens and markers) and `none` (a unit left out, a
tag dropped). Every decision is saved as the peer's mapping and reused for
its later recipes; the latest data the peer sent for each entry is kept with
it.

A mirror is a recipe row without an owner, published, capped for peering
(`peer_capped`) and marked with its peer (`mirror_peer_id`), whose
visibility is the peer's incoming choice: every signed-in user (`instance`)
or the members of one group (`shared` with that group). Its steps name the
mapped local entries, so everything derived (the ingredient list, nutrition,
seasons) comes from the local catalogue. Plain-text lines and equipment, and
sub-recipe lines whose sub-recipe is not mirrored here, are kept in the
mirror's extras. Step and line ids derive from the source ids, so they stay
stable across updates, and each build appends a revision, so variations on
the mirror notice a source change. The source's variations are mirrored read
only under ids derived from theirs.

The document a mirror was built from is kept, so a corrected mapping
rebuilds every mirror of that peer at once, and a sub-recipe mirrored later
is linked into the mirrors that use it.
"""

import hashlib
import io
import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Literal
from uuid import UUID
from uuid import uuid5

from src.cookbook.application.services._exchange import first_name
from src.cookbook.application.services._exchange import parse_uuid
from src.cookbook.application.services.catalogue_matching import CatalogueMatcher
from src.cookbook.application.services.formats.catalogue_v1 import CatalogueSectionV1
from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import TagEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import UnitEntryV1
from src.cookbook.application.services.formats.codec import FormatError
from src.cookbook.application.services.formats.codec import read
from src.cookbook.application.services.formats.codec import to_json
from src.cookbook.application.services.formats.recipe_mapper import UsedRecords
from src.cookbook.application.services.formats.recipe_mapper import collect_used
from src.cookbook.application.services.formats.recipes_v1 import MANIFEST
from src.cookbook.application.services.formats.recipes_v1 import FileEntryV1
from src.cookbook.application.services.formats.recipes_v1 import RecipeContentV1
from src.cookbook.application.services.formats.recipes_v1 import RecipeEntryV1
from src.cookbook.application.services.formats.recipes_v1 import RecipesDocumentV1
from src.cookbook.application.services.formats.specs import RECIPES
from src.cookbook.application.services.recipe_deletion import RecipeDeletion
from src.cookbook.application.use_cases.equipment.manage_equipment import ManageEquipment
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ConversionCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import IngredientCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ManageIngredients
from src.cookbook.application.use_cases.recipes.manage_recipes import ManageRecipes
from src.cookbook.application.use_cases.recipes.manage_recipes import RecipeCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepEquipmentCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepIngredientCommand
from src.cookbook.application.use_cases.recipes.manage_variations import ManageVariations
from src.cookbook.application.use_cases.recipes.manage_variations import VariationCommand
from src.cookbook.application.use_cases.recipes.recipe_archive import _Ids
from src.cookbook.application.use_cases.recipes.recipe_archive import _ImportRun
from src.cookbook.application.use_cases.recipes.recipe_archive import _variation_change
from src.cookbook.application.use_cases.resources.manage_resources import ManageResources
from src.cookbook.application.use_cases.resources.manage_resources import TagCommand
from src.cookbook.domain.entities.mirror import CatalogueMapping
from src.cookbook.domain.entities.mirror import MappingAction
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.entities.mirror import RecipeMirror
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import DuplicateNameError
from src.cookbook.domain.exceptions import PeerMappingError
from src.cookbook.domain.exceptions import RecipeArchiveError
from src.cookbook.domain.services.translations import LOCALES
from src.cookbook.domain.services.variations import MAX_NAME
from src.cookbook.domain.services.variations import MAX_NOTE
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.peer import MirrorVisibility
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import FileTypeNotAcceptedError
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.image_processor import IImageProcessor
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.shared_kernel.domain.services.clock import now_utc

MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_UNPACKED_BYTES = 256 * 1024 * 1024
DecisionAction = Literal["map", "create", "plain", "none"]
# The decisions each kind of entry allows.
ALLOWED_ACTIONS: dict[MappingKind, frozenset[str]] = {
    MappingKind.UNIT: frozenset({"map", "none"}),
    MappingKind.TAG: frozenset({"map", "create", "none"}),
    MappingKind.INGREDIENT: frozenset({"map", "create", "plain"}),
    MappingKind.EQUIPMENT: frozenset({"map", "create", "plain"}),
}


def system_actor() -> User:
    """The stand-in account mirror work runs as: id 0, so revisions record
    no author and created catalogue entries no owner, and allowed to create
    draft ingredients."""
    return User(
        full_name="",
        email="",
        created=datetime(1970, 1, 1, tzinfo=UTC),
        hashed_password="",
        is_active=False,
        permissions=[Permission.WRITE_INGREDIENTS],
    )


def mirror_visibility(peer: Peer) -> tuple[RecipeVisibility, list[int]]:
    """The visibility and group shares of the peer's mirrors: every
    signed-in user, or the members of the chosen group (nobody while the
    group is gone)."""
    if peer.mirror_visibility == MirrorVisibility.GROUP:
        return RecipeVisibility.SHARED, [peer.mirror_group_id] if peer.mirror_group_id else []
    return RecipeVisibility.INSTANCE, []


@dataclass(frozen=True)
class Suggestion:
    id: str
    name: str


@dataclass(frozen=True)
class NeededEntry:
    """A catalogue entry of the peer that needs an administrator's decision."""

    kind: MappingKind
    remote_id: str
    name: str
    names: dict[str, str]
    suggestion: Suggestion | None = None
    # For ingredients: the category a created entry would get.
    category_suggestion: Suggestion | None = None
    allergens: list[str] = field(default_factory=list)
    diet_markers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MappingDecision:
    kind: MappingKind
    remote_id: str
    action: DecisionAction
    # The local entry's public id, for `map`.
    target_id: str | None = None
    # The category of a created ingredient, by public id; None leaves it
    # uncategorised.
    category_id: str | None = None


@dataclass(frozen=True)
class ReceivedRecipe:
    """A `.cui` payload of one recipe from a peer, opened."""

    document: RecipesDocumentV1
    entry: RecipeEntryV1
    archive: zipfile.ZipFile | None


def read_payload(data: bytes, item_id: str | None = None) -> ReceivedRecipe:
    """Opens the payload of one recipe; raises `RecipeArchiveError` when it
    is not a readable `cuisine-recipes` document of that recipe."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise RecipeArchiveError("The recipe from the other instance is no zip file.") from exc
    if sum(m.file_size for m in archive.infolist()) > MAX_UNPACKED_BYTES:
        raise RecipeArchiveError("The recipe from the other instance is too large.")
    try:
        raw = json.loads(archive.read(MANIFEST))
        document = RECIPES.read(raw)
    except (KeyError, ValueError, FormatError) as exc:
        raise RecipeArchiveError(
            f"The recipe from the other instance is unreadable: {exc}"
        ) from exc
    return ReceivedRecipe(document=document, entry=_entry(document, item_id), archive=archive)


def read_document(raw: dict[str, Any], item_id: str | None = None) -> ReceivedRecipe:
    """A stored document, without its images."""
    try:
        document = RECIPES.read(raw)
    except FormatError as exc:
        raise RecipeArchiveError(str(exc)) from exc
    return ReceivedRecipe(document=document, entry=_entry(document, item_id), archive=None)


def _entry(document: RecipesDocumentV1, item_id: str | None) -> RecipeEntryV1:
    for entry in document.recipes:
        if item_id is None or entry.id.lower() == item_id.lower():
            return entry
    raise RecipeArchiveError("The payload does not hold the recipe it was sent for.")


def used_records(received: ReceivedRecipe) -> UsedRecords:
    used = UsedRecords()
    collect_used(used, received.entry.snapshot, received.entry.variations)
    return used


def _remote_name(kind: MappingKind, entry: Any) -> tuple[str, dict[str, str]]:
    if kind is MappingKind.INGREDIENT:
        names = {k: v.name for k, v in entry.names.items() if v.name}
        return first_name(names, entry.original_locale), names
    if kind is MappingKind.UNIT:
        names = dict(entry.names)
        return first_name(names) or entry.code, names
    names = dict(entry.names)
    return first_name(names), names


class MirrorBuilder:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        mirror_repo: IMirrorRepository,
        variation_repo: IRecipeVariationRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        file_repo: IStoredFileRepository,
        images: IImageProcessor,
        recipes: ManageRecipes,
        variations: ManageVariations,
        ingredients: ManageIngredients,
        equipment: ManageEquipment,
        resources: ManageResources,
        peer_repo: IPeerRepository,
    ) -> None:
        self._peers = peer_repo
        self._recipes = recipe_repo
        self._mirrors = mirror_repo
        self._variations = variation_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._categories = category_repo
        self._families = family_repo
        self._files = file_repo
        self._images = images
        self._manage_recipes = recipes
        self._manage_variations = variations
        self._manage_ingredients = ingredients
        self._manage_equipment = equipment
        self._manage_resources = resources
        self._system = system_actor()

    def _matcher(self) -> CatalogueMatcher:
        return CatalogueMatcher(
            unit_repo=self._units,
            tag_repo=self._tags,
            category_repo=self._categories,
            family_repo=self._families,
            ingredient_repo=self._ingredients,
            equipment_repo=self._equipment,
        )

    # ── Matching ─────────────────────────────────────────────────────

    async def _seed_match(self, kind: MappingKind, entry: Any) -> int | None:
        key = getattr(entry, "seed_key", None)
        if not key:
            return None
        match kind:
            case MappingKind.UNIT:
                return next((u.id for u in await self._units.list_all() if u.seed_key == key), None)
            case MappingKind.TAG:
                return next((t.id for t in await self._tags.list_all() if t.seed_key == key), None)
            case MappingKind.INGREDIENT:
                found = (await self._ingredients.by_seed_keys([key])).get(key)
                return found.id if found is not None else None
            case MappingKind.EQUIPMENT:
                item = (await self._equipment.by_seed_keys([key])).get(key)
                return item.id if item is not None else None

    async def _suggest(
        self, matcher: CatalogueMatcher, kind: MappingKind, entry: Any
    ) -> Suggestion | None:
        match kind:
            case MappingKind.UNIT:
                unit = await matcher.unit(entry)
                return Suggestion(str(unit.public_id), unit.code) if unit else None
            case MappingKind.TAG:
                tag = await matcher.tag(entry)
                return Suggestion(str(tag.public_id), _tag_name(tag)) if tag else None
            case MappingKind.INGREDIENT:
                found = await matcher.ingredient(entry)
                if found is None or found.status is IngredientStatus.ARCHIVED:
                    return None
                return Suggestion(str(found.public_id), _ingredient_name(found))
            case MappingKind.EQUIPMENT:
                item = await matcher.equipment(entry)
                return Suggestion(str(item.public_id), _equipment_name(item)) if item else None

    @staticmethod
    def _entries(received: ReceivedRecipe) -> list[tuple[MappingKind, str, Any]]:
        """Every catalogue entry the recipe and its variations name."""
        used = used_records(received)
        catalogue = received.document.catalogue
        found: list[tuple[MappingKind, str, Any]] = []
        for kind, ids, entries in (
            (MappingKind.UNIT, used.units, catalogue.units),
            (MappingKind.TAG, used.tags, catalogue.tags),
            (MappingKind.INGREDIENT, used.ingredients, catalogue.ingredients),
            (MappingKind.EQUIPMENT, used.equipment, catalogue.equipment),
        ):
            for remote_id in sorted(ids):
                entry: Any = entries.get(remote_id)
                if entry is not None:
                    found.append((kind, remote_id, entry))
        return found

    async def needs(
        self, peer: Peer, received: ReceivedRecipe, *, record: bool
    ) -> list[NeededEntry]:
        """The entries that still need a decision. With `record` the peer's
        latest data of every entry and every seed key match are saved as its
        mappings; without it nothing is written."""
        matcher = self._matcher()
        needed: list[NeededEntry] = []
        now = now_utc()
        for kind, remote_id, entry in self._entries(received):
            mapping = await self._mirrors.mapping(peer.id, kind, remote_id)
            name, names = _remote_name(kind, entry)
            if mapping is None:
                mapping = CatalogueMapping(
                    peer_id=peer.id, kind=kind, remote_id=remote_id, updated=now
                )
            mapping = replace(mapping, remote_name=name, remote_data=to_json(entry), updated=now)
            if not mapping.decided:
                seeded = await self._seed_match(kind, entry)
                if seeded is not None:
                    mapping = replace(
                        mapping, action=MappingAction.MAP, local_id=seeded, matched_by="seed_key"
                    )
            if record:
                await self._mirrors.save_mapping(mapping)
            if mapping.decided:
                continue
            category = None
            if kind is MappingKind.INGREDIENT and entry.category is not None:
                found = await matcher.category(entry.category.seed_key, entry.category.names)
                if found is not None:
                    category = Suggestion(str(found.public_id), _name_of(found.translations))
            needed.append(
                NeededEntry(
                    kind=kind,
                    remote_id=remote_id,
                    name=name,
                    names=names,
                    suggestion=await self._suggest(matcher, kind, entry),
                    category_suggestion=category,
                    allergens=list(getattr(entry, "allergens", [])),
                    diet_markers=list(getattr(entry, "diet_markers", [])),
                )
            )
        if record:
            await self._record_conversion_units(peer, received, now)
        return needed

    async def _record_conversion_units(
        self, peer: Peer, received: ReceivedRecipe, now: datetime
    ) -> None:
        """Saves a mapping for each unit that only the conversions of the
        recipe's ingredients name. Such a unit never needs a decision, since
        no line of the recipe uses it, but its mapping lets an ingredient
        created from the peer's data keep the conversion, lets the peer's
        suggestions name it, and lets an administrator map it by hand. It is
        matched by seed key like every other unit and otherwise left
        undecided."""
        used = used_records(received)
        catalogue = received.document.catalogue
        wanted = {
            conversion.unit_id
            for remote_id in used.ingredients
            if (ingredient := catalogue.ingredients.get(remote_id)) is not None
            for conversion in ingredient.conversions
        } - set(used.units)
        for remote_id in sorted(wanted):
            entry = catalogue.units.get(remote_id)
            if entry is None:
                continue
            mapping = await self._mirrors.mapping(peer.id, MappingKind.UNIT, remote_id)
            if mapping is None:
                mapping = CatalogueMapping(
                    peer_id=peer.id, kind=MappingKind.UNIT, remote_id=remote_id, updated=now
                )
            name, _ = _remote_name(MappingKind.UNIT, entry)
            mapping = replace(mapping, remote_name=name, remote_data=to_json(entry), updated=now)
            if not mapping.decided:
                seeded = await self._seed_match(MappingKind.UNIT, entry)
                if seeded is not None:
                    mapping = replace(
                        mapping, action=MappingAction.MAP, local_id=seeded, matched_by="seed_key"
                    )
            await self._mirrors.save_mapping(mapping)

    # ── Decisions ────────────────────────────────────────────────────

    async def decide(
        self, peer: Peer, received: ReceivedRecipe | None, decision: MappingDecision
    ) -> CatalogueMapping:
        """Saves one decision as the peer's mapping, creating the local entry
        for `create` from the peer's data (from the received recipe, else
        from the data kept with the mapping)."""
        if decision.action not in ALLOWED_ACTIONS[decision.kind]:
            raise PeerMappingError(
                f"{decision.action!r} is not a choice for a {decision.kind.value}."
            )
        mapping = await self._mirrors.mapping(peer.id, decision.kind, decision.remote_id)
        entry: Any = None
        if received is not None:
            entry = getattr(received.document.catalogue, _section(decision.kind)).get(
                decision.remote_id
            )
        if mapping is None and entry is None:
            raise PeerMappingError(
                f"The other instance never sent the {decision.kind.value} {decision.remote_id}."
            )
        now = now_utc()
        if mapping is None:
            name, _ = _remote_name(decision.kind, entry)
            mapping = CatalogueMapping(
                peer_id=peer.id,
                kind=decision.kind,
                remote_id=decision.remote_id,
                remote_name=name,
                remote_data=to_json(entry),
                updated=now,
            )
        if entry is None:
            entry = _entry_from_data(decision.kind, mapping.remote_data)
        local_id: int | None = None
        created = False
        action = MappingAction.MAP
        match decision.action:
            case "map":
                local_id = await self._local_id(decision.kind, decision.target_id)
            case "create":
                local_id = await self._create(peer, decision, entry)
                created = True
            case "plain":
                action = MappingAction.PLAIN
            case "none":
                action = MappingAction.NONE
        mapping = replace(
            mapping,
            action=action,
            local_id=local_id,
            created_here=created,
            matched_by="decision",
            updated=now,
        )
        await self._mirrors.save_mapping(mapping)
        return mapping

    async def decide_automatically(self, peer: Peer, received: ReceivedRecipe) -> None:
        """Decides every entry of the recipe that still needs a decision,
        for a peer whose recipes are taken in without asking (`sync_all`):
        the suggested local entry (a unit by code, an ingredient or
        equipment item by name or alias in either language) is mapped;
        otherwise an ingredient or equipment item is created from the peer's
        data as a draft for the review queue (an ingredient in the category
        the peer names, when one matches, else uncategorised), a unit is
        left out and a tag dropped. An entry that cannot be created, such as
        one whose name is taken by an archived entry, is kept as plain text.
        The decisions are saved like an administrator's."""
        for needed in await self.needs(peer, received, record=True):
            suggestion = needed.suggestion
            if needed.kind in (MappingKind.UNIT, MappingKind.TAG):
                mapped = needed.kind is MappingKind.UNIT and suggestion is not None
                await self.decide(
                    peer,
                    received,
                    MappingDecision(
                        kind=needed.kind,
                        remote_id=needed.remote_id,
                        action="map" if mapped else "none",
                        target_id=suggestion.id if mapped and suggestion else None,
                    ),
                )
                continue
            if suggestion is not None:
                await self.decide(
                    peer,
                    received,
                    MappingDecision(
                        kind=needed.kind,
                        remote_id=needed.remote_id,
                        action="map",
                        target_id=suggestion.id,
                    ),
                )
                continue
            category = needed.category_suggestion
            try:
                await self.decide(
                    peer,
                    received,
                    MappingDecision(
                        kind=needed.kind,
                        remote_id=needed.remote_id,
                        action="create",
                        category_id=category.id if category else None,
                    ),
                )
            except (PeerMappingError, DuplicateNameError):
                await self.decide(
                    peer,
                    received,
                    MappingDecision(kind=needed.kind, remote_id=needed.remote_id, action="plain"),
                )

    async def _local_id(self, kind: MappingKind, public_id: str | None) -> int:
        found: Any = None
        if public_id:
            match kind:
                case MappingKind.UNIT:
                    found = await self._units.get_by_public_id(public_id)
                case MappingKind.TAG:
                    found = await self._tags.get_by_public_id(public_id)
                case MappingKind.INGREDIENT:
                    found = await self._ingredients.get_by_public_id(public_id)
                case MappingKind.EQUIPMENT:
                    found = await self._equipment.get_by_public_id(public_id)
        if found is None:
            raise PeerMappingError(f"Pick an existing {kind.value} to map to.")
        return int(found.id)

    async def _create(self, peer: Peer, decision: MappingDecision, entry: Any) -> int:
        try:
            match decision.kind:
                case MappingKind.INGREDIENT:
                    return await self._create_ingredient(peer, entry, decision.category_id)
                case MappingKind.EQUIPMENT:
                    names = {k: v for k, v in entry.names.items() if v and k in LOCALES}
                    locale = next((loc for loc in ("en-GB", "de-AT") if names.get(loc)), None)
                    if locale is None:
                        raise PeerMappingError("The equipment item has no name to create it with.")
                    try:
                        kind = EquipmentKind(entry.kind or EquipmentKind.UTENSIL.value)
                    except ValueError:
                        kind = EquipmentKind.UTENSIL
                    item = await self._manage_equipment.create_draft(
                        names[locale], locale, kind=kind
                    )
                    return item.id
                case MappingKind.TAG:
                    try:
                        tag_kind = TagKind(entry.kind or TagKind.OTHER.value)
                    except ValueError:
                        tag_kind = TagKind.OTHER
                    tag = await self._manage_resources.create_tag(
                        TagCommand(
                            kind=tag_kind,
                            translations={
                                k: NameText(v) for k, v in entry.names.items() if v and k in LOCALES
                            },
                            color=entry.color,
                        ),
                        commit=False,
                    )
                    return tag.id
        except DuplicateNameError as exc:
            raise PeerMappingError(f"{exc} Map the entry to the existing one instead.") from exc
        raise PeerMappingError(f"A {decision.kind.value} cannot be created here; map it instead.")

    async def _create_ingredient(
        self, peer: Peer, entry: IngredientEntryV1, category_id: str | None
    ) -> int:
        texts = {
            k: IngredientText(name=v.name, plural_name=v.plural_name)
            for k, v in entry.names.items()
            if v.name and k in LOCALES
        }
        original = entry.original_locale if entry.original_locale in texts else None
        original = original or next(iter(sorted(texts)), None)
        if original is None:
            raise PeerMappingError("The ingredient has no name to create it with.")
        units: dict[str, str] = {}
        for conversion in entry.conversions:
            mapping = await self._mirrors.mapping(peer.id, MappingKind.UNIT, conversion.unit_id)
            if mapping is not None and mapping.action is MappingAction.MAP and mapping.local_id:
                unit = next(
                    (u for u in await self._units.list_all() if u.id == mapping.local_id), None
                )
                if unit is not None:
                    units[conversion.unit_id] = str(unit.public_id)
        n = entry.nutrition
        command = IngredientCommand(
            original_locale=original,
            translations=texts,
            category_id=category_id,
            aliases={k: list(v) for k, v in entry.aliases.items() if k in LOCALES},
            nutrition=Nutrition(
                kcal=n.kcal,
                protein=n.protein,
                fat=n.fat,
                saturated_fat=n.saturated_fat,
                carbohydrates=n.carbohydrates,
                sugar=n.sugar,
                fibre=n.fibre,
                salt=n.salt,
            ),
            extended_nutrition=dict(entry.extended_nutrition),
            season_months=list(entry.season_months),
            density_g_per_ml=entry.density_g_per_ml,
            conversions=[
                ConversionCommand(unit_id=units[c.unit_id], grams=c.grams)
                for c in entry.conversions
                if c.unit_id in units
            ],
            allergens=[Allergen(a) for a in entry.allergens if a in Allergen],
            diet_markers=[DietMarker(m) for m in entry.diet_markers if m in DietMarker],
        )
        last: DuplicateNameError | None = None
        for attempt in (command, replace(command, aliases={})):
            try:
                created = await self._manage_ingredients.create(
                    self._system, attempt, status=IngredientStatus.DRAFT, commit=False
                )
            except DuplicateNameError as exc:
                last = exc
                continue
            return created.id
        assert last is not None
        raise last

    # ── Building ─────────────────────────────────────────────────────

    async def _resolved(self, peer: Peer, received: ReceivedRecipe) -> "_Resolved":
        """The peer's ids mapped to this instance's, per kind. Call only
        once `needs` is empty."""
        resolved = _Resolved()
        units = {u.id: u for u in await self._units.list_all()}
        tags = {t.id: t for t in await self._tags.list_all()}
        for kind, remote_id, entry in self._entries(received):
            mapping = await self._mirrors.mapping(peer.id, kind, remote_id)
            if mapping is None or not mapping.decided:
                raise PeerMappingError(
                    "A catalogue entry of the recipe has no mapping yet.",
                    missing=[f"{kind.value}:{remote_id}"],
                )
            if mapping.action is MappingAction.PLAIN:
                resolved.plain[remote_id] = entry
                continue
            if mapping.action is not MappingAction.MAP or mapping.local_id is None:
                continue
            match kind:
                case MappingKind.UNIT:
                    unit = units.get(mapping.local_id)
                    if unit is not None:
                        resolved.unit[remote_id] = str(unit.public_id)
                        resolved.unit_names[str(unit.public_id)] = {
                            k: v.name for k, v in unit.translations.items()
                        }
                case MappingKind.TAG:
                    tag = tags.get(mapping.local_id)
                    if tag is not None:
                        resolved.tag[remote_id] = str(tag.public_id)
                case MappingKind.INGREDIENT:
                    found = (await self._ingredients.get_many([mapping.local_id])) or []
                    if found:
                        resolved.ingredient[remote_id] = str(found[0].public_id)
                case MappingKind.EQUIPMENT:
                    items = await self._equipment.get_many([mapping.local_id])
                    if items:
                        resolved.equipment[remote_id] = str(items[0].public_id)
        for line_unit, entry in received.document.catalogue.units.items():
            resolved.remote_unit_names[line_unit] = dict(entry.names)
        return resolved

    async def _store_files(
        self, received: ReceivedRecipe, known: Mapping[str, str]
    ) -> dict[str, str]:
        """Every image of the payload as a local stored file: one stored for
        an earlier revision is reused, a new one is stored as an upload
        would be. A missing or unreadable image is left out."""
        found: dict[str, str] = {}
        for public_id, entry in received.document.files.items():
            if public_id in known and await self._files.get_by_public_id(known[public_id]):
                found[public_id] = known[public_id]
                continue
            if received.archive is None:
                continue
            stored = await self._store_file(received.archive, entry, public_id)
            if stored is not None:
                found[public_id] = str(stored.public_id)
        return found

    async def _store_file(
        self, archive: zipfile.ZipFile, entry: FileEntryV1, public_id: str
    ) -> StoredFile | None:
        name = entry.name or public_id
        try:
            info = archive.getinfo(entry.path)
            if info.file_size > MAX_IMAGE_BYTES:
                return None
            processed = await self._images.process(archive.read(info))
        except (KeyError, FileTypeNotAcceptedError):
            return None
        return await self._files.add(
            StoredFile(
                file_name=f"{name.rsplit('.', 1)[0] or 'image'}.webp",
                content_type="image/webp",
                size=len(processed.data),
                content_hash=hashlib.sha256(processed.data).hexdigest(),
                created=now_utc(),
                creator_id=None,
                width=processed.width,
                height=processed.height,
                thumbnail_size=len(processed.thumbnail),
                thumbnail_hash=hashlib.sha256(processed.thumbnail).hexdigest(),
            ),
            processed.data,
            processed.thumbnail,
        )

    async def build(
        self,
        peer: Peer,
        received: ReceivedRecipe,
        *,
        etag: str,
        note: str,
    ) -> Recipe:
        """Creates or updates the peer's mirror of the received recipe. Every
        catalogue entry must have a mapping (`needs` empty)."""
        entry = received.entry
        origin = parse_uuid(entry.id)
        if origin is None:
            raise RecipeArchiveError("The recipe from the other instance has no valid id.")
        existing = await self._mirrors.by_origin(peer.id, origin)
        recipe = await self._recipes.get(existing.recipe_id) if existing is not None else None
        resolved = await self._resolved(peer, received)
        files = await self._store_files(received, existing.files if existing else {})
        resolved.file = files
        for sub_id in {
            line.sub_recipe_id
            for line in [
                *(si for step in entry.snapshot.steps for si in step.ingredients),
                *entry.snapshot.ingredients,
            ]
            if line.sub_recipe_id
        }:
            sub_origin = parse_uuid(sub_id)
            sub = await self._mirrors.by_origin(peer.id, sub_origin) if sub_origin else None
            if sub is not None:
                sub_recipe = await self._recipes.get(sub.recipe_id)
                if sub_recipe is not None:
                    resolved.recipe[sub_id] = str(sub_recipe.public_id)
        now = now_utc()
        if recipe is None:
            recipe = Recipe(
                owner_id=None,
                original_locale=entry.snapshot.original_locale,
                created=now,
                changed=now,
                status=RecipeStatus.PUBLISHED,
                published_at=now,
                created_via=CreatedVia.PEER,
                mirror_peer_id=peer.id,
                peer_capped=True,
            )
        instance_id = parse_uuid(received.document.instance_id)
        recipe.origin_instance_id = instance_id if instance_id else None
        recipe.origin_public_id = origin if instance_id else None
        recipe.visibility, recipe.shared_group_ids = mirror_visibility(peer)
        recipe.shared_user_ids, recipe.shared_peer_ids, recipe.co_editor_ids = [], [], []
        command, extras = _mirror_command(entry, resolved)
        extras.update(_author_avatars(entry, files))
        saved = await self._manage_recipes.save_mirror(
            recipe, command, system=self._system, note=note
        )
        await self._mirror_variations(saved, entry, resolved)
        old_files = set(existing.files.values()) if existing else set()
        await self._mirrors.save(
            RecipeMirror(
                recipe_id=saved.id,
                peer_id=peer.id,
                origin_public_id=origin,
                etag=etag,
                source_revision=etag.removeprefix("W/").strip('"'),
                source_author_name=entry.author_name,
                document=to_json(received.document),
                files=files,
                extras=extras,
                accepted_at=existing.accepted_at if existing else now,
                updated_at=now,
            )
        )
        await self._drop_files(sorted(old_files - set(files.values())), saved.id)
        if existing is None:
            await self._link_parents(peer, entry.id)
        return saved

    async def _drop_files(self, public_ids: list[str], recipe_id: int) -> None:
        for public_id in public_ids:
            stored = await self._files.get_by_public_id(public_id)
            if stored is not None and not await self._recipes.file_in_use_elsewhere(
                stored.id, recipe_id
            ):
                await self._files.delete(stored)

    async def _mirror_variations(
        self, recipe: Recipe, entry: RecipeEntryV1, resolved: "_Resolved"
    ) -> None:
        """The source's variations, read only, under ids derived from
        theirs; those the source no longer sends are removed. Local
        variations on the mirror stay."""
        run = _ImportRun()
        ids = resolved.ids()
        kept: set[UUID] = set()
        for variation in entry.variations:
            source_id = parse_uuid(variation.id)
            if source_id is None or variation.private:
                continue
            locale = variation.locale if variation.locale in LOCALES else recipe.original_locale
            commands = [
                command
                for change in variation.changes
                if (
                    command := _variation_change(
                        change, ids, entry.snapshot.names, "", variation, run
                    )
                )
            ]
            fitting, _ = await self._manage_variations.fitting_changes(recipe, commands, locale)
            public_id = uuid5(recipe.public_id, f"variation:{source_id}")
            kept.add(public_id)
            await self._manage_variations.save_mirrored(
                recipe,
                public_id,
                source_id,
                variation.author_name,
                VariationCommand(
                    name=(variation.name.strip() or "Variation")[:MAX_NAME],
                    locale=locale,
                    note=variation.note.strip()[:MAX_NOTE],
                    private=False,
                    changes=fitting,
                ),
            )
        for stored in await self._variations.for_recipe(recipe.id):
            if stored.mirrored and stored.public_id not in kept:
                await self._variations.delete(stored)

    async def _link_parents(self, peer: Peer, source_id: str) -> None:
        """A sub-recipe mirrored after the mirrors that use it: they link it
        now."""
        for mirror in await self._mirrors.for_peer(peer.id):
            unlinked = mirror.extras.get("unlinked_sub_recipes") or []
            if any(str(u.get("source_id", "")).lower() == source_id.lower() for u in unlinked):
                await self.rebuild(peer, mirror, note="Sub-recipe linked")

    async def rebuild(self, peer: Peer, mirror: RecipeMirror, *, note: str) -> Recipe | None:
        """Builds the mirror again from the document it was built from, after
        a mapping changed or a sub-recipe came or went. Returns None (and
        changes nothing) when an entry now lacks a mapping."""
        received = read_document(mirror.document)
        if await self.needs(peer, received, record=False):
            return None
        return await self.build(peer, received, etag=mirror.etag, note=note)

    async def remove(self, mirror: RecipeMirror) -> None:
        """Deletes the mirror like any recipe (its local variations, the
        personal records on it and its images go with it, and so do the
        authors' avatars it came with); the mirrors using it as a sub-recipe
        are rebuilt without the link."""
        recipe = await self._recipes.get(mirror.recipe_id)
        if recipe is None:
            return
        parents = (await self._recipes.parent_ids([recipe.id])).get(recipe.id, [])
        await RecipeDeletion(recipe_repo=self._recipes, file_repo=self._files).stage(
            recipe, unlink_parents=True
        )
        await self._drop_files(sorted(set(mirror.files.values())), recipe.id)
        if not parents:
            return
        peer = await self._peers.get(mirror.peer_id)
        if peer is None:
            return
        for parent in (await self._mirrors.for_recipes(parents)).values():
            if parent.peer_id == peer.id:
                await self.rebuild(peer, parent, note="Sub-recipe withdrawn")

    async def set_visibility(self, peer: Peer) -> None:
        """Applies the peer's incoming visibility to all its mirrors."""
        visibility, groups = mirror_visibility(peer)
        for recipe in await self._recipes.mirrors_of(peer.id):
            if recipe.visibility is visibility and recipe.shared_group_ids == groups:
                continue
            recipe.visibility, recipe.shared_group_ids = visibility, groups
            await self._recipes.save(recipe)


@dataclass
class _Resolved:
    """The peer's ids mapped to this instance's public ids, per kind, plus
    the entries kept as plain text."""

    unit: dict[str, str] = field(default_factory=dict)
    tag: dict[str, str] = field(default_factory=dict)
    ingredient: dict[str, str] = field(default_factory=dict)
    equipment: dict[str, str] = field(default_factory=dict)
    recipe: dict[str, str] = field(default_factory=dict)
    file: dict[str, str] = field(default_factory=dict)
    plain: dict[str, Any] = field(default_factory=dict)
    unit_names: dict[str, dict[str, str]] = field(default_factory=dict)
    remote_unit_names: dict[str, dict[str, str]] = field(default_factory=dict)

    def ids(self) -> _Ids:
        return _Ids(
            ingredient=self.ingredient,
            equipment=self.equipment,
            unit=self.unit,
            tag=self.tag,
            file=self.file,
            recipe=self.recipe,
            catalogue=CatalogueSectionV1(),
        )


def _author_avatars(entry: RecipeEntryV1, files: Mapping[str, str]) -> dict[str, Any]:
    """The local public ids of the avatars of the recipe's author and of
    its variations' authors, for the mirror's extras. The source sends an
    avatar only while the author shows their name on paired instances."""
    variations = {
        v.id.lower(): files[v.author_avatar]
        for v in entry.variations
        if v.author_avatar and v.author_avatar in files
    }
    recipe = files.get(entry.author_avatar) if entry.author_avatar else None
    return {"author_avatar": recipe, "variation_author_avatars": variations}


def _section(kind: MappingKind) -> str:
    return {
        MappingKind.UNIT: "units",
        MappingKind.TAG: "tags",
        MappingKind.INGREDIENT: "ingredients",
        MappingKind.EQUIPMENT: "equipment",
    }[kind]


def _entry_from_data(kind: MappingKind, data: dict[str, Any]) -> Any:
    cls: type = {
        MappingKind.UNIT: UnitEntryV1,
        MappingKind.TAG: TagEntryV1,
        MappingKind.INGREDIENT: IngredientEntryV1,
        MappingKind.EQUIPMENT: EquipmentEntryV1,
    }[kind]
    try:
        return read(cls, data)
    except FormatError as exc:
        raise PeerMappingError("The data kept for this entry is unreadable.") from exc


def _name_of(translations: Mapping[str, Any]) -> str:
    return first_name({k: v.name for k, v in translations.items()})


def _tag_name(tag: Any) -> str:
    return _name_of(tag.translations)


def _ingredient_name(ingredient: Any) -> str:
    return first_name(
        {k: v.name for k, v in ingredient.translations.items()}, ingredient.original_locale
    )


def _equipment_name(item: Any) -> str:
    return _name_of(item.translations)


def _difficulty(value: str) -> Difficulty:
    try:
        return Difficulty(value)
    except ValueError:
        return Difficulty.EASY


def _label(amount: float | None, unit: Mapping[str, str], name: str, locale: str) -> str:
    parts = []
    if amount is not None:
        parts.append(f"{amount:g}")
    unit_name = unit.get(locale) or first_name(unit)
    if unit_name:
        parts.append(unit_name)
    parts.append(name)
    return " ".join(parts)


def _mirror_command(
    entry: RecipeEntryV1, resolved: _Resolved
) -> tuple[RecipeCommand, dict[str, Any]]:
    """The save command of the mirror and its extras: the lines and
    equipment kept as plain text, and the sub-recipe lines whose sub-recipe
    is not mirrored here. Mentions of anything not placed become text. The
    declared ingredient list keeps only the lines naming a mapped
    ingredient or a mirrored sub-recipe; the steps' plain-text and unlinked
    lines still carry what the steps use of the rest."""
    content: RecipeContentV1 = entry.snapshot
    ids = resolved.ids()
    plain_lines: list[dict[str, Any]] = []
    plain_equipment: list[dict[str, Any]] = []
    unlinked: list[dict[str, Any]] = []
    steps: list[StepCommand] = []
    for index, step in enumerate(content.steps):
        lines: list[StepIngredientCommand] = []
        for position, line in enumerate(step.ingredients):
            notes = {k: NoteText(v.note) for k, v in line.notes.items() if k in LOCALES}
            unit = resolved.unit.get(line.unit_id) if line.unit_id else None
            if line.sub_recipe_id:
                target = resolved.recipe.get(line.sub_recipe_id)
                if target is None:
                    titles = content.names.recipes.get(line.sub_recipe_id) or {}
                    unlinked.append(
                        {
                            "step": index,
                            "position": position,
                            "source_id": line.sub_recipe_id,
                            "titles": dict(titles),
                            "amount": line.amount,
                            "unit_id": unit,
                        }
                    )
                    continue
                lines.append(
                    StepIngredientCommand(
                        id=line.id,
                        sub_recipe_id=target,
                        amount=line.amount,
                        unit_id=unit,
                        notes=notes,
                    )
                )
                continue
            remote = line.ingredient_id or ""
            if remote in resolved.plain:
                source = resolved.plain[remote]
                names = {k: v.name for k, v in source.names.items() if v.name}
                unit_names = resolved.unit_names.get(unit, {}) if unit else {}
                plain_lines.append(
                    {
                        "step": index,
                        "position": position,
                        "names": names,
                        "amount": line.amount,
                        "unit_id": unit,
                        "notes": {k: v.note for k, v in notes.items()},
                        "allergens": list(source.allergens),
                        "diet_markers": list(source.diet_markers),
                        "labels": {
                            locale: _label(
                                line.amount,
                                unit_names,
                                names.get(locale) or first_name(names, source.original_locale),
                                locale,
                            )
                            for locale in LOCALES
                        },
                    }
                )
                continue
            target = resolved.ingredient.get(remote)
            if target is None:
                continue
            lines.append(
                StepIngredientCommand(
                    id=line.id, ingredient_id=target, amount=line.amount, unit_id=unit, notes=notes
                )
            )
        equipment: list[StepEquipmentCommand] = []
        for item in step.equipment:
            remote = item.equipment_id or ""
            if remote in resolved.plain:
                source = resolved.plain[remote]
                plain_equipment.append(
                    {
                        "step": index,
                        "names": dict(source.names),
                        "count": item.count,
                        "notes": {k: v.note for k, v in item.notes.items()},
                    }
                )
                continue
            if remote in resolved.equipment:
                equipment.append(
                    StepEquipmentCommand(
                        id=item.id,
                        equipment_id=resolved.equipment[remote],
                        count=item.count,
                        notes={k: NoteText(v.note) for k, v in item.notes.items() if k in LOCALES},
                    )
                )
        steps.append(
            StepCommand(
                id=step.id,
                translations={
                    k: StepText(ids.rewrite(v.text))
                    for k, v in step.translations.items()
                    if k in LOCALES
                },
                duration_minutes=step.duration_minutes,
                image_file_id=resolved.file.get(step.image_id) if step.image_id else None,
                ingredients=lines,
                equipment=equipment,
            )
        )
    yield_unit = resolved.unit.get(content.yield_unit_id) if content.yield_unit_id else None
    command = RecipeCommand(
        original_locale=content.original_locale,
        translations={
            k: RecipeText(v.title, v.description, v.tips)
            for k, v in content.translations.items()
            if k in LOCALES
        },
        base_servings=content.base_servings,
        prep_minutes=content.prep_minutes,
        cook_minutes=content.cook_minutes,
        rest_minutes=content.rest_minutes,
        difficulty=_difficulty(content.difficulty),
        cover_file_id=resolved.file.get(content.cover_image_id) if content.cover_image_id else None,
        source_url=content.source_url,
        source_name=content.source_name,
        tag_ids=[resolved.tag[t] for t in content.tag_ids if t in resolved.tag],
        steps=steps,
        ingredients=[
            StepIngredientCommand(
                id=line.id,
                ingredient_id=resolved.ingredient.get(line.ingredient_id or "")
                if not line.sub_recipe_id
                else None,
                sub_recipe_id=resolved.recipe.get(line.sub_recipe_id)
                if line.sub_recipe_id
                else None,
                amount=line.amount,
                unit_id=resolved.unit.get(line.unit_id) if line.unit_id else None,
                notes={k: NoteText(v.note) for k, v in line.notes.items() if k in LOCALES},
            )
            for line in content.ingredients
            if (line.sub_recipe_id and line.sub_recipe_id in resolved.recipe)
            or (
                not line.sub_recipe_id
                and (line.ingredient_id or "") not in resolved.plain
                and (line.ingredient_id or "") in resolved.ingredient
            )
        ],
        yield_amount=content.yield_amount if yield_unit else None,
        yield_unit_id=yield_unit,
    )
    extras = {
        "plain_lines": plain_lines,
        "plain_equipment": plain_equipment,
        "unlinked_sub_recipes": unlinked,
    }
    return command, extras
