"""
The administrator's side of mirrors: the recipes from paired instances that
wait for a decision, accepting them with a decision for every catalogue
entry without a mapping, rejecting and reopening them, and the catalogue
mappings per peer with their correction. The routes check read:settings or
write:settings and the peering switch; nothing here is offered to users.

Accepting builds the mirror (or applies the held update) in one
transaction; it refuses with 422 `PeerMappingError` while an entry still
lacks a decision, naming the missing ones. Each recipe is accepted on its
own: a recipe using a sub-recipe that is not mirrored yet shows that line
as not available and links it once the sub-recipe is accepted. A rejected
recipe stays rejected until an administrator reopens or accepts it.
"Accept everything that waits" accepts every pending recipe of one peer
with the automatic decisions of `sync_all`, leaving rejected ones alone.
Correcting a mapping rebuilds every mirror of that peer that uses the entry.
"""

from dataclasses import dataclass

from src.cookbook.application.services._exchange import first_name
from src.cookbook.application.services._exchange import parse_uuid
from src.cookbook.application.services.mirror_builder import MappingDecision
from src.cookbook.application.services.mirror_builder import MirrorBuilder
from src.cookbook.application.services.mirror_builder import NeededEntry
from src.cookbook.application.services.mirror_builder import read_document
from src.cookbook.application.services.mirror_builder import read_payload
from src.cookbook.application.services.mirror_builder import used_records
from src.cookbook.domain.entities.mirror import CatalogueMapping
from src.cookbook.domain.entities.mirror import IncomingRecipe
from src.cookbook.domain.entities.mirror import IncomingStatus
from src.cookbook.domain.entities.mirror import MappingAction
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import IncomingRecipeNotFoundError
from src.cookbook.domain.exceptions import PeerMappingError
from src.cookbook.domain.exceptions import PeerMappingNotFoundError
from src.cookbook.domain.exceptions import RecipeArchiveError
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.platform.domain.entities.peer import Peer
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import PeerNotFoundError
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

_SECTIONS = {
    MappingKind.UNIT: "units",
    MappingKind.TAG: "tags",
    MappingKind.INGREDIENT: "ingredients",
    MappingKind.EQUIPMENT: "equipment",
}


@dataclass(frozen=True)
class SubRecipeNeed:
    """A sub-recipe the waiting recipe uses: its title when the peer shares
    it with this instance too, and whether it is mirrored or waiting here."""

    source_id: str
    title: str | None
    mirrored: bool
    waiting: bool


@dataclass(frozen=True)
class IncomingView:
    item: IncomingRecipe
    peer: Peer
    entries: list[NeededEntry]
    sub_recipes: list[SubRecipeNeed]
    # The mirror a held update belongs to.
    mirror_id: str | None
    description: str


@dataclass(frozen=True)
class MappingView:
    mapping: CatalogueMapping
    target_id: str | None
    target_name: str | None
    # How many mirrors of the peer name the entry.
    used_by: int


