"""The rules of a peer channel: the retry schedule, the sequence decision,
restore detection, item tokens and the protocol message readers."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

from src.platform.application.services.peering_messages import read_changes
from src.platform.application.services.peering_messages import read_event
from src.platform.application.use_cases.peering.channel_source import etag_matches
from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.services.peer_channel_rules import SequenceStep
from src.platform.domain.services.peer_channel_rules import is_token
from src.platform.domain.services.peer_channel_rules import retry_after
from src.platform.domain.services.peer_channel_rules import sequence_step
from src.platform.domain.services.peer_channel_rules import source_was_restored

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


def test_retries_follow_the_schedule_and_then_go_on_hourly() -> None:
    waits = [retry_after(n, NOW) - NOW for n in range(1, 9)]
    assert waits == [
        timedelta(minutes=1),
        timedelta(minutes=5),
        timedelta(minutes=30),
        timedelta(hours=2),
        timedelta(hours=1),
        timedelta(hours=1),
        timedelta(hours=1),
        timedelta(hours=1),
    ]


@pytest.mark.parametrize(
    ("last", "seq", "prev", "step"),
    [
        (0, 1, 0, SequenceStep.APPLY),
        # Holes left by collapsed updates are no gap.
        (3, 7, 3, SequenceStep.APPLY),
        # Caught up beyond the predecessor by a timer.
        (5, 7, 3, SequenceStep.APPLY),
        # A gap: the predecessor was never processed.
        (3, 7, 5, SequenceStep.CATCH_UP),
        # A duplicate, or a restored source.
        (7, 7, 3, SequenceStep.CATCH_UP),
        (7, 2, 1, SequenceStep.CATCH_UP),
    ],
)
def test_the_sequence_decides_between_applying_and_catching_up(
    last: int, seq: int, prev: int, step: SequenceStep
) -> None:
    assert sequence_step(last, seq, prev) is step


def test_a_source_below_what_was_processed_was_restored() -> None:
    assert source_was_restored(10, 4)
    assert not source_was_restored(10, 10)
    assert not source_was_restored(0, 0)


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("recipe", True),
        ("0b9f6c1e-3a7d-4d1e-8f52-1c2b3a4d5e6f", True),
        ("a.b:c_d-e", True),
        ("", False),
        ("-leading", False),
        ("with space", False),
        ("slash/inside", False),
        ("x" * 65, False),
        (7, False),
    ],
)
def test_item_tokens_need_no_escaping(value: object, ok: bool) -> None:
    assert is_token(value, 64) is ok


def test_an_event_is_read_strictly_but_tolerates_unknown_fields() -> None:
    event = read_event(
        {
            "type": "item.updated",
            "seq": 4,
            "prev_seq": 2,
            "kind": "recipe",
            "id": "r1",
            "revision": "3",
            "future": True,
        }
    )
    assert (event.kind, event.id, event.revision) == ("recipe", "r1", "3")
    unknown = read_event({"type": "item.renamed", "seq": 5, "prev_seq": 4})
    assert unknown.type == "item.renamed"
    bad_events: list[object] = [
        {"type": "item.shared", "seq": 1, "prev_seq": 0, "kind": "recipe"},
        {"type": "item.shared", "seq": 1, "prev_seq": 0, "kind": "a b", "id": "x"},
        {"type": "ping", "seq": 2, "prev_seq": 2},
        {"type": "ping", "seq": -1},
        {"seq": 1},
        [],
    ]
    for bad in bad_events:
        with pytest.raises(InvalidPeerConfigurationError):
            read_event(bad)


def test_changes_skip_unknown_entries() -> None:
    changes = read_changes(
        {
            "since": 0,
            "max_seq": 9,
            "more": False,
            "changes": [
                {"type": "item.shared", "kind": "recipe", "id": "r1", "seq": 3, "revision": "1"},
                {"type": "item.renamed", "kind": "recipe", "id": "r2", "seq": 4},
                {"type": "item.withdrawn", "kind": "recipe", "id": "r3", "seq": 9},
            ],
        }
    )
    assert [(c.type, c.id) for c in changes.changes] == [
        ("item.shared", "r1"),
        ("item.withdrawn", "r3"),
    ]
    with pytest.raises(InvalidPeerConfigurationError):
        read_changes({"since": 0, "changes": []})


def test_if_none_match_compares_weak_and_strong_etags() -> None:
    assert etag_matches('"3"', '"3"')
    assert etag_matches('W/"3", "4"', '"3"')
    assert etag_matches("*", '"3"')
    assert not etag_matches('"2"', '"3"')
    assert not etag_matches(None, '"3"')
    assert not etag_matches('"3"', "")
