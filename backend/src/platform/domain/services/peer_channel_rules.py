"""
The rules of a peer channel: the event types, the retry schedule that never
gives up, the timers, and what a receiver does with a sequence number.
"""

import re
from datetime import datetime
from datetime import timedelta
from enum import Enum

# The events of a peer channel. Item events are content agnostic and name
# the item's kind (`recipe`), so the transport never names a cookbook
# concept.
ITEM_SHARED = "item.shared"
ITEM_UPDATED = "item.updated"
ITEM_WITHDRAWN = "item.withdrawn"
PEER_UPDATED = "peer.updated"
PEER_REVOKED = "peer.revoked"
PING = "ping"
ITEM_EVENTS = frozenset({ITEM_SHARED, ITEM_UPDATED, ITEM_WITHDRAWN})
CONTROL_EVENTS = frozenset({PEER_UPDATED, PING})
EVENT_TYPES = ITEM_EVENTS | CONTROL_EVENTS | {PEER_REVOKED}
# The kind of a control event's log entry; its id is the event type, so a
# newer ping replaces an older one.
CONTROL_KIND = ""

KIND_MAX = 64
ITEM_ID_MAX = 128
REVISION_MAX = 128
# Item kinds and ids appear in signed request paths, so they are limited to
# characters that need no escaping there.
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
# The largest item content a receiver accepts from a peer.
ITEM_MAX_BYTES = 64 * 1024 * 1024

# The waits after the 1st, 2nd, ... failed attempt; after the last one the
# sender keeps trying every `RETRY_FOREVER_EVERY`. A peer channel never
# gives up and is never switched off.
RETRY_DELAYS = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=30),
    timedelta(hours=2),
)
RETRY_FOREVER_EVERY = timedelta(hours=1)

# Every instance asks each peer for changes on this timer, whether or not
# events arrive, and compares the full list once a day.
CATCH_UP_EVERY = timedelta(minutes=15)
RECONCILE_EVERY = timedelta(hours=24)
PING_EVERY = timedelta(hours=24)

# How many entries one `/changes` answer carries; the receiver asks again
# from the last one while `more` is set.
CHANGES_PAGE = 500
# How many events the sender sends to one peer in one run.
SEND_BATCH = 50
# A lease longer than any run, after which another worker may take over
# from one that died.
LEASE = timedelta(minutes=5)


def is_token(value: object, limit: int) -> bool:
    """Whether the value can be an item kind or id: a short string of
    letters, digits and `._:-`."""
    return isinstance(value, str) and len(value) <= limit and _TOKEN.fullmatch(value) is not None


def retry_after(attempts: int, now: datetime) -> datetime:
    """When to try again after `attempts` failed attempts in a row."""
    if 1 <= attempts <= len(RETRY_DELAYS):
        return now + RETRY_DELAYS[attempts - 1]
    return now + RETRY_FOREVER_EVERY


class SequenceStep(Enum):
    # The event follows what was processed: apply it.
    APPLY = "apply"
    # Something was missed (a gap), or the event is not newer than what was
    # processed (a duplicate, or the source was restored from a backup):
    # ask the source what changed since the last processed sequence.
    CATCH_UP = "catch_up"


def sequence_step(last: int, seq: int, prev_seq: int) -> SequenceStep:
    """What a receiver that processed up to `last` does with event `seq`,
    whose predecessor in the sender's log was `prev_seq`. The log keeps
    only the latest event per item, so sequence numbers have holes and the
    sender names the predecessor instead."""
    if seq <= last or prev_seq > last:
        return SequenceStep.CATCH_UP
    return SequenceStep.APPLY


def source_was_restored(last: int, max_seq: int) -> bool:
    """A source whose highest sequence is below what this side already
    processed was restored from a backup: the receiver reconciles fully."""
    return max_seq < last
