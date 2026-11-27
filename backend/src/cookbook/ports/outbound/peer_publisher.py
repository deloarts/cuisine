"""
Telling paired instances about recipes, seen from the cookbook. Platform's
peer channel fulfils it (`Platform.peer_channel`): an event is written in
the transaction of the change and sent by Platform's worker afterwards.
"""

from typing import Protocol


class IPeerPublisher(Protocol):
    async def publish(
        self, peer_id: int, type: str, kind: str, item_id: str, revision: str | None
    ) -> bool:
        """Queues `item.shared`, `item.updated` or `item.withdrawn` for one
        peer; False when the peer is not actively paired."""
        ...

    async def last_published(self, kind: str, item_id: str) -> dict[int, tuple[str, str | None]]:
        """Per peer, the type and revision of the latest event about the
        item."""
        ...

    async def published_items(self, peer_id: int, kind: str) -> dict[str, tuple[str, str | None]]:
        """Per item of the kind, the type and revision of the latest event
        published to the peer."""
        ...
