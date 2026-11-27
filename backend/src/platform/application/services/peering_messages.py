"""
The messages of peering protocol version 1 as stdlib dataclasses: the
contract other instances rely on. `scripts/export_formats.py` writes their
JSON Schemas to `formats/cuisine-peering.v1.<message>.schema.json`, and CI
fails when a schema and these classes disagree.

The handshake and `/hello` are built and read by `peering_identity.py`;
the channel messages (an event and the answer to `/changes`) are built and
read here. Readers ignore fields they do not know, so a newer release of
the same protocol version may add fields.
"""

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from src.platform.domain.entities.peer_channel import PeerChannelEvent
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.services.peer_channel_rules import CHANGES_PAGE
from src.platform.domain.services.peer_channel_rules import CONTROL_KIND
from src.platform.domain.services.peer_channel_rules import ITEM_EVENTS
from src.platform.domain.services.peer_channel_rules import ITEM_ID_MAX
from src.platform.domain.services.peer_channel_rules import KIND_MAX
from src.platform.domain.services.peer_channel_rules import REVISION_MAX
from src.platform.domain.services.peer_channel_rules import is_token

PROTOCOL_NAME = "cuisine-peering"


@dataclass(frozen=True)
class HandshakeRequestV1:
    """POST /handshake: the accepting instance's identity, the invitation
    code and the secret the inviting instance shall sign its requests
    with."""

    instance_id: str
    name: str
    base_url: str
    protocol_versions: list[int]
    code: str
    secret: str
    app_version: str = ""
    formats: dict[str, list[int]] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HelloResponseV1:
    """GET /hello: the answering instance's identity, supported versions
    and capabilities, and the versions negotiated with the caller."""

    instance_id: str
    name: str
    base_url: str
    protocol_versions: list[int]
    protocol_version: int
    format_versions: dict[str, int]
    app_version: str = ""
    formats: dict[str, list[int]] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HandshakeResponseV1:
    """The answer to POST /handshake: the inviting instance's identity, the
    negotiated versions and the secret the accepting instance shall sign
    its requests with."""

    instance_id: str
    name: str
    base_url: str
    protocol_versions: list[int]
    protocol_version: int
    format_versions: dict[str, int]
    secret: str
    app_version: str = ""
    formats: dict[str, list[int]] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PeerUpdateV1:
    """What changed about the sending instance, carried by `peer.updated`."""

    app_version: str = ""
    protocol_versions: list[int] = field(default_factory=list)
    formats: dict[str, list[int]] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EventV1:
    """POST /events: one thin event of a peer channel. Item events
    (`item.shared`, `item.updated`, `item.withdrawn`) name the item's kind,
    id and revision; the receiver fetches the content itself. `seq` only
    grows; `prev_seq` is the sequence of the event before it in the
    sender's log, so the receiver can tell a gap from the holes that
    collapsing updates leaves."""

    type: str
    seq: int
    prev_seq: int
    kind: str | None = None
    id: str | None = None
    revision: str | None = None
    peer: PeerUpdateV1 | None = None


@dataclass(frozen=True)
class ChangeV1:
    """The latest state of one item: shared or updated with its revision,
    or withdrawn as a tombstone."""

    type: str
    kind: str
    id: str
    seq: int
    revision: str | None = None


@dataclass(frozen=True)
class ChangesResponseV1:
    """GET /changes?since=n: the latest state of every item with a sequence
    above n, in sequence order, and the channel's highest sequence. While
    `more` is set, ask again from the last entry's sequence."""

    since: int
    max_seq: int
    more: bool
    changes: list[ChangeV1] = field(default_factory=list)


# Every message of protocol version 1, by the name its schema file carries.
MESSAGES_V1: dict[str, type] = {
    "handshake-request": HandshakeRequestV1,
    "handshake-response": HandshakeResponseV1,
    "hello-response": HelloResponseV1,
    "event": EventV1,
    "changes-response": ChangesResponseV1,
}
PROTOCOL_MESSAGES: dict[int, dict[str, type]] = {1: MESSAGES_V1}


