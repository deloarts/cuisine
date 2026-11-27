"""Pairing with other Cuisine instances: invitations, the handshake with
version negotiation, peer request signatures, revoke in both directions,
refresh, the feature switch, the target guard and the security log.

Most tests run one instance ("A") and play the other side by hand or
through a fake peer client. `test_two_instances_pair_end_to_end` runs two
complete apps on two SQLite files that talk to each other through ASGI
transports."""

import tempfile
import time
import uuid
from collections.abc import AsyncIterator
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bootstrap import seed
from src.bootstrap.main import create_app
from src.bootstrap.models import Base
from src.platform import const
from src.platform.adapters.inbound.api import auth_deps
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.outbound.external.login_attempts import InMemoryLoginAttemptTracker
from src.platform.adapters.outbound.external.peering.httpx_peer_client import HttpxPeerClient
from src.platform.adapters.outbound.external.replay_guard import InMemoryReplayGuard
from src.platform.adapters.outbound.external.request_rate_limiter import InMemoryRequestRateLimiter
from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.adapters.outbound.persistence.models.peer_models import PeerInvitationModel
from src.platform.adapters.outbound.persistence.models.security_models import SecurityEventModel
from src.platform.adapters.outbound.persistence.repositories.peer_repository import (
    SqlAlchemyPeerRepository,
)
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.session import build_engine
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.entities.settings import NotificationSettings
from src.platform.domain.exceptions import PeerUnreachableError
from src.platform.domain.services.peering_rules import hash_code
from src.platform.domain.services.peering_rules import sign_request
from src.platform.infrastructure.config.settings import DatabaseSettings
from src.platform.ports.outbound.peer_client import PeerReply
from src.platform.ports.outbound.peer_client import PeerRequest
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import enrol_at_login
from tests.integration.conftest import login
from tests.integration.conftest import system_user

WEB = "/api/v1/web"
PEERING = "/api/peering/v1"
A_URL = "https://a.example"
B_URL = "https://b.example"
B_ID = uuid.UUID("6d1f3c8e-2b47-4d39-9a51-0e7c2f8b4a16")
B_SECRET = "cuisine_ps_" + "b" * 43
PUBLIC_ADDRESS = "93.184.216.34"


def resolver_for(table: dict[str, str]) -> Any:
    async def resolve(host: str, _port: int) -> Sequence[str]:
        return [table.get(host, PUBLIC_ADDRESS)]

    return resolve


GUARD = WebhookTargetGuard(
    resolver=resolver_for({"loopback.example": "127.0.0.1", "lan.example": "10.0.0.5"})
)


class FakePeerClient:
    """Records every request and answers from a script: a PeerReply, an
    exception to raise, or a callable taking the request."""

    def __init__(self) -> None:
        self.sent: list[PeerRequest] = []
        self.replies: list[Any] = []

    async def send(self, request: PeerRequest, *, allow_private: bool) -> PeerReply:
        self.sent.append(request)
        reply = self.replies.pop(0) if self.replies else PeerReply(204, None, "1")
        if isinstance(reply, Exception):
            raise reply
        if callable(reply):
            result: PeerReply = reply(request)
            return result
        assert isinstance(reply, PeerReply)
        return reply


def build_app(
    *,
    base_url: str,
    peer_client: Any,
    replay: InMemoryReplayGuard | None = None,
    attempts: InMemoryLoginAttemptTracker | None = None,
) -> Any:
    app = create_app()
    limiter = InMemoryRequestRateLimiter()
    guard_replay = replay or InMemoryReplayGuard()
    tracker = attempts or InMemoryLoginAttemptTracker()
    app.dependency_overrides[deps.get_login_attempts] = lambda: tracker
    app.dependency_overrides[deps.get_replay_guard] = lambda: guard_replay
    app.dependency_overrides[deps.get_request_rate_limiter] = lambda: limiter
    app.dependency_overrides[deps.get_webhook_guard] = lambda: GUARD
    app.dependency_overrides[deps.get_own_base_url] = lambda: base_url
    app.dependency_overrides[deps.get_peer_client] = lambda: peer_client
    return app


async def enable_peering(sessions: async_sessionmaker[AsyncSession] = SessionLocal) -> None:
    async with sessions() as db:
        await SqlAlchemySettingsRepository(db).save_features(FeatureSettings(peering=True))
        await db.commit()


