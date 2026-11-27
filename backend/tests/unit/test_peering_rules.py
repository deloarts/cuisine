"""The pure rules of peering: invitation links, version negotiation, the
request signature, and the log redaction of peering secrets."""

import time
from datetime import UTC
from datetime import datetime

import pytest

from src.platform.domain.exceptions import InvalidPeerConfigurationError
from src.platform.domain.exceptions import PeeringVersionMismatchError
from src.platform.domain.services.peering_rules import Negotiated
from src.platform.domain.services.peering_rules import invitation_link
from src.platform.domain.services.peering_rules import negotiate
from src.platform.domain.services.peering_rules import negotiation_is_acceptable
from src.platform.domain.services.peering_rules import new_invitation_code
from src.platform.domain.services.peering_rules import new_peer_secret
from src.platform.domain.services.peering_rules import normalised_base_url
from src.platform.domain.services.peering_rules import parse_invitation_link
from src.platform.domain.services.peering_rules import sign_request
from src.platform.domain.services.peering_rules import signature_matches
from src.platform.domain.services.peering_rules import timestamp_is_fresh
from src.platform.infrastructure.logging.ring_buffer import Redactor

OWN_FORMATS = {"cuisine-recipes": (1, 2), "cuisine-catalogue": (1,)}


def test_an_invitation_link_round_trips() -> None:
    code = new_invitation_code()
    link = invitation_link("https://cuisine.example/", code)
    assert link == f"https://cuisine.example/peering/accept?code={code}"
    parsed = parse_invitation_link(link, require_https=True)
    assert (parsed.base_url, parsed.code) == ("https://cuisine.example", code)
    prefixed = parse_invitation_link(
        f"https://Example.org:8443/cook/peering/accept/?code={code}", require_https=True
    )
    assert prefixed.base_url == "https://example.org:8443/cook"


@pytest.mark.parametrize(
    "link",
    [
        "https://cuisine.example/somewhere?code=cuisine_pi_x",
        "https://cuisine.example/peering/accept?code=other",
        "https://cuisine.example/peering/accept",
        "ftp://cuisine.example/peering/accept?code=cuisine_pi_x",
        "https://user:pw@cuisine.example/peering/accept?code=cuisine_pi_x",
    ],
)
def test_malformed_invitation_links_are_refused(link: str) -> None:
    with pytest.raises(InvalidPeerConfigurationError):
        parse_invitation_link(link, require_https=True)


def test_plain_http_is_only_accepted_in_debug_mode() -> None:
    with pytest.raises(InvalidPeerConfigurationError, match="https"):
        normalised_base_url("http://cuisine.example", require_https=True)
    assert normalised_base_url("http://cuisine.example/", require_https=False) == (
        "http://cuisine.example"
    )


def test_negotiation_picks_the_highest_common_versions() -> None:
    result = negotiate(
        own_protocols=(1, 2),
        peer_protocols=[2, 3],
        own_formats=OWN_FORMATS,
        peer_formats={"cuisine-recipes": [1, 2, 3], "cuisine-catalogue": [2], "other": [1]},
        required_formats={"cuisine-recipes"},
    )
    # The catalogue shares no version and is optional, so it is left out.
    assert result == Negotiated(protocol_version=2, format_versions={"cuisine-recipes": 2})


def test_negotiation_without_overlap_names_both_sides() -> None:
    with pytest.raises(PeeringVersionMismatchError, match=r"speaks 1, 2, the other one 3"):
        negotiate(
            own_protocols=(1, 2),
            peer_protocols=[3],
            own_formats=OWN_FORMATS,
            peer_formats={"cuisine-recipes": [1]},
            required_formats={"cuisine-recipes"},
        )
    with pytest.raises(PeeringVersionMismatchError, match="cuisine-recipes"):
        negotiate(
            own_protocols=(1,),
            peer_protocols=[1],
            own_formats=OWN_FORMATS,
            peer_formats={"cuisine-recipes": [5]},
            required_formats={"cuisine-recipes"},
        )
    with pytest.raises(PeeringVersionMismatchError, match="does not know"):
        negotiate(
            own_protocols=(1,),
            peer_protocols=[1],
            own_formats=OWN_FORMATS,
            peer_formats={},
            required_formats={"cuisine-recipes"},
        )


def test_an_answer_with_unsupported_versions_is_not_acceptable() -> None:
    def ok(negotiated: Negotiated) -> bool:
        return negotiation_is_acceptable(
            negotiated,
            own_protocols=(1,),
            own_formats=OWN_FORMATS,
            required_formats={"cuisine-recipes"},
        )

    assert ok(Negotiated(1, {"cuisine-recipes": 2}))
    assert not ok(Negotiated(2, {"cuisine-recipes": 1}))
    assert not ok(Negotiated(1, {"cuisine-recipes": 3}))
    assert not ok(Negotiated(1, {"cuisine-catalogue": 1}))


def test_a_signature_binds_id_time_method_target_and_body() -> None:
    secret = new_peer_secret()
    now = int(time.time())
    parts = {"message_id": "m1", "timestamp": now, "method": "GET", "target": "/hello"}
    header = sign_request(secret, body=b"", **parts)  # type: ignore[arg-type]
    assert header.startswith("v1,")
    assert signature_matches(secret, f"v1,other {header}", body=b"", **parts)  # type: ignore[arg-type]
    for change in (
        {"message_id": "m2"},
        {"timestamp": now + 1},
        {"method": "POST"},
        {"target": "/revoke"},
    ):
        assert not signature_matches(
            secret,
            header,
            body=b"",
            **(parts | change),  # type: ignore[arg-type]
        )
    assert not signature_matches(secret, header, body=b"x", **parts)  # type: ignore[arg-type]
    assert not signature_matches(new_peer_secret(), header, body=b"", **parts)  # type: ignore[arg-type]
    assert not signature_matches("", header, body=b"", **parts)  # type: ignore[arg-type]


def test_timestamps_older_or_newer_than_five_minutes_are_stale() -> None:
    now = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
    stamp = int(now.timestamp())
    assert timestamp_is_fresh(stamp - 300, now)
    assert timestamp_is_fresh(stamp + 300, now)
    assert not timestamp_is_fresh(stamp - 301, now)
    assert not timestamp_is_fresh(stamp + 301, now)


def test_the_log_redacts_peer_secrets_and_invitation_codes() -> None:
    secret, code = new_peer_secret(), new_invitation_code()
    text = Redactor([])(f"pairing with {secret} via https://a.example/peering/accept?code={code}")
    assert secret not in text and code not in text
    assert "cuisine_ps_[redacted]" in text and "cuisine_pi_[redacted]" in text
