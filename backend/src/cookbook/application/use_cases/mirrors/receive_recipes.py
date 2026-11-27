"""
Taking in the recipes paired instances share with this one: the `recipe`
consumer of the peer channel, and what follows a revoke or a change of a
peer's switches. It never commits; the transport or the use case calling it
does.

A recipe that has no mirror here yet waits for an administrator (an
`IncomingRecipe`, with the payload and its images), unless the instance does
not accept recipes from that peer. An update of a mirror whose catalogue
entries all have a mapping is applied at once; one that brings an entry
without a mapping waits too, while the mirror keeps its previous revision.
A peer whose recipes are taken in without asking (`sync_all`) skips both
waits: every entry without a mapping gets the automatic decision
(`MirrorBuilder.decide_automatically`) and the recipe becomes a mirror, or
the update applies, at once. A rejected recipe stays rejected, whatever the
peer's switches: later updates refresh what is kept of it but do not queue
or accept it again. A withdrawn recipe removes the mirror and anything
waiting.
"""

from uuid import UUID

from src.cookbook.application.services.mirror_builder import MirrorBuilder
from src.cookbook.application.services.mirror_builder import read_payload
from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.domain.entities.mirror import IncomingKind
from src.cookbook.domain.entities.mirror import IncomingRecipe
from src.cookbook.domain.entities.mirror import IncomingStatus
from src.cookbook.domain.entities.mirror import RecipeMirror
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.ports.outbound.peer_content import PeerItem
from src.shared_kernel.domain.services.clock import now_utc


def _origin(item_id: str) -> UUID | None:
    try:
        return UUID(item_id)
    except ValueError:
        return None


class ReceivePeerRecipes:
    def __init__(
        self,
        *,
        mirror_repo: IMirrorRepository,
        recipe_repo: IRecipeRepository,
        builder: MirrorBuilder,
        sharing: PeerRecipeSharing,
    ) -> None:
        self._mirrors = mirror_repo
        self._recipes = recipe_repo
        self._builder = builder
        self._sharing = sharing

    # ── The consumer ─────────────────────────────────────────────────

    async def current_etag(self, peer: Peer, item_id: str) -> str | None:
        origin = _origin(item_id)
        if origin is None:
            return None
        waiting = await self._mirrors.incoming_by_origin(peer.id, origin)
        if waiting is not None and waiting.etag:
            return waiting.etag
        mirror = await self._mirrors.by_origin(peer.id, origin)
        return mirror.etag if mirror is not None and mirror.etag else None

    async def apply(self, peer: Peer, item: PeerItem) -> None:
        origin = _origin(item.item_id)
        if origin is None:
            return
        received = read_payload(item.content, item.item_id)
        mirror = await self._mirrors.by_origin(peer.id, origin)
        waiting = await self._mirrors.incoming_by_origin(peer.id, origin)
        if waiting is not None and waiting.status is IncomingStatus.REJECTED:
            # Kept current, so reopening it shows the latest version.
            await self._wait(peer, origin, received.entry, item, waiting, waiting.kind)
            return
        if mirror is None and not peer.accept_incoming:
            return
        if peer.sync_all:
            await self._builder.decide_automatically(peer, received)
        if mirror is None:
            if peer.sync_all:
                await self._builder.build(
                    peer, received, etag=item.etag, note=f"Accepted from {peer.name}"
                )
                if waiting is not None:
                    await self._mirrors.delete_incoming(waiting.id)
                return
            await self._builder.needs(peer, received, record=True)
            await self._wait(peer, origin, received.entry, item, waiting, IncomingKind.NEW)
            return
        if await self._builder.needs(peer, received, record=True):
            await self._wait(peer, origin, received.entry, item, waiting, IncomingKind.UPDATE)
            return
        await self._builder.build(peer, received, etag=item.etag, note=f"Updated from {peer.name}")
        if waiting is not None:
            await self._mirrors.delete_incoming(waiting.id)

    async def _wait(
        self,
        peer: Peer,
        origin: UUID,
        entry: object,
        item: PeerItem,
        waiting: IncomingRecipe | None,
        kind: IncomingKind,
    ) -> None:
        title = str(getattr(entry, "title", "") or "")
        author = getattr(entry, "author_name", None)
        now = now_utc()
        if waiting is None:
            waiting = IncomingRecipe(
                peer_id=peer.id,
                origin_public_id=origin,
                status=IncomingStatus.PENDING,
                kind=kind,
                title=title,
                author_name=author,
                etag=item.etag,
                payload=item.content,
                received_at=now,
            )
        else:
            waiting.kind = kind
            waiting.title = title
            waiting.author_name = author
            waiting.etag = item.etag
            waiting.payload = item.content
            if waiting.status is IncomingStatus.PENDING:
                waiting.received_at = now
        await self._mirrors.save_incoming(waiting)

    async def withdraw(self, peer: Peer, item_id: str) -> None:
        origin = _origin(item_id)
        if origin is None:
            return
        waiting = await self._mirrors.incoming_by_origin(peer.id, origin)
        if waiting is not None:
            await self._mirrors.delete_incoming(waiting.id)
        mirror = await self._mirrors.by_origin(peer.id, origin)
        if mirror is not None:
            await self._builder.remove(mirror)

    async def reconcile(self, peer: Peer, shared_ids: set[str]) -> None:
        shared = {i.lower() for i in shared_ids}
        held = {str(m.origin_public_id) for m in await self._mirrors.for_peer(peer.id)}
        held |= {
            str(i.origin_public_id) for i in await self._mirrors.incoming_list(peer_id=peer.id)
        }
        for item_id in sorted(held):
            if item_id.lower() not in shared:
                await self.withdraw(peer, item_id)

    # ── Hooks ────────────────────────────────────────────────────────

    async def peer_revoked(self, peer: Peer) -> None:
        """Every mirror, waiting recipe and catalogue mapping of the peer
        goes; copies made from its mirrors stay."""
        mirrors: list[RecipeMirror] = await self._mirrors.for_peer(peer.id)
        for mirror in mirrors:
            await self._builder.remove(mirror)
        await self._mirrors.purge_peer(peer.id)

    async def peer_changed(
        self, peer: Peer, changed: frozenset[str], gained: frozenset[str]
    ) -> None:
        if changed & {"mirror_visibility", "mirror_group"}:
            await self._builder.set_visibility(peer)
        if "users_may_share" in changed:
            await self._sharing.resync([peer.id])
        if gained:
            # Forgetting the etags makes the next comparison fetch every
            # recipe of the peer again, now that more of it can be shown.
            for mirror in await self._mirrors.for_peer(peer.id):
                mirror.etag = ""
                await self._mirrors.save(mirror)
            for waiting in await self._mirrors.incoming_list(peer_id=peer.id):
                waiting.etag = ""
                await self._mirrors.save_incoming(waiting)

    async def peer_paired(self, peer: Peer) -> None:
        """A new pairing, or one after a revoke: the peer gets every recipe
        it should hold at once (every peers and public recipe, since nothing
        is shared with it explicitly yet)."""
        await self._sharing.announce(peer)

    async def privacy_saved(self, before: PrivacySettings, after: PrivacySettings) -> None:
        if before.allow_public_recipes != after.allow_public_recipes:
            await self._sharing.resync()

    async def features_saved(self, before: FeatureSettings, after: FeatureSettings) -> None:
        """Peers recipes go to paired instances only while peering is on."""
        if before.peering != after.peering:
            await self._sharing.resync()