@pytest.fixture
def fake_peer() -> FakePeerClient:
    return FakePeerClient()


@pytest.fixture
async def instance(
    fake_peer: FakePeerClient, login_system: LoginSystem
) -> AsyncIterator[httpx.AsyncClient]:
    """Instance A at https://a.example with peering on, its client signed in
    as the system user."""
    app = build_app(base_url=A_URL, peer_client=fake_peer)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://testserver"
    ) as c:
        await login_system(c)
        await enable_peering()
        yield c


async def invite(client: httpx.AsyncClient) -> str:
    response = await client.post(f"{WEB}/admin/peers/invitations", headers=CSRF)
    assert response.status_code == 201, response.text
    link: str = response.json()["link"]
    return link.split("code=", 1)[1]


def handshake_body(code: str, **changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "instance_id": str(B_ID),
        "name": "Friend's kitchen",
        "base_url": B_URL,
        "app_version": "9.9.9",
        "protocol_versions": [1],
        "formats": {"cuisine-recipes": [1], "cuisine-catalogue": [1]},
        "capabilities": ["variations", "seasons"],
        "code": code,
        "secret": B_SECRET,
        "a_future_field": {"ignored": True},
    }
    body.update(changes)
    return body


async def pair_b(client: httpx.AsyncClient) -> dict[str, Any]:
    """Plays instance B's side of a handshake; returns A's answer."""
    response = await client.post(f"{PEERING}/handshake", json=handshake_body(await invite(client)))
    assert response.status_code == 200, response.text
    answer: dict[str, Any] = response.json()
    return answer


def signed(
    secret: str,
    method: str,
    target: str,
    body: bytes = b"",
    *,
    instance: uuid.UUID = B_ID,
    timestamp: int | None = None,
    message_id: str | None = None,
    version: str | None = "1",
) -> dict[str, str]:
    message_id = message_id or str(uuid.uuid4())
    timestamp = int(time.time()) if timestamp is None else timestamp
    headers = {
        "Cuisine-Peer": str(instance),
        "webhook-id": message_id,
        "webhook-timestamp": str(timestamp),
        "webhook-signature": sign_request(
            secret,
            message_id=message_id,
            timestamp=timestamp,
            method=method,
            target=target,
            body=body,
        ),
    }
    if version is not None:
        headers["Cuisine-Peering-Version"] = version
    return headers


async def stored_peer(instance_id: uuid.UUID = B_ID) -> Peer:
    async with SessionLocal() as db:
        peer = await SqlAlchemyPeerRepository(db).get_by_instance_id(instance_id)
    assert peer is not None
    return peer


async def security_events(kind: str) -> list[dict[str, Any]]:
    async with SessionLocal() as db:
        rows = await db.scalars(
            select(SecurityEventModel)
            .where(SecurityEventModel.event_type == kind)
            .order_by(SecurityEventModel.id)
        )
        return [{"outcome": r.outcome, **dict(r.detail)} for r in rows.all()]


def hello_reply(**changes: Any) -> PeerReply:
    data: dict[str, Any] = {
        "instance_id": str(B_ID),
        "name": "Friend's kitchen",
        "base_url": B_URL,
        "app_version": "9.9.9",
        "protocol_versions": [1],
        "formats": {"cuisine-recipes": [1], "cuisine-catalogue": [1]},
        "capabilities": ["variations", "seasons"],
        "protocol_version": 1,
        "format_versions": {"cuisine-recipes": 1, "cuisine-catalogue": 1},
    }
    data.update(changes)
    return PeerReply(200, data, "1")


# ── Feature switch ────────────────────────────────────────────────────