def event_message(event: PeerChannelEvent, prev_seq: int) -> dict[str, Any]:
    control = event.kind == CONTROL_KIND
    peer = PeerUpdateV1(**event.data) if control and event.data else None
    return asdict(
        EventV1(
            type=event.type,
            seq=event.seq,
            prev_seq=prev_seq,
            kind=None if control else event.kind,
            id=None if control else event.item_id,
            revision=event.revision,
            peer=peer,
        )
    )


def changes_message(
    since: int, max_seq: int, events: list[PeerChannelEvent], *, page: int = CHANGES_PAGE
) -> dict[str, Any]:
    return asdict(
        ChangesResponseV1(
            since=since,
            max_seq=max_seq,
            more=len(events) >= page,
            changes=[
                ChangeV1(type=e.type, kind=e.kind, id=e.item_id, seq=e.seq, revision=e.revision)
                for e in events
            ],
        )
    )


def _bad(what: str) -> InvalidPeerConfigurationError:
    return InvalidPeerConfigurationError(f"The other instance sent an invalid {what}.")


def _count(value: Any, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _bad(what)
    return value


def _text(value: Any, limit: int, what: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value or len(value) > limit:
        raise _bad(what)
    return value


def _token(value: Any, limit: int, what: str) -> str:
    if not is_token(value, limit):
        raise _bad(what)
    assert isinstance(value, str)
    return value


def read_event(data: Any) -> EventV1:
    """Reads an event. Raises InvalidPeerConfigurationError for a missing or
    malformed field; an unknown type is kept, for the caller to ignore."""
    if not isinstance(data, dict):
        raise _bad("event")
    kind_name = _text(data.get("type"), 64, "event type")
    assert kind_name is not None
    seq = _count(data.get("seq"), "sequence number")
    prev_seq = _count(data.get("prev_seq", 0), "sequence number")
    if prev_seq >= seq:
        raise _bad("sequence number")
    kind = item_id = revision = None
    if kind_name in ITEM_EVENTS:
        kind = _token(data.get("kind"), KIND_MAX, "item kind")
        item_id = _token(data.get("id"), ITEM_ID_MAX, "item id")
        revision = _text(data.get("revision"), REVISION_MAX, "revision", optional=True)
    peer = data.get("peer")
    update = None
    if isinstance(peer, dict):
        update = PeerUpdateV1(
            app_version=str(peer.get("app_version", ""))[:64],
            capabilities=[
                str(c)[:64] for c in peer.get("capabilities") or [] if isinstance(c, str)
            ][:64],
        )
    return EventV1(
        type=kind_name,
        seq=seq,
        prev_seq=prev_seq,
        kind=kind,
        id=item_id,
        revision=revision,
        peer=update,
    )


def read_changes(data: Any) -> ChangesResponseV1:
    """Reads the answer to `/changes`. Entries of an unknown type are left
    out; a malformed answer raises InvalidPeerConfigurationError."""
    if not isinstance(data, dict):
        raise _bad("list of changes")
    since = _count(data.get("since"), "list of changes")
    max_seq = _count(data.get("max_seq"), "list of changes")
    raw = data.get("changes")
    if not isinstance(raw, list):
        raise _bad("list of changes")
    changes: list[ChangeV1] = []
    for entry in raw:
        if not isinstance(entry, dict) or entry.get("type") not in ITEM_EVENTS:
            continue
        kind = _token(entry.get("kind"), KIND_MAX, "item kind")
        item_id = _token(entry.get("id"), ITEM_ID_MAX, "item id")
        changes.append(
            ChangeV1(
                type=str(entry["type"]),
                kind=kind,
                id=item_id,
                seq=_count(entry.get("seq"), "sequence number"),
                revision=_text(entry.get("revision"), REVISION_MAX, "revision", optional=True),
            )
        )
    return ChangesResponseV1(
        since=since, max_seq=max_seq, more=bool(data.get("more")), changes=changes
    )