class ManageIncomingRecipes:
    def __init__(
        self,
        *,
        mirror_repo: IMirrorRepository,
        recipe_repo: IRecipeRepository,
        peer_repo: IPeerRepository,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        builder: MirrorBuilder,
        uow: IUnitOfWork,
    ) -> None:
        self._mirrors = mirror_repo
        self._recipes = recipe_repo
        self._peers = peer_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._builder = builder
        self._uow = uow

    # ── Waiting recipes ──────────────────────────────────────────────

    async def _item(self, public_id: str) -> tuple[IncomingRecipe, Peer]:
        item = await self._mirrors.incoming(public_id)
        peer = await self._peers.get(item.peer_id) if item is not None else None
        if item is None or peer is None:
            raise IncomingRecipeNotFoundError(
                "No recipe from another instance waits under this id."
            )
        return item, peer

    async def _view(self, item: IncomingRecipe, peer: Peer) -> IncomingView:
        received = read_payload(item.payload, str(item.origin_public_id))
        content = received.entry.snapshot
        subs: list[SubRecipeNeed] = []
        for source_id in dict.fromkeys(
            line.sub_recipe_id
            for step in content.steps
            for line in step.ingredients
            if line.sub_recipe_id
        ):
            titles = content.names.recipes.get(source_id) or {}
            origin = parse_uuid(source_id)
            mirrored = origin is not None and await self._mirrors.by_origin(peer.id, origin)
            waiting = origin is not None and await self._mirrors.incoming_by_origin(peer.id, origin)
            subs.append(
                SubRecipeNeed(
                    source_id=source_id,
                    title=first_name(titles, content.original_locale) or None,
                    mirrored=bool(mirrored),
                    waiting=bool(waiting),
                )
            )
        mirror = await self._mirrors.by_origin(peer.id, item.origin_public_id)
        mirror_recipe = await self._recipes.get(mirror.recipe_id) if mirror else None
        text = content.translations.get(content.original_locale)
        return IncomingView(
            item=item,
            peer=peer,
            entries=await self._builder.needs(peer, received, record=False),
            sub_recipes=subs,
            mirror_id=str(mirror_recipe.public_id) if mirror_recipe else None,
            description=text.description if text else "",
        )

    async def waiting(self, status: IncomingStatus | None = None) -> list[IncomingView]:
        views = []
        for item in await self._mirrors.incoming_list(status):
            peer = await self._peers.get(item.peer_id)
            if peer is not None and peer.active:
                views.append(await self._view(item, peer))
        return views

    async def get(self, public_id: str) -> IncomingView:
        item, peer = await self._item(public_id)
        return await self._view(item, peer)

    async def accept(self, public_id: str, decisions: list[MappingDecision]) -> Recipe:
        """Saves the decisions for the entries the recipe needs, then builds
        the mirror or applies the held update. A rejected recipe may be
        accepted too, which undoes the rejection."""
        item, peer = await self._item(public_id)
        if not peer.active:
            raise InvalidPeerConfigurationError("The pairing with this instance is revoked.")
        received = read_payload(item.payload, str(item.origin_public_id))
        wanted = {(d.kind, d.remote_id): d for d in decisions}
        for needed in await self._builder.needs(peer, received, record=True):
            decision = wanted.get((needed.kind, needed.remote_id))
            if decision is not None:
                await self._builder.decide(peer, received, decision)
        missing = await self._builder.needs(peer, received, record=False)
        if missing:
            raise PeerMappingError(
                "Decide for every catalogue entry of the recipe first.",
                missing=[f"{e.kind.value}:{e.remote_id}" for e in missing],
            )
        recipe = await self._builder.build(
            peer, received, etag=item.etag, note=f"Accepted from {peer.name}"
        )
        await self._mirrors.delete_incoming(item.id)
        await self._uow.commit()
        return recipe

    async def accept_waiting(self, peer_public_id: str) -> int:
        """Accepts every recipe of the peer that waits now, with the
        automatic decisions a peer with `sync_all` gets, in one transaction;
        rejected recipes stay rejected. A payload that cannot be read stays
        waiting. Answers how many recipes were accepted."""
        peer = await self._peer(peer_public_id)
        if not peer.active:
            raise InvalidPeerConfigurationError("The pairing with this instance is revoked.")
        accepted = 0
        for item in await self._mirrors.incoming_list(IncomingStatus.PENDING, peer_id=peer.id):
            try:
                received = read_payload(item.payload, str(item.origin_public_id))
            except RecipeArchiveError:
                continue
            await self._builder.decide_automatically(peer, received)
            await self._builder.build(
                peer, received, etag=item.etag, note=f"Accepted from {peer.name}"
            )
            await self._mirrors.delete_incoming(item.id)
            accepted += 1
        await self._uow.commit()
        return accepted

    async def reject(self, public_id: str) -> IncomingView:
        """Discards the recipe. It stays rejected: updates from the peer
        refresh what is kept of it but do not ask again."""
        item, peer = await self._item(public_id)
        item.status = IncomingStatus.REJECTED
        item.decided_at = now_utc()
        saved = await self._mirrors.save_incoming(item)
        await self._uow.commit()
        return await self._view(saved, peer)

    async def reopen(self, public_id: str) -> IncomingView:
        """Puts a rejected recipe back into the queue."""
        item, peer = await self._item(public_id)
        item.status = IncomingStatus.PENDING
        item.decided_at = None
        saved = await self._mirrors.save_incoming(item)
        await self._uow.commit()
        return await self._view(saved, peer)

    # ── Mappings ─────────────────────────────────────────────────────

    async def _peer(self, public_id: str) -> Peer:
        peer = await self._peers.get_by_public_id(public_id)
        if peer is None:
            raise PeerNotFoundError("No such paired instance.")
        return peer

    async def _usage(self, peer: Peer) -> dict[tuple[MappingKind, str], int]:
        counts: dict[tuple[MappingKind, str], int] = {}
        for mirror in await self._mirrors.for_peer(peer.id):
            used = used_records(read_document(mirror.document))
            for kind, ids in (
                (MappingKind.UNIT, used.units),
                (MappingKind.TAG, used.tags),
                (MappingKind.INGREDIENT, used.ingredients),
                (MappingKind.EQUIPMENT, used.equipment),
            ):
                for remote_id in ids:
                    counts[(kind, remote_id)] = counts.get((kind, remote_id), 0) + 1
        return counts

    async def _targets(
        self, mappings: list[CatalogueMapping]
    ) -> dict[tuple[MappingKind, int], tuple[str, str]]:
        """The public id and name of every local entry the mappings name."""
        found: dict[tuple[MappingKind, int], tuple[str, str]] = {}
        ids = {
            kind: sorted(
                {
                    m.local_id
                    for m in mappings
                    if m.kind is kind and m.action is MappingAction.MAP and m.local_id
                }
            )
            for kind in MappingKind
        }
        for unit in await self._units.list_all():
            if unit.id in ids[MappingKind.UNIT]:
                found[(MappingKind.UNIT, unit.id)] = (str(unit.public_id), unit.code)
        for tag in await self._tags.list_all():
            if tag.id in ids[MappingKind.TAG]:
                found[(MappingKind.TAG, tag.id)] = (
                    str(tag.public_id),
                    first_name({k: v.name for k, v in tag.translations.items()}),
                )
        for ingredient in await self._ingredients.get_many(ids[MappingKind.INGREDIENT]):
            found[(MappingKind.INGREDIENT, ingredient.id)] = (
                str(ingredient.public_id),
                first_name(
                    {k: v.name for k, v in ingredient.translations.items()},
                    ingredient.original_locale,
                ),
            )
        for item in await self._equipment.get_many(ids[MappingKind.EQUIPMENT]):
            found[(MappingKind.EQUIPMENT, item.id)] = (
                str(item.public_id),
                first_name({k: v.name for k, v in item.translations.items()}),
            )
        return found

    async def _mapping_views(
        self, peer: Peer, mappings: list[CatalogueMapping]
    ) -> list[MappingView]:
        usage = await self._usage(peer)
        targets = await self._targets(mappings)
        views = []
        for mapping in mappings:
            target = (
                targets.get((mapping.kind, mapping.local_id))
                if mapping.local_id is not None
                else None
            )
            views.append(
                MappingView(
                    mapping=mapping,
                    target_id=target[0] if target else None,
                    target_name=target[1] if target else None,
                    used_by=usage.get((mapping.kind, mapping.remote_id), 0),
                )
            )
        return views

    async def mappings(self, peer_public_id: str) -> list[MappingView]:
        peer = await self._peer(peer_public_id)
        return await self._mapping_views(peer, await self._mirrors.mappings(peer.id))

    async def correct(self, peer_public_id: str, decision: MappingDecision) -> MappingView:
        """Changes one mapping of the peer and rebuilds every mirror of the
        peer that names the entry, in one transaction."""
        peer = await self._peer(peer_public_id)
        if await self._mirrors.mapping(peer.id, decision.kind, decision.remote_id) is None:
            raise PeerMappingNotFoundError("This instance never sent that catalogue entry.")
        mapping = await self._builder.decide(peer, None, decision)
        for mirror in await self._mirrors.for_peer(peer.id):
            used = used_records(read_document(mirror.document))
            if decision.remote_id in getattr(used, _SECTIONS[decision.kind]):
                await self._builder.rebuild(peer, mirror, note="Catalogue mapping changed")
        await self._uow.commit()
        return (await self._mapping_views(peer, [mapping]))[0]