async def test_every_peering_route_answers_404_while_the_switch_is_off(
    fake_peer: FakePeerClient, login_system: LoginSystem
) -> None:
    app = build_app(base_url=A_URL, peer_client=fake_peer)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://testserver"
    ) as c:
        await login_system(c)
        features = (await c.get(f"{WEB}/settings/features")).json()
        # A fresh instance starts with peering on, so switch it off first.
        assert features["peering"] is True
        await c.put(f"{WEB}/settings/features", headers=CSRF, json=features | {"peering": False})
        assert (await c.get("/api/v1/public/info")).json()["features"]["peering"] is False
        for method, path in (
            ("GET", f"{WEB}/admin/peers"),
            ("GET", f"{WEB}/admin/peers/self"),
            ("POST", f"{WEB}/admin/peers/invitations"),
            ("POST", f"{WEB}/admin/peers/accept"),
            ("POST", f"{PEERING}/handshake"),
            ("GET", f"{PEERING}/hello"),
            ("POST", f"{PEERING}/revoke"),
        ):
            response = await c.request(method, path, headers=CSRF, json={})
            assert response.status_code == 404, (method, path, response.text)
        await c.put(f"{WEB}/settings/features", headers=CSRF, json=features | {"peering": True})
        assert (await c.get(f"{WEB}/admin/peers")).status_code == 200


# ── Invitations ───────────────────────────────────────────────────────


async def test_an_invitation_is_a_one_time_link_stored_as_its_hash(
    instance: httpx.AsyncClient,
) -> None:
    response = await instance.post(f"{WEB}/admin/peers/invitations", headers=CSRF)
    assert response.status_code == 201
    created = response.json()
    assert created["link"].startswith(f"{A_URL}/peering/accept?code=cuisine_pi_")
    code = created["link"].split("code=", 1)[1]
    assert created["expires_at"] > created["created"]
    listed = (await instance.get(f"{WEB}/admin/peers/invitations")).json()
    assert [i["id"] for i in listed] == [created["id"]]
    assert "link" not in listed[0]
    async with SessionLocal() as db:
        row = await db.scalar(select(PeerInvitationModel))
        assert row is not None
        assert row.code_hash == hash_code(code)
        assert code not in row.code_hash
        assert row.expires_at - row.created == timedelta(hours=24)
    assert await security_events("peer_invitation_created")

    revoked = await instance.delete(f"{WEB}/admin/peers/invitations/{created['id']}", headers=CSRF)
    assert revoked.status_code == 204
    assert (await instance.get(f"{WEB}/admin/peers/invitations")).json() == []
    refused = await instance.post(f"{PEERING}/handshake", json=handshake_body(code))
    assert refused.status_code == 401
    assert (await security_events("peer_pairing_refused"))[-1]["reason"] == "unknown_code"


