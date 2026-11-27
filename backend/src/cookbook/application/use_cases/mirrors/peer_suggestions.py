"""
Suggestions from paired instances: catalogue values a peer sent with its
recipes that differ from the local entry its mapping points at, listed for
an administrator next to the reference data updates and accepted or
dismissed field by field. The local catalogue never changes without that.

Each mapping that points at a local unit, tag, ingredient or equipment item
keeps the latest catalogue entry the peer sent (`remote_data`). Both sides
become named fields as in the catalogue file (`catalogue_fields.py`) and
are compared the same way: an empty value from the peer is a gap, except
allergens, diet markers and season months. Two fields are compared as what
the peer adds rather than as a replacement, since the peer's entry covers
only what its recipes needed: other names per locale are the local list
joined with the peer's, and conversions are the local ones with the peer's
added or changed. A conversion names its unit through the peer's unit
mapping; a unit without a mapping is left out and named with the
suggestion. A category or family is found by seed key or name.

Nothing is stored beyond dismissals: the suggestions are computed on every
read from the mappings, so a newer `remote_data` updates them at once, also
for entries created here from the peer's data. A dismissal keeps the peer,
kind, entry, field and a digest of the value the peer offered; the
suggestion stays hidden until the peer offers another value.

Reading needs read:settings (checked by the route). Accepting and
dismissing need the rights of the catalogue file for the kind: ingredients
manage:ingredients and write:ingredients, units, tags and equipment
write:resources. Accepting writes through the normal use cases, so a name or
other name another entry holds is refused with `DuplicateNameError`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Final

from src.cookbook.application.services.catalogue_fields import CatalogueLookups
from src.cookbook.application.services.catalogue_fields import CatalogueWriter
from src.cookbook.application.services.catalogue_fields import Fields
from src.cookbook.application.services.catalogue_fields import Ref
from src.cookbook.application.services.catalogue_fields import clean_list
from src.cookbook.application.services.catalogue_fields import current_fields
from src.cookbook.application.services.catalogue_fields import equipment_fields
from src.cookbook.application.services.catalogue_fields import find_differences
from src.cookbook.application.services.catalogue_fields import first_name
from src.cookbook.application.services.catalogue_fields import ingredient_fields
from src.cookbook.application.services.catalogue_fields import is_safety
from src.cookbook.application.services.catalogue_fields import local_ref
from src.cookbook.application.services.catalogue_fields import plain
from src.cookbook.application.services.catalogue_fields import resolve_local
from src.cookbook.application.services.catalogue_fields import row_names
from src.cookbook.application.services.catalogue_fields import sorted_conversions
from src.cookbook.application.services.catalogue_fields import tag_fields
from src.cookbook.application.services.catalogue_fields import unit_fields
from src.cookbook.application.services.catalogue_fields import value_hash
from src.cookbook.application.services.catalogue_matching import CatalogueMatcher
from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import TagEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import UnitEntryV1
from src.cookbook.application.services.formats.codec import FormatError
from src.cookbook.application.services.formats.codec import read
from src.cookbook.application.use_cases.resources.catalogue_file import CatalogueFile
from src.cookbook.domain.entities.mirror import CatalogueMapping
from src.cookbook.domain.entities.mirror import MappingAction
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.entities.mirror import SuggestionDismissal
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.exceptions import PeerMappingNotFoundError
from src.cookbook.domain.exceptions import PeerSuggestionNotFoundError
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
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
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PeerNotFoundError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# The kinds a mapping can point at, in the order the list shows them.
SUGGESTION_KINDS: Final = (
    MappingKind.INGREDIENT,
    MappingKind.UNIT,
    MappingKind.TAG,
    MappingKind.EQUIPMENT,
)
_ENTRY_TYPES: Final[dict[MappingKind, type]] = {
    MappingKind.UNIT: UnitEntryV1,
    MappingKind.TAG: TagEntryV1,
    MappingKind.INGREDIENT: IngredientEntryV1,
    MappingKind.EQUIPMENT: EquipmentEntryV1,
}


@dataclass(frozen=True)
class PeerSuggestion:
    """One field of a local entry with the value a peer offers for it."""

    peer: Peer
    kind: MappingKind
    # The entry's public id at the peer.
    source_id: str
    local: Any
    field: str
    current: Any
    suggested: Any
    # Digest of what the peer offers, for dismissals.
    offered_hash: str
    # Conversions only: the peer's units that have no mapping here, by name.
    unmapped_units: list[str]


@dataclass(frozen=True)
class SuggestionItem:
    peer: Peer
    source_id: str
    field: str
    # Plain JSON values: references by name, conversions as unit code to grams.
    current: Any
    suggested: Any
    unmapped_units: list[str]


@dataclass(frozen=True)
class SuggestionGroup:
    """Every suggestion for one local entry, from every peer."""

    kind: str
    id: str
    name: str
    # True when an allergen or diet marker suggestion is among them.
    warning: bool
    suggestions: list[SuggestionItem]


@dataclass
class _Context:
    locale: str
    lookups: CatalogueLookups
    matcher: CatalogueMatcher
    tags: dict[int, Any]


class PeerSuggestions:
    def __init__(
        self,
        *,
        peer_repo: IPeerRepository,
        mirror_repo: IMirrorRepository,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        writer: CatalogueWriter,
        uow: IUnitOfWork,
    ) -> None:
        self._peers = peer_repo
        self._mirrors = mirror_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._categories = category_repo
        self._families = family_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._writer = writer
        self._uow = uow

    # ── Reading ──────────────────────────────────────────────────────

    async def read(
        self,
        actor: User,
        *,
        peer_public_id: str | None = None,
        kind: MappingKind | None = None,
    ) -> list[SuggestionGroup]:
        """The suggestions not dismissed, grouped by local entry: entries
        with allergen or diet marker suggestions first, then by kind and
        name; within an entry those two fields first."""
        if peer_public_id is not None:
            peers = [await self._peer(peer_public_id)]
        else:
            peers = await self._peers.list_active()
        ctx = await self._context(actor)
        found: list[PeerSuggestion] = []
        for peer in peers:
            found += await self._for_peer(ctx, peer, kind)
        return self._groups(ctx, found)

    def _groups(self, ctx: _Context, found: list[PeerSuggestion]) -> list[SuggestionGroup]:
        grouped: dict[tuple[str, str], list[PeerSuggestion]] = {}
        locals_: dict[tuple[str, str], Any] = {}
        for s in found:
            key = (s.kind.value, str(s.local.public_id))
            grouped.setdefault(key, []).append(s)
            locals_[key] = s.local
        groups: list[SuggestionGroup] = []
        for (kind, public_id), items in grouped.items():
            items.sort(key=lambda s: (not is_safety(s.field), s.field, s.peer.name.casefold()))
            groups.append(
                SuggestionGroup(
                    kind=kind,
                    id=public_id,
                    name=self._name(locals_[(kind, public_id)], ctx.locale),
                    warning=any(is_safety(s.field) for s in items),
                    suggestions=[
                        SuggestionItem(
                            peer=s.peer,
                            source_id=s.source_id,
                            field=s.field,
                            current=plain(s.current),
                            suggested=plain(s.suggested),
                            unmapped_units=s.unmapped_units,
                        )
                        for s in items
                    ],
                )
            )
        order = {k.value: i for i, k in enumerate(SUGGESTION_KINDS)}
        groups.sort(key=lambda g: (not g.warning, order[g.kind], g.name.casefold()))
        return groups

    @staticmethod
    def _name(local: Any, locale: str) -> str:
        if isinstance(local, Unit):
            return first_name(row_names(local), locale) or local.code
        return first_name(row_names(local), locale) or "?"

    async def _peer(self, public_id: str) -> Peer:
        peer = await self._peers.get_by_public_id(public_id)
        if peer is None or not peer.active:
            raise PeerNotFoundError("No such paired instance.")
        return peer

    async def _context(self, actor: User) -> _Context:
        return _Context(
            locale=ui_locale(actor.language.value),
            lookups=CatalogueLookups(
                categories={c.id: c for c in await self._categories.list_all()},
                families={f.id: f for f in await self._families.list_all()},
                units={u.id: u for u in await self._units.list_all()},
            ),
            matcher=CatalogueMatcher(
                unit_repo=self._units,
                tag_repo=self._tags,
                category_repo=self._categories,
                family_repo=self._families,
                ingredient_repo=self._ingredients,
                equipment_repo=self._equipment,
            ),
            tags={t.id: t for t in await self._tags.list_all()},
        )

    async def _for_peer(
        self,
        ctx: _Context,
        peer: Peer,
        kind: MappingKind | None,
        only: tuple[MappingKind, str] | None = None,
    ) -> list[PeerSuggestion]:
        mappings = await self._mirrors.mappings(peer.id)
        units = self._unit_mappings(ctx, mappings)
        if kind in (None, MappingKind.INGREDIENT):
            await self._conversion_units(ctx, peer, mappings, units)
        dismissed = {
            (d.kind, d.remote_id, d.field): d.value_hash
            for d in await self._mirrors.dismissals(peer.id)
        }
        wanted = [
            m
            for m in mappings
            if m.action is MappingAction.MAP
            and m.local_id is not None
            and (kind is None or m.kind is kind)
            and (only is None or (m.kind, m.remote_id) == only)
        ]
        locals_ = await self._locals(ctx, wanted)
        found: list[PeerSuggestion] = []
        for mapping in wanted:
            local = locals_.get((mapping.kind, mapping.local_id or 0))
            if local is None:
                continue
            found.extend(
                s
                for s in await self._suggestions(ctx, peer, mapping, local, units)
                if dismissed.get((s.kind, s.source_id, s.field)) != s.offered_hash
            )
        return found

    @staticmethod
    def _unit_mappings(
        ctx: _Context, mappings: list[CatalogueMapping]
    ) -> dict[str, tuple[Unit | None, str]]:
        """Each of the peer's units by its id there: the unit here it maps
        to (None without one) and the peer's name for it."""
        found: dict[str, tuple[Unit | None, str]] = {}
        for m in mappings:
            if m.kind is not MappingKind.UNIT:
                continue
            unit = (
                ctx.lookups.units.get(m.local_id)
                if m.action is MappingAction.MAP and m.local_id is not None
                else None
            )
            code = str(m.remote_data.get("code") or "") if m.remote_data else ""
            found[m.remote_id] = (unit, code or m.remote_name or m.remote_id)
        return found

    async def _conversion_units(
        self,
        ctx: _Context,
        peer: Peer,
        mappings: list[CatalogueMapping],
        units: dict[str, tuple[Unit | None, str]],
    ) -> None:
        """Adds the peer's units that its ingredients' conversions name but
        that have no mapping, which happens for mirrors received before such
        units got one. They are read from the documents of the peer's mirrors
        and taken when their seed key names a unit here; a code alone is
        never taken silently."""
        wanted = (
            {
                c.get("unit_id")
                for m in mappings
                if m.kind is MappingKind.INGREDIENT and m.action is MappingAction.MAP
                for c in m.remote_data.get("conversions") or []
                if isinstance(c, dict)
            }
            - set(units)
            - {None}
        )
        if not wanted:
            return
        by_key = {u.seed_key: u for u in ctx.lookups.units.values() if u.seed_key}
        for mirror in await self._mirrors.for_peer(peer.id):
            catalogue = mirror.document.get("catalogue")
            section = catalogue.get("units") if isinstance(catalogue, dict) else None
            if not isinstance(section, dict):
                continue
            for remote_id in list(wanted):
                data = section.get(remote_id)
                if not isinstance(data, dict):
                    continue
                key = data.get("seed_key")
                units[str(remote_id)] = (
                    by_key.get(key) if isinstance(key, str) else None,
                    str(data.get("code") or remote_id),
                )
                wanted.discard(remote_id)
            if not wanted:
                return

    async def _locals(
        self, ctx: _Context, mappings: list[CatalogueMapping]
    ) -> dict[tuple[MappingKind, int], Any]:
        ids: dict[MappingKind, set[int]] = {}
        for m in mappings:
            ids.setdefault(m.kind, set()).add(m.local_id or 0)
        found: dict[tuple[MappingKind, int], Any] = {}
        for unit_id in ids.get(MappingKind.UNIT, set()):
            if unit_id in ctx.lookups.units:
                found[(MappingKind.UNIT, unit_id)] = ctx.lookups.units[unit_id]
        for tag_id in ids.get(MappingKind.TAG, set()):
            if tag_id in ctx.tags:
                found[(MappingKind.TAG, tag_id)] = ctx.tags[tag_id]
        if ids.get(MappingKind.INGREDIENT):
            for ingredient in await self._ingredients.get_many(sorted(ids[MappingKind.INGREDIENT])):
                # An archived ingredient has left the catalogue.
                if ingredient.status is not IngredientStatus.ARCHIVED:
                    found[(MappingKind.INGREDIENT, ingredient.id)] = ingredient
        if ids.get(MappingKind.EQUIPMENT):
            for item in await self._equipment.get_many(sorted(ids[MappingKind.EQUIPMENT])):
                found[(MappingKind.EQUIPMENT, item.id)] = item
        return found

    async def _suggestions(
        self,
        ctx: _Context,
        peer: Peer,
        mapping: CatalogueMapping,
        local: Any,
        units: Mapping[str, tuple[Unit | None, str]],
    ) -> list[PeerSuggestion]:
        try:
            entry: Any = read(_ENTRY_TYPES[mapping.kind], mapping.remote_data)
        except FormatError:
            return []
        current = current_fields(mapping.kind.value, local, ctx.lookups, ctx.locale)
        unmapped: list[str] = []
        match mapping.kind:
            case MappingKind.UNIT:
                offered = unit_fields(entry)
            case MappingKind.TAG:
                offered = tag_fields(entry)
            case MappingKind.EQUIPMENT:
                offered = equipment_fields(entry)
            case MappingKind.INGREDIENT:
                offered, unmapped = await self._ingredient_offer(ctx, entry, units)
        incoming = _joined(offered, current)
        return [
            PeerSuggestion(
                peer=peer,
                kind=mapping.kind,
                source_id=mapping.remote_id,
                local=local,
                field=d.field,
                current=d.current,
                suggested=d.incoming,
                offered_hash=value_hash(offered[d.field]),
                unmapped_units=unmapped if d.field == "conversions" else [],
            )
            for d in find_differences(incoming, current)
        ]

    async def _ingredient_offer(
        self,
        ctx: _Context,
        entry: IngredientEntryV1,
        units: Mapping[str, tuple[Unit | None, str]],
    ) -> tuple[Fields, list[str]]:
        category = None
        if entry.category is not None:
            found = await ctx.matcher.category(entry.category.seed_key, entry.category.names)
            category = local_ref(found, ctx.locale) if found is not None else None
        family = None
        if entry.family is not None:
            kin = await ctx.matcher.family(entry.family.seed_key, entry.family.names)
            family = local_ref(kin, ctx.locale) if kin is not None else None
        pairs: list[tuple[Ref, float]] = []
        unmapped: list[str] = []
        for conversion in entry.conversions:
            unit, name = units.get(conversion.unit_id, (None, conversion.unit_id))
            if unit is None:
                unmapped.append(name)
                continue
            pairs.append((local_ref(unit, ctx.locale), float(conversion.grams)))
        fields = ingredient_fields(entry, category, family, sorted_conversions(pairs))
        return fields, sorted(set(unmapped), key=str.casefold)

    # ── Accepting and dismissing ─────────────────────────────────────

    async def _one(
        self, actor: User, peer_public_id: str, kind: MappingKind, source_id: str, name: str
    ) -> tuple[_Context, PeerSuggestion]:
        if kind.value not in CatalogueFile.allowed_kinds(actor):
            raise PermissionDeniedError(
                "Ingredients need manage:ingredients and write:ingredients; units, tags "
                "and equipment need write:resources."
            )
        peer = await self._peer(peer_public_id)
        mapping = await self._mirrors.mapping(peer.id, kind, source_id)
        if mapping is None or mapping.action is not MappingAction.MAP or mapping.local_id is None:
            raise PeerMappingNotFoundError(
                "The paired instance has no entry mapped to this catalogue here."
            )
        ctx = await self._context(actor)
        for s in await self._for_peer(ctx, peer, None, only=(kind, source_id)):
            if s.field == name:
                return ctx, s
        raise PeerSuggestionNotFoundError("The paired instance offers no other value here.")

    async def accept(
        self, actor: User, peer_public_id: str, kind: MappingKind, source_id: str, name: str
    ) -> None:
        """Writes the peer's value of the field into the local entry."""
        ctx, found = await self._one(actor, peer_public_id, kind, source_id, name)
        await self._writer.write(
            actor,
            kind.value,
            found.local,
            {name: found.suggested},
            ctx.lookups,
            resolve_local,
        )
        await self._uow.commit()

    async def dismiss(
        self, actor: User, peer_public_id: str, kind: MappingKind, source_id: str, name: str
    ) -> None:
        """Hides the suggestion until the peer offers another value."""
        _, found = await self._one(actor, peer_public_id, kind, source_id, name)
        await self._mirrors.save_dismissal(
            SuggestionDismissal(
                peer_id=found.peer.id,
                kind=kind,
                remote_id=source_id,
                field=name,
                value_hash=found.offered_hash,
                dismissed_at=now_utc(),
            )
        )
        await self._uow.commit()


def _joined(offered: Fields, current: Fields) -> Fields:
    """The peer's fields with other names and conversions as what they add
    to the local entry: the joined alias lists and the local conversions
    with the peer's added or changed. Nothing the peer leaves out is
    proposed for removal."""
    joined = dict(offered)
    for name, value in offered.items():
        if name.startswith("aliases.") and value:
            joined[name] = clean_list([*(current.get(name) or []), *value])
        elif name == "conversions" and value:
            merged = {ref.key: (ref, grams) for ref, grams in current.get(name) or ()}
            for ref, grams in value:
                merged[ref.key] = (ref, grams)
            joined[name] = sorted_conversions(list(merged.values()))
    return joined
