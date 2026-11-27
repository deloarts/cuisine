"""
Publishes events to peer channels. A use case calls it inside its own
transaction when an item it shares with a peer changes or stops being
shared, so the event exists exactly when the change was committed, like a
webhook delivery. The channel worker sends it afterwards and keeps trying
until the peer takes it.

Each event gets the next sequence number of the peer's channel and replaces
the previous event of the same item in the channel log, so only the latest
state of an item is ever sent. Publishing to a revoked or unknown peer is a
no-op. The peering feature switch does not stop publishing, only sending:
switched on again, a channel sends what changed in the meantime.
"""

from typing import Any

from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer_channel import PeerChannelEvent
from src.platform.domain.services.peer_channel_rules import CONTROL_KIND
from src.platform.domain.services.peer_channel_rules import ITEM_EVENTS
from src.platform.domain.services.peer_channel_rules import ITEM_ID_MAX
from src.platform.domain.services.peer_channel_rules import KIND_MAX
from src.platform.domain.services.peer_channel_rules import PEER_UPDATED
from src.platform.domain.services.peer_channel_rules import PING
from src.platform.domain.services.peer_channel_rules import REVISION_MAX
from src.platform.domain.services.peer_channel_rules import is_token
from src.platform.ports.outbound.repositories.peer_channel_repository import IPeerChannelRepository
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.shared_kernel.domain.services.clock import now_utc


class PeerChannel:
    def __init__(self, *, peers: IPeerRepository, channels: IPeerChannelRepository) -> None:
        self._peers = peers
        self._channels = channels

    async def publish(
        self, peer_id: int, type: str, kind: str, item_id: str, revision: str | None
    ) -> bool:
        """Queues an item event (`item.shared`, `item.updated` or
        `item.withdrawn`) for one peer. The caller commits. False when the
        peer is not actively paired."""
        if type not in ITEM_EVENTS:
            raise ValueError(f"{type!r} is not an item event.")
        if not is_token(kind, KIND_MAX) or not is_token(item_id, ITEM_ID_MAX):
            raise ValueError("An item event needs a kind and an id of letters, digits and ._:-.")
        if revision is not None and len(revision) > REVISION_MAX:
            raise ValueError("The revision is too long.")
        peer = await self._peers.get(peer_id)
        if peer is None or not peer.active:
            return False
        await self._record(peer, type, kind, item_id, revision, {})
        return True

    async def publish_to(
        self, peer_ids: list[int], type: str, kind: str, item_id: str, revision: str | None
    ) -> int:
        """`publish` for every peer the item is shared with; returns how many
        channels got the event."""
        made = 0
        for peer_id in sorted(set(peer_ids)):
            made += int(await self.publish(peer_id, type, kind, item_id, revision))
        return made

    async def last_published(self, kind: str, item_id: str) -> dict[int, tuple[str, str | None]]:
        """Per peer, the type and revision of the latest event published
        about one item, so a caller can tell what each peer holds now and
        publish only what changed."""
        return {
            peer_id: (event.type, event.revision)
            for peer_id, event in (await self._channels.item_states(kind, item_id)).items()
        }

    async def published_items(self, peer_id: int, kind: str) -> dict[str, tuple[str, str | None]]:
        """Per item of one kind, the type and revision of the latest event
        published to the peer."""
        return {
            event.item_id: (event.type, event.revision)
            for event in await self._channels.item_events(peer_id, kind)
        }

    async def publish_control(self, peer: Peer, type: str, data: dict[str, Any]) -> None:
        """Queues `peer.updated` or `ping`; a newer one replaces an older one
        that was not sent yet."""
        if type not in (PEER_UPDATED, PING):
            raise ValueError(f"{type!r} is not a control event.")
        if peer.active:
            await self._record(peer, type, CONTROL_KIND, type, None, data)

    async def _record(
        self,
        peer: Peer,
        type: str,
        kind: str,
        item_id: str,
        revision: str | None,
        data: dict[str, Any],
    ) -> None:
        seq = await self._channels.next_seq(peer)
        await self._channels.record(
            PeerChannelEvent(
                peer_id=peer.id,
                seq=seq,
                type=type,
                kind=kind,
                item_id=item_id,
                revision=revision,
                data=data,
                created=now_utc(),
            )
        )