async def test_invitations_need_write_settings(
    instance: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("reader", permissions=["read:settings"])
    # A settings permission makes two-factor authentication mandatory.
    step = await login(other_client, "reader@example.com", "cook-password-1")
    await enrol_at_login(other_client, step["setup_token"])
    assert (await other_client.get(f"{WEB}/admin/peers")).status_code == 200
    refused = await other_client.post(f"{WEB}/admin/peers/invitations", headers=CSRF)
    assert refused.status_code == 403


async def test_a_code_works_once_and_not_after_expiry(instance: httpx.AsyncClient) -> None:
    code = await invite(instance)
    first = await instance.post(f"{PEERING}/handshake", json=handshake_body(code))
    assert first.status_code == 200
    again = await instance.post(f"{PEERING}/handshake", json=handshake_body(code))
    assert again.status_code == 401
    assert again.json()["code"] == "InvalidPeerInvitationError"
    assert (await security_events("peer_pairing_refused"))[-1]["reason"] == "used_code"
    assert (await instance.get(f"{WEB}/admin/peers/invitations")).json() == []

    late = await invite(instance)
    async with SessionLocal() as db:
        await db.execute(
            update(PeerInvitationModel)
            .where(PeerInvitationModel.code_hash == hash_code(late))
            .values(expires_at=now_utc() - timedelta(minutes=1))
        )
        await db.commit()
    expired = await instance.post(
        f"{PEERING}/handshake",
        json=handshake_body(late, instance_id=str(uuid.uuid4())),
    )
    assert expired.status_code == 401
    refusal = (await security_events("peer_pairing_refused"))[-1]
    assert refusal["reason"] == "expired_code"
    assert refusal["outcome"] == "failure"


# ── Handshake ─────────────────────────────────────────────────────────


async def test_the_handshake_stores_the_peer_with_both_secrets(
    instance: httpx.AsyncClient,
) -> None:
    answer = await pair_b(instance)
    own = (await instance.get(f"{WEB}/admin/peers/self")).json()
    assert answer["instance_id"] == own["instance_id"]
    assert answer["base_url"] == A_URL == own["base_url"]
    assert answer["protocol_version"] == 1
    assert answer["format_versions"] == {"cuisine-recipes": 1, "cuisine-catalogue": 1}
    assert answer["secret"].startswith("cuisine_ps_")
    assert own["capabilities"] == ["equipment", "extended_nutrients", "seasons", "variations"]

    peer = await stored_peer()
    assert peer.inbound_secret == answer["secret"]
    assert peer.outbound_secret == B_SECRET
    assert peer.base_url == B_URL
    assert peer.capabilities == ["seasons", "variations"]
    assert (peer.users_may_share, peer.accept_incoming, peer.sync_all) == (
        True,
        True,
        True,
    )
    assert peer.mirror_visibility.value == "instance"

    async with SessionLocal() as db:
        raw = (await db.execute(text("SELECT inbound_secret, outbound_secret FROM peers"))).one()
    assert answer["secret"] not in raw[0] and B_SECRET not in raw[1]
    assert not raw[0].startswith("cuisine_ps_")

    listed = await instance.get(f"{WEB}/admin/peers")
    assert listed.status_code == 200
    assert answer["secret"] not in listed.text and B_SECRET not in listed.text
    entry = listed.json()[0]
    assert entry["name"] == "Friend's kitchen"
    assert entry["status"] == "active"
    assert entry["app_version"] == "9.9.9"
    assert entry["last_contact_at"] is not None
    paired = await security_events("peer_paired")
    assert paired[-1]["role"] == "invited" and paired[-1]["peer"] == entry["id"]
    async with SessionLocal() as db:
        details = [str(r.detail) for r in (await db.scalars(select(SecurityEventModel))).all()]
    assert not any(answer["secret"] in d or B_SECRET in d for d in details)


async def test_versions_without_overlap_are_refused_naming_both(
    instance: httpx.AsyncClient,
) -> None:
    code = await invite(instance)
    refused = await instance.post(
        f"{PEERING}/handshake", json=handshake_body(code, protocol_versions=[7, 8])
    )
    assert refused.status_code == 422
    assert refused.json()["code"] == "PeeringVersionMismatchError"
    assert "1" in refused.json()["detail"] and "7, 8" in refused.json()["detail"]
    formats = await instance.post(
        f"{PEERING}/handshake",
        json=handshake_body(code, formats={"cuisine-recipes": [5]}),
    )
    assert formats.status_code == 422
    assert "cuisine-recipes" in formats.json()["detail"]
    assert (await security_events("peer_pairing_refused"))[-1]["reason"] == "version_mismatch"
    # The code is still good once the other side is updated.
    retried = await instance.post(f"{PEERING}/handshake", json=handshake_body(code))
    assert retried.status_code == 200


async def test_an_active_pairing_is_refused_and_a_revoked_one_paired_again(
    instance: httpx.AsyncClient,
) -> None:
    await pair_b(instance)
    first = await stored_peer()
    again = await instance.post(f"{PEERING}/handshake", json=handshake_body(await invite(instance)))
    assert again.status_code == 409
    assert again.json()["code"] == "PeerAlreadyPairedError"

    await instance.post(f"{WEB}/admin/peers/{first.public_id}/revoke", headers=CSRF)
    answer = await pair_b(instance)
    renewed = await stored_peer()
    assert renewed.public_id == first.public_id
    assert renewed.active
    assert renewed.inbound_secret == answer["secret"] != first.inbound_secret


async def test_a_handshake_with_a_bad_identity_is_refused(instance: httpx.AsyncClient) -> None:
    code = await invite(instance)
    own = (await instance.get(f"{WEB}/admin/peers/self")).json()
    cases = [
        handshake_body(code, instance_id=own["instance_id"]),
        handshake_body(code, base_url="http://b.example"),
        handshake_body(code, base_url="https://loopback.example"),
        handshake_body(code, secret="short"),
        handshake_body(code, protocol_versions="1"),
    ]
    for body in cases:
        response = await instance.post(f"{PEERING}/handshake", json=body)
        assert response.status_code == 422, (body, response.text)
    assert (await instance.get(f"{WEB}/admin/peers")).json() == []


# ── Peer authentication ───────────────────────────────────────────────


async def test_hello_answers_a_signed_request(instance: httpx.AsyncClient) -> None:
    answer = await pair_b(instance)
    response = await instance.get(
        f"{PEERING}/hello", headers=signed(answer["secret"], "GET", "/hello")
    )
    assert response.status_code == 200, response.text
    assert response.headers["Cuisine-Peering-Version"] == "1"
    body = response.json()
    assert body["instance_id"] == answer["instance_id"]
    assert body["protocol_versions"] == [1]
    assert body["format_versions"]["cuisine-recipes"] == 1
    assert "secret" not in body


async def test_peer_requests_with_a_bad_signature_are_refused_and_logged(
    instance: httpx.AsyncClient,
) -> None:
    answer = await pair_b(instance)
    secret = answer["secret"]
    stale = int(time.time()) - 600
    reused = str(uuid.uuid4())
    assert (
        await instance.get(
            f"{PEERING}/hello", headers=signed(secret, "GET", "/hello", message_id=reused)
        )
    ).status_code == 200
    cases = {
        "bad_signature": signed("cuisine_ps_" + "z" * 43, "GET", "/hello"),
        "stale_timestamp": signed(secret, "GET", "/hello", timestamp=stale),
        "replayed": signed(secret, "GET", "/hello", message_id=reused),
        "unknown_peer": signed(secret, "GET", "/hello", instance=uuid.uuid4()),
        "malformed": {"Cuisine-Peering-Version": "1"},
    }
    # A signature for another route does not open this one.
    other_route = signed(secret, "POST", "/revoke")
    assert (await instance.get(f"{PEERING}/hello", headers=other_route)).status_code == 401
    for reason, headers in cases.items():
        response = await instance.get(f"{PEERING}/hello", headers=headers)
        assert response.status_code == 401, reason
        assert response.json()["code"] == "PeerAuthenticationError"
        assert response.headers["Cuisine-Peering-Version"] == "1"
    reasons = [e["reason"] for e in await security_events("peer_auth_failed")]
    assert reasons == ["bad_signature", *cases]
    no_version = await instance.get(
        f"{PEERING}/hello", headers=signed(secret, "GET", "/hello", version=None)
    )
    assert no_version.status_code == 422
    future = await instance.get(
        f"{PEERING}/hello", headers=signed(secret, "GET", "/hello", version="9")
    )
    assert future.status_code == 422
    assert "9" in future.json()["detail"]


async def test_the_peering_surface_is_rate_limited(
    instance: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(const, "PEERING_REQUEST_LIMIT", 2)
    for _ in range(2):
        assert (await instance.get(f"{PEERING}/hello")).status_code == 422
    limited = await instance.get(f"{PEERING}/hello")
    assert limited.status_code == 429
    assert limited.headers["Retry-After"]


# ── Revoke ────────────────────────────────────────────────────────────


async def test_a_peer_that_revokes_is_marked_revoked(instance: httpx.AsyncClient) -> None:
    answer = await pair_b(instance)
    headers = signed(answer["secret"], "POST", "/revoke", b"{}")
    response = await instance.post(f"{PEERING}/revoke", content=b"{}", headers=headers)
    assert response.status_code == 204, response.text
    peer = await stored_peer()
    assert not peer.active
    assert peer.revoked_by is not None and peer.revoked_by.value == "remote"
    assert peer.inbound_secret == "" and peer.outbound_secret == ""
    assert (await security_events("peer_revoked"))[-1]["by"] == "remote"
    hello_headers = signed(answer["secret"], "GET", "/hello")
    after = await instance.get(f"{PEERING}/hello", headers=hello_headers)
    assert after.status_code == 401
    assert (await security_events("peer_auth_failed"))[-1]["reason"] == "revoked"


async def test_revoking_locally_tells_the_peer_best_effort(
    instance: httpx.AsyncClient, fake_peer: FakePeerClient
) -> None:
    await pair_b(instance)
    peer = await stored_peer()
    revoked: list[Peer] = []

    async def hook(p: Peer) -> None:
        revoked.append(p)

    deps.register_peer_revoked_hook(lambda _db: hook)
    try:
        fake_peer.replies.append(PeerUnreachableError("offline"))
        response = await instance.post(f"{WEB}/admin/peers/{peer.public_id}/revoke", headers=CSRF)
    finally:
        deps._peer_revoked_hooks.clear()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["peer_notified"] is False
    assert body["peer"]["status"] == "revoked" and body["peer"]["revoked_by"] == "local"
    sent = fake_peer.sent[-1]
    assert (sent.method, sent.target, sent.base_url) == ("POST", "/revoke", B_URL)
    assert sent.signing is not None and sent.signing.secret == B_SECRET
    assert [p.public_id for p in revoked] == [peer.public_id]
    after = await stored_peer()
    assert not after.active and after.outbound_secret == ""
    assert (await security_events("peer_revoked"))[-1]["by"] == "local"


# ── Refresh and switches ──────────────────────────────────────────────


async def test_refresh_reads_hello_again(
    instance: httpx.AsyncClient, fake_peer: FakePeerClient
) -> None:
    await pair_b(instance)
    peer = await stored_peer()
    fake_peer.replies.append(
        hello_reply(name="Renamed kitchen", app_version="10.0.0", capabilities=["equipment"])
    )
    response = await instance.post(f"{WEB}/admin/peers/{peer.public_id}/refresh", headers=CSRF)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["name"], body["app_version"], body["capabilities"]) == (
        "Renamed kitchen",
        "10.0.0",
        ["equipment"],
    )
    request = fake_peer.sent[-1]
    assert (request.method, request.target) == ("GET", "/hello")
    assert request.signing is not None and request.signing.secret == B_SECRET
    changed = (await security_events("peer_changed"))[-1]
    assert changed["action"] == "refreshed"
    assert set(changed["fields"]) == {"name", "app_version", "capabilities"}

    fake_peer.replies.append(hello_reply(protocol_versions=[4]))
    mismatch = await instance.post(f"{WEB}/admin/peers/{peer.public_id}/refresh", headers=CSRF)
    assert mismatch.status_code == 422
    assert (await stored_peer()).protocol_version == 1


async def test_switches_are_stored_and_a_group_must_exist(instance: httpx.AsyncClient) -> None:
    await pair_b(instance)
    peer = await stored_peer()
    url = f"{WEB}/admin/peers/{peer.public_id}/switches"
    switches = {
        "users_may_share": False,
        "sync_all": True,
        "accept_incoming": False,
        "mirror_visibility": "group",
        "mirror_group": str(uuid.uuid4()),
    }
    assert (await instance.put(url, headers=CSRF, json=switches)).status_code == 422
    group = await instance.post(
        f"{WEB}/groups", headers=CSRF, json={"name": "Friends", "permissions": []}
    )
    assert group.status_code == 201, group.text
    switches["mirror_group"] = group.json()["id"]
    saved = await instance.put(url, headers=CSRF, json=switches)
    assert saved.status_code == 200, saved.text
    assert saved.json()["mirror_group"] == group.json()["id"]
    assert saved.json()["sync_all"] is True
    assert (await security_events("peer_changed"))[-1]["action"] == "switches"


# ── Accepting an invitation (instance B's side) ───────────────────────


async def test_accepting_refuses_urls_the_guard_or_https_rule_refuses(
    instance: httpx.AsyncClient, fake_peer: FakePeerClient
) -> None:
    code = "cuisine_pi_" + "c" * 43
    cases = [
        f"http://b.example/peering/accept?code={code}",
        f"https://loopback.example/peering/accept?code={code}",
        f"https://backend/peering/accept?code={code}",
        "https://b.example/somewhere/else",
        "https://b.example/peering/accept?code=nothing",
    ]
    for link in cases:
        response = await instance.post(
            f"{WEB}/admin/peers/accept", headers=CSRF, json={"invitation_url": link}
        )
        assert response.status_code == 422, (link, response.text)
    async with SessionLocal() as db:
        await SqlAlchemySettingsRepository(db).save_notifications(
            NotificationSettings(allow_private_webhook_targets=False)
        )
        await db.commit()
    private = await instance.post(
        f"{WEB}/admin/peers/accept",
        headers=CSRF,
        json={"invitation_url": f"https://lan.example/peering/accept?code={code}"},
    )
    assert private.status_code == 422
    assert "private network" in private.json()["detail"]
    assert fake_peer.sent == []


async def test_accepting_stores_what_the_inviting_instance_answers(
    instance: httpx.AsyncClient, fake_peer: FakePeerClient
) -> None:
    secret_for_us = "cuisine_ps_" + "a" * 43
    fake_peer.replies.append(hello_reply(secret=secret_for_us))
    code = "cuisine_pi_" + "c" * 43
    response = await instance.post(
        f"{WEB}/admin/peers/accept",
        headers=CSRF,
        json={"invitation_url": f"{B_URL}/peering/accept?code={code}"},
    )
    assert response.status_code == 200, response.text
    request = fake_peer.sent[-1]
    assert (request.base_url, request.method, request.target) == (B_URL, "POST", "/handshake")
    assert request.signing is None
    assert request.body is not None and request.body["code"] == code
    assert request.body["base_url"] == A_URL
    peer = await stored_peer()
    assert peer.outbound_secret == secret_for_us
    assert peer.inbound_secret == request.body["secret"]
    assert (await security_events("peer_paired"))[-1]["role"] == "accepted"

    fake_peer.replies.append(PeerReply(422, {"detail": "No common protocol version: 1 vs 3."}, "3"))
    refused = await instance.post(
        f"{WEB}/admin/peers/accept",
        headers=CSRF,
        json={"invitation_url": f"https://c.example/peering/accept?code={code}"},
    )
    assert refused.status_code == 400
    assert "No common protocol version: 1 vs 3." in refused.json()["detail"]
    assert (await security_events("peer_pairing_refused"))[-1]["reason"] == "refused_by_peer"


# ── Two instances ─────────────────────────────────────────────────────


class _PeerTransport:
    """Hands the peer client of one app a transport into the other app,
    built lazily because the two apps need each other."""

    def __init__(self) -> None:
        self.app: Any = None

    def client(self) -> HttpxPeerClient:
        return HttpxPeerClient(
            GUARD, require_https=True, transport=httpx.ASGITransport(app=self.app)
        )


async def test_two_instances_pair_end_to_end(
    login_system: LoginSystem, monkeypatch: pytest.MonkeyPatch
) -> None:
    with tempfile.TemporaryDirectory(prefix="cuisine-peer-b-") as folder:
        engine_b = build_engine(DatabaseSettings(url=f"sqlite:///{Path(folder) / 'b.db'}"))
        sessions_b = async_sessionmaker(autoflush=False, expire_on_commit=False, bind=engine_b)
        async with engine_b.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            to_a, to_b = _PeerTransport(), _PeerTransport()
            app_a = build_app(base_url=A_URL, peer_client=to_b.client())
            app_b = build_app(base_url=B_URL, peer_client=to_a.client())
            to_a.app, to_b.app = app_a, app_b
            # Built before the apps existed; rebuild now that both do.
            app_a.dependency_overrides[deps.get_peer_client] = to_b.client
            app_b.dependency_overrides[deps.get_peer_client] = to_a.client

            async def db_b() -> AsyncIterator[AsyncSession]:
                async with sessions_b() as session:
                    yield session

            app_b.dependency_overrides[deps.get_db] = db_b
            monkeypatch.setattr(seed, "SessionLocal", sessions_b)
            await seed.ensure_system_user()
            monkeypatch.undo()
            async with sessions_b() as db:
                admin_b = await system_user(SqlAlchemyUserRepository(db))
            assert admin_b is not None
            app_b.dependency_overrides[auth_deps.get_current_user] = lambda: admin_b
            await enable_peering()
            await enable_peering(sessions_b)

            async with (
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app_a), base_url="https://testserver"
                ) as a,
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app_b), base_url="https://testserver"
                ) as b,
            ):
                await login_system(a)
                link = (await a.post(f"{WEB}/admin/peers/invitations", headers=CSRF)).json()["link"]
                accepted = await b.post(
                    f"{WEB}/admin/peers/accept", headers=CSRF, json={"invitation_url": link}
                )
                assert accepted.status_code == 200, accepted.text
                a_self = (await a.get(f"{WEB}/admin/peers/self")).json()
                b_self = (await b.get(f"{WEB}/admin/peers/self")).json()
                assert a_self["instance_id"] != b_self["instance_id"]
                assert accepted.json()["instance_id"] == a_self["instance_id"]
                assert accepted.json()["base_url"] == A_URL

                on_a = (await a.get(f"{WEB}/admin/peers")).json()
                assert [p["instance_id"] for p in on_a] == [b_self["instance_id"]]
                assert on_a[0]["base_url"] == B_URL

                a_peer = await stored_peer(uuid.UUID(b_self["instance_id"]))
                async with sessions_b() as db:
                    b_peer = await SqlAlchemyPeerRepository(db).get_by_instance_id(
                        uuid.UUID(a_self["instance_id"])
                    )
                assert b_peer is not None
                # Each side signs with the secret the other issued.
                assert a_peer.outbound_secret == b_peer.inbound_secret
                assert b_peer.outbound_secret == a_peer.inbound_secret
                assert a_peer.inbound_secret != b_peer.inbound_secret

                # Signed requests work in both directions.
                a_peer_url = f"{WEB}/admin/peers/{a_peer.public_id}"
                refreshed = await a.post(f"{a_peer_url}/refresh", headers=CSRF)
                assert refreshed.status_code == 200, refreshed.text
                assert (
                    await b.post(f"{WEB}/admin/peers/{b_peer.public_id}/refresh", headers=CSRF)
                ).status_code == 200

                # B revokes; A hears of it.
                revoked = await b.post(f"{WEB}/admin/peers/{b_peer.public_id}/revoke", headers=CSRF)
                assert revoked.status_code == 200, revoked.text
                assert revoked.json()["peer_notified"] is True
                after = (await a.get(f"{WEB}/admin/peers")).json()[0]
                assert (after["status"], after["revoked_by"]) == ("revoked", "remote")
                stale = await a.post(f"{WEB}/admin/peers/{a_peer.public_id}/refresh", headers=CSRF)
                assert stale.status_code == 422
        finally:
            await engine_b.dispose()


