from datetime import datetime
from typing import Any
from typing import Protocol

from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer_channel import PeerChannelEvent
from src.platform.domain.entities.peer_channel import PeerChannelState
from src.platform.domain.entities.peer_channel import PeerInboxJob


class IPeerChannelRepository(Protocol):
    async def state(self, peer: Peer) -> PeerChannelState:
        """The channel state of the peer, created when missing and started
        afresh when it belongs to an earlier pairing."""
        ...

    async def states(self, peer_ids: list[int]) -> dict[int, PeerChannelState]:
        """The stored states of these peers, without creating any."""
        ...

    async def update_state(self, peer_id: int, values: dict[str, Any]) -> None:
        """Writes the named columns of the state and nothing else, so the
        sender, the receiver and the timers never overwrite each other."""
        ...

    async def next_seq(self, peer: Peer) -> int:
        """Gives out the next sequence number of the peer's channel. Two
        callers at once get different numbers."""
        ...

    async def record(self, event: PeerChannelEvent) -> None:
        """Writes the event as the latest of its item, replacing the one
        before it."""
        ...

    async def events_after(self, peer_id: int, seq: int, *, limit: int) -> list[PeerChannelEvent]:
        """Log entries with a sequence above `seq`, in sequence order."""
        ...

    async def item_events_after(
        self, peer_id: int, seq: int, *, limit: int
    ) -> list[PeerChannelEvent]:
        """Like `events_after`, without control events."""
        ...

    async def item_events(self, peer_id: int, kind: str) -> list[PeerChannelEvent]:
        """Every item log entry of one kind."""
        ...

    async def item_states(self, kind: str, item_id: str) -> dict[int, PeerChannelEvent]:
        """Per peer, the latest log entry of one item: what each peer was
        last told about it."""
        ...

    async def count_after(self, peer_id: int, seq: int) -> int: ...

    async def due_to_send(self, now: datetime) -> list[int]:
        """Peers with events their peer has not accepted yet whose next
        attempt is due."""
        ...

    async def claim(self, peer_id: int, lease: str, now: datetime, until: datetime) -> bool:
        """Takes the `send` or `receive` lease of a channel unless another
        worker holds it. True when this caller took it."""
        ...

    async def release(self, peer_id: int, lease: str) -> None: ...

    async def claim_timer(self, peer_id: int, timer: str, now: datetime, next_at: datetime) -> bool:
        """Moves a due timer (`catch_up`, `reconcile` or `ping`) on to
        `next_at`, unless another worker did. True when this caller did."""
        ...

    async def due_timers(self, timer: str, now: datetime) -> list[int]:
        """Peers whose timer is due."""
        ...

    async def add_job(self, job: PeerInboxJob) -> None: ...

    async def due_jobs(self, now: datetime) -> list[int]:
        """Peers whose oldest queued event is due."""
        ...

    async def jobs(self, peer_id: int, *, limit: int) -> list[PeerInboxJob]:
        """The queued events of a peer, in the order they arrived."""
        ...

    async def save_job(self, job: PeerInboxJob) -> None: ...
    async def delete_job(self, job: PeerInboxJob) -> None: ...
    async def count_jobs(self, peer_id: int) -> int: ...
    async def has_job(self, peer_id: int, type: str) -> bool:
        """Whether a queued event of this type without a sequence exists."""
        ...

    async def purge(self, peer_id: int) -> None:
        """Deletes the channel state, the log and the queue of the peer."""
        ...
