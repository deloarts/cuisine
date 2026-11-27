"""
The source side of a peer channel: what a paired instance may ask about the
items this instance shares with it, and the daily repair of the channel
log.

`/changes?since=n` answers from the channel log, which holds the latest
event per item, so many updates of one item collapse into its latest
revision and a withdrawn item appears as a tombstone. `/items/{kind}/{id}`
asks the provider registered for the kind, which checks at fetch time that
the item is still shared with the caller; anything else answers as
withdrawn.

The repair compares, once a day, what each provider says is shared with a
peer with the channel log and publishes what differs, so a change that was
never published (or a log restored from a backup) does not drift forever.
"""

from dataclasses import dataclass

from src.platform.application.services.peer_channel import PeerChannel
from src.platform.application.services.peering_messages import changes_message
from src.platform.domain.entities.peer import Peer
from src.platform.domain.services.peer_channel_rules import CHANGES_PAGE
from src.platform.domain.services.peer_channel_rules import ITEM_SHARED
from src.platform.domain.services.peer_channel_rules import ITEM_UPDATED
from src.platform.domain.services.peer_channel_rules import ITEM_WITHDRAWN
from src.platform.ports.outbound.peer_content import IPeerContentProvider
from src.platform.ports.outbound.peer_content import PeerItem
from src.platform.ports.outbound.repositories.peer_channel_repository import IPeerChannelRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork


@dataclass(frozen=True)
class ItemAnswer:
    # None when the item is not shared with the caller.
    item: PeerItem | None
    # The caller's copy is current.
    not_modified: bool = False


def etag_matches(header: str | None, etag: str) -> bool:
    """Whether an `If-None-Match` header names the etag, weak or strong."""
    if not header or not etag:
        return False
    wanted = {part.strip().removeprefix("W/") for part in header.split(",")}
    return "*" in wanted or etag.removeprefix("W/") in wanted


class AnswerPeerChannel:
    def __init__(
        self,
        *,
        channels: IPeerChannelRepository,
        providers: dict[str, IPeerContentProvider],
        uow: IUnitOfWork,
    ) -> None:
        self._channels = channels
        self._providers = providers
        self._uow = uow

    async def changes(self, peer: Peer, since: int) -> dict[str, object]:
        state = await self._channels.state(peer)
        await self._uow.commit()
        events = await self._channels.item_events_after(peer.id, since, limit=CHANGES_PAGE)
        return changes_message(since, state.out_seq, events)

    async def item(
        self, peer: Peer, kind: str, item_id: str, *, if_none_match: str | None
    ) -> ItemAnswer:
        provider = self._providers.get(kind)
        if provider is None:
            return ItemAnswer(item=None)
        found = await provider.fetch(peer, item_id)
        if found is None:
            return ItemAnswer(item=None)
        if etag_matches(if_none_match, found.etag):
            return ItemAnswer(item=found, not_modified=True)
        return ItemAnswer(item=found)


class RepairPeerChannel:
    def __init__(
        self,
        *,
        channels: IPeerChannelRepository,
        channel: PeerChannel,
        providers: dict[str, IPeerContentProvider],
        uow: IUnitOfWork,
    ) -> None:
        self._channels = channels
        self._channel = channel
        self._providers = providers
        self._uow = uow

    async def repair(self, peer: Peer) -> int:
        """Publishes what the log is missing or has wrong; returns how many
        events it published."""
        published = 0
        for kind, provider in sorted(self._providers.items()):
            shared = {s.item_id: s.revision for s in await provider.shared_with(peer)}
            logged = {e.item_id: e for e in await self._channels.item_events(peer.id, kind)}
            for item_id, revision in sorted(shared.items()):
                entry = logged.get(item_id)
                if entry is None or entry.type == ITEM_WITHDRAWN:
                    await self._channel.publish(peer.id, ITEM_SHARED, kind, item_id, revision)
                    published += 1
                elif entry.revision != revision:
                    await self._channel.publish(peer.id, ITEM_UPDATED, kind, item_id, revision)
                    published += 1
            for item_id, entry in sorted(logged.items()):
                if entry.type != ITEM_WITHDRAWN and item_id not in shared:
                    await self._channel.publish(peer.id, ITEM_WITHDRAWN, kind, item_id, None)
                    published += 1
        await self._uow.commit()
        return published