# ── Permissions per route ─────────────────────────────────────────────

_ANY_ID = "00000000-0000-0000-0000-000000000000"
_PEER_READ_ROUTES = [
    ("GET", f"{WEB}/admin/peers/self"),
    ("GET", f"{WEB}/admin/peers/invitations"),
    ("GET", f"{WEB}/admin/peers"),
]
_PEER_WRITE_ROUTES = [
    ("POST", f"{WEB}/admin/peers/invitations"),
    ("DELETE", f"{WEB}/admin/peers/invitations/{_ANY_ID}"),
    ("POST", f"{WEB}/admin/peers/accept"),
    ("PUT", f"{WEB}/admin/peers/{_ANY_ID}/switches"),
    ("POST", f"{WEB}/admin/peers/{_ANY_ID}/refresh"),
    ("POST", f"{WEB}/admin/peers/{_ANY_ID}/revoke"),
    ("POST", f"{WEB}/admin/peers/{_ANY_ID}/sync"),
]


async def _request(client: httpx.AsyncClient, method: str, path: str) -> httpx.Response:
    body: dict[str, object] | None = None if method in ("GET", "DELETE") else {}
    return await client.request(method, path, headers=CSRF, json=body)


@pytest.mark.parametrize(("method", "path"), _PEER_READ_ROUTES + _PEER_WRITE_ROUTES)
async def test_every_peer_route_refuses_a_user_without_settings_permissions(
    instance: httpx.AsyncClient,
    make_user: MakeUser,
    other_client: httpx.AsyncClient,
    method: str,
    path: str,
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    refused = await _request(other_client, method, path)
    assert (refused.status_code, refused.json()["code"]) == (403, "PermissionDeniedError")


@pytest.mark.parametrize(("method", "path"), _PEER_WRITE_ROUTES)
async def test_every_changing_peer_route_needs_write_settings(
    instance: httpx.AsyncClient,
    make_user: MakeUser,
    other_client: httpx.AsyncClient,
    method: str,
    path: str,
) -> None:
    await make_user("reader", permissions=["read:settings"])
    step = await login(other_client, "reader@example.com", "cook-password-1")
    await enrol_at_login(other_client, step["setup_token"])
    refused = await _request(other_client, method, path)
    assert (refused.status_code, refused.json()["code"]) == (403, "PermissionDeniedError")
