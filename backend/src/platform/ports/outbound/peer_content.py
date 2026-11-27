"""
What travels over a peer channel, seen from Platform. Platform moves items
between paired instances without knowing what they are; another package
registers, per item kind, a provider that answers for the items this
instance shares and a consumer that takes in the items a peer shares
(`deps.register_peer_content`, from the composition root).

Both run on the session of the request or job that calls them. The
transport commits; a provider or consumer never does.
"""

from dataclasses import dataclass
from typing import Protocol

from src.platform.domain.entities.peer import Peer


@dataclass(frozen=True)
class SharedItem:
    item_id: str
    # Changes whenever the item's content for the peer changes, such as a
    # revision number.
    revision: str


@dataclass(frozen=True)
class PeerItem:
    item_id: str
    content: bytes
    media_type: str
    # A validator of the content: equal etags mean equal bytes.
    etag: str


class IPeerContentProvider(Protocol):
    """The source side of one item kind."""

    async def shared_with(self, peer: Peer) -> list[SharedItem]:
        """Every item of this kind currently shared with the peer. The
        daily repair compares it with the channel log and publishes what
        differs."""
        ...

    async def fetch(self, peer: Peer, item_id: str) -> PeerItem | None:
        """The item as the peer receives it, or None when it is not (or no
        longer) shared with the peer. Permission is checked here, at fetch
        time, whatever the channel log says."""
        ...


class IPeerContentConsumer(Protocol):
    """The receiving side of one item kind."""

    async def current_etag(self, peer: Peer, item_id: str) -> str | None:
        """The etag of the item as last applied from this peer, so an
        unchanged item is not fetched again; None when it is not held."""
        ...

    async def apply(self, peer: Peer, item: PeerItem) -> None:
        """Takes in a new or changed item from the peer."""
        ...

    async def withdraw(self, peer: Peer, item_id: str) -> None:
        """The peer no longer shares the item. A no-op when it is not
        held."""
        ...

    async def reconcile(self, peer: Peer, shared_ids: set[str]) -> None:
        """The full list of what the peer shares of this kind: withdraw
        every item from this peer that is not in it."""
        ...
