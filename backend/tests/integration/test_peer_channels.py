"""The peer channel transport between two paired instances: publishing,
delivery with a retry schedule that never gives up, the inbound queue,
fetching items, sequence gaps, restore detection, the timers, version
announcements, revoking, the feature switch, request authentication and the
protocol message schemas.

Every test runs two complete apps ("A" on the test database, "B" on a
second SQLite file) paired through their admin endpoints, talking to each
other through ASGI transports. A fake content kind `note` is registered for
both: a source keeps its notes in `World.source`, a receiver keeps what it
took in in `World.held`. The channel worker is driven by hand with
`run_a()` and `run_b()`."""

import json
import tempfile
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dataclasses import field
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import pytest
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bootstrap import seed
from src.bootstrap.models import Base
from src.bootstrap.peer_channel_worker import announce_peer_changes_once
from src.bootstrap.peer_channel_worker import run_peer_channels_once
from src.platform.adapters.inbound.api import auth_deps
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.outbound.external.peering.httpx_peer_client import HttpxPeerClient
from src.platform.adapters.outbound.persistence.models.peer_channel_models import (
    PeerChannelEventModel,
)
from src.platform.adapters.outbound.persistence.models.peer_channel_models import PeerChannelModel
from src.platform.adapters.outbound.persistence.models.peer_channel_models import PeerInboxModel
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.session import build_engine
from src.platform.application.services.peering_messages import changes_message
from src.platform.application.services.peering_messages import event_message
from src.platform.application.use_cases.peering import authenticate_peer
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.peer_channel import PeerChannelEvent
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.services.peer_channel_rules import ITEM_SHARED
from src.platform.domain.services.peer_channel_rules import ITEM_UPDATED
from src.platform.domain.services.peer_channel_rules import ITEM_WITHDRAWN
from src.platform.domain.services.peer_channel_rules import PEER_UPDATED
from src.platform.domain.services.peering_rules import sign_request
from src.platform.infrastructure.config.settings import DatabaseSettings
from src.platform.ports.outbound.peer_content import PeerItem
from src.platform.ports.outbound.peer_content import SharedItem
from src.shared_kernel.domain.services.clock import now_utc
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import system_user
from tests.integration.test_peering import A_URL
from tests.integration.test_peering import B_URL
from tests.integration.test_peering import GUARD
from tests.integration.test_peering import build_app
from tests.integration.test_peering import enable_peering

WEB = "/api/v1/web"
PEERING = "/api/peering/v1"
KIND = "note"
FORMATS = Path(__file__).resolve().parents[2] / "formats"


# ── Fake content ──────────────────────────────────────────────────────


@dataclass
class Note:
    revision: str
    text: str
    shared: bool = True


@dataclass
class World:
    """What each instance shares as a source and holds as a receiver."""

    source: dict[str, dict[str, Note]] = field(default_factory=lambda: {"a": {}, "b": {}})
    held: dict[str, dict[str, tuple[str, str]]] = field(default_factory=lambda: {"a": {}, "b": {}})
    fetched: dict[str, list[str]] = field(default_factory=lambda: {"a": [], "b": []})
    withdrawn: dict[str, list[str]] = field(default_factory=lambda: {"a": [], "b": []})


class FakeProvider:
    def __init__(self, world: World, side: str) -> None:
        self._notes = world.source[side]

    async def shared_with(self, peer: Peer) -> list[SharedItem]:
        return [SharedItem(i, n.revision) for i, n in sorted(self._notes.items()) if n.shared]

    async def fetch(self, peer: Peer, item_id: str) -> PeerItem | None:
        note = self._notes.get(item_id)
        if note is None or not note.shared:
            return None
        return PeerItem(
            item_id=item_id,
            content=json.dumps({"text": note.text}).encode(),
            media_type="application/json",
            etag=f'"{note.revision}"',
        )


class FakeConsumer:
    def __init__(self, world: World, side: str) -> None:
        self._world = world
        self._side = side

    async def current_etag(self, peer: Peer, item_id: str) -> str | None:
        held = self._world.held[self._side].get(item_id)
        return held[0] if held else None

    async def apply(self, peer: Peer, item: PeerItem) -> None:
        assert item.media_type == "application/json"
        self._world.fetched[self._side].append(item.item_id)
        self._world.held[self._side][item.item_id] = (item.etag, json.loads(item.content)["text"])

    async def withdraw(self, peer: Peer, item_id: str) -> None:
        if self._world.held[self._side].pop(item_id, None) is not None:
            self._world.withdrawn[self._side].append(item_id)

    async def reconcile(self, peer: Peer, shared_ids: set[str]) -> None:
        for item_id in sorted(set(self._world.held[self._side]) - shared_ids):
            await self.withdraw(peer, item_id)


# ── The link between the two apps ─────────────────────────────────────


class Link(httpx.AsyncBaseTransport):
    """One direction of the network: requests of one app into the other.
    It can be cut completely, cut for `/events` only (an instance that
    cannot receive events), or swallow events as if they got lost after
    the receiver answered."""

    def __init__(self) -> None:
        self.app: Any = None
        self.offline = False
        self.events_offline = False
        self.lose_events = 0
        self.requests: list[str] = []
        # The handshake request and answer bodies, for the schema test.
        self.handshakes: list[tuple[bytes, bytes]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix(PEERING)
        self.requests.append(f"{request.method} {path}")
        is_event = path == "/events"
        if self.offline or (self.events_offline and is_event):
            raise httpx.ConnectError("offline", request=request)
        if self.lose_events and is_event:
            self.lose_events -= 1
            return httpx.Response(202, json={})
        response = await httpx.ASGITransport(app=self.app).handle_async_request(request)
        if path == "/handshake":
            answer = await response.aread()
            self.handshakes.append((request.content, answer))
            return httpx.Response(response.status_code, headers=response.headers, content=answer)
        return response

    def client(self) -> HttpxPeerClient:
        return HttpxPeerClient(GUARD, require_https=True, transport=self)


@dataclass
class Pair:
    a: httpx.AsyncClient
    b: httpx.AsyncClient
    sessions_b: async_sessionmaker[AsyncSession]
    to_a: Link
    to_b: Link
    world: World
    # Each side's record of the other.
    b_on_a: Peer
    a_on_b: Peer

    def sessions(self, side: str) -> async_sessionmaker[AsyncSession]:
        return SessionLocal if side == "a" else self.sessions_b

    def peer(self, side: str) -> Peer:
        return self.b_on_a if side == "a" else self.a_on_b

    async def run(self, side: str) -> Any:
        return await run_peer_channels_once(
            sessions=self.sessions(side),
            client=(self.to_b if side == "a" else self.to_a).client(),
            base_url=A_URL if side == "a" else B_URL,
            guard=GUARD,
        )

    async def run_a(self) -> Any:
        return await self.run("a")

    async def run_b(self) -> Any:
        return await self.run("b")

    async def publish(self, side: str, type: str, item_id: str, revision: str | None) -> None:
        async with self.sessions(side)() as db:
            assert await Platform(db).peer_channel.publish(
                self.peer(side).id, type, KIND, item_id, revision
            )
            await db.commit()

    async def share(self, side: str, item_id: str, revision: str, text: str) -> None:
        """Shares (or updates) a note at the source and publishes it."""
        known = item_id in self.world.source[side]
        self.world.source[side][item_id] = Note(revision, text)
        await self.publish(side, ITEM_UPDATED if known else ITEM_SHARED, item_id, revision)

    async def channel(self, side: str) -> PeerChannelModel:
        async with self.sessions(side)() as db:
            row = await db.get(PeerChannelModel, self.peer(side).id)
            assert row is not None
            return row

    async def set_channel(self, side: str, **values: Any) -> None:
        async with self.sessions(side)() as db:
            await db.execute(
                update(PeerChannelModel)
                .where(PeerChannelModel.peer_id == self.peer(side).id)
                .values(**values)
            )
            await db.commit()

    async def make_due(self, side: str, *timers: str) -> None:
        past = now_utc() - timedelta(seconds=1)
        await self.set_channel(side, **{f"{t}_due_at": past for t in timers})

    async def retry_now(self, side: str) -> None:
        await self.set_channel(side, next_send_at=now_utc() - timedelta(seconds=1))

    async def log(self, side: str) -> list[PeerChannelEventModel]:
        async with self.sessions(side)() as db:
            rows = await db.scalars(
                select(PeerChannelEventModel)
                .where(PeerChannelEventModel.peer_id == self.peer(side).id)
                .order_by(PeerChannelEventModel.seq)
            )
            return list(rows.all())

    async def inbox(self, side: str) -> list[PeerInboxModel]:
        async with self.sessions(side)() as db:
            rows = await db.scalars(
                select(PeerInboxModel)
                .where(PeerInboxModel.peer_id == self.peer(side).id)
                .order_by(PeerInboxModel.id)
            )
            return list(rows.all())

    async def stored_peer(self, side: str) -> Peer:
        async with self.sessions(side)() as db:
            found = await Platform(db).peers.get(self.peer(side).id)
        assert found is not None
        return found

    async def admin_peer(self, side: str) -> dict[str, Any]:
        client = self.a if side == "a" else self.b
        listed = (await client.get(f"{WEB}/admin/peers")).json()
        found: dict[str, Any] = next(p for p in listed if p["id"] == str(self.peer(side).public_id))
        return found

    async def settle(self) -> None:
        """Runs both sides until nothing moves."""
        for _ in range(4):
            await self.run_a()
            await self.run_b()


@pytest.fixture
async def pair(login_system: LoginSystem, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Pair]:
    world = World()
    with tempfile.TemporaryDirectory(prefix="cuisine-peer-b-") as folder:
        engine_b = build_engine(DatabaseSettings(url=f"sqlite:///{Path(folder) / 'b.db'}"))
        sessions_b = async_sessionmaker(autoflush=False, expire_on_commit=False, bind=engine_b)
        async with engine_b.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        def side_of(db: AsyncSession) -> str:
            return "b" if db.bind is engine_b else "a"

        deps.register_peer_content(
            KIND,
            provider=lambda db: FakeProvider(world, side_of(db)),
            consumer=lambda db: FakeConsumer(world, side_of(db)),
        )
        try:
            to_a, to_b = Link(), Link()
            app_a = build_app(base_url=A_URL, peer_client=to_b.client())
            app_b = build_app(base_url=B_URL, peer_client=to_a.client())
            to_a.app, to_b.app = app_a, app_b

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
                async with SessionLocal() as db:
                    (b_on_a,) = await Platform(db).peers.list_active()
                async with sessions_b() as db:
                    (a_on_b,) = await Platform(db).peers.list_active()
                pair = Pair(
                    a=a,
                    b=b,
                    sessions_b=sessions_b,
                    to_a=to_a,
                    to_b=to_b,
                    world=world,
                    b_on_a=b_on_a,
                    a_on_b=a_on_b,
                )
                # The first run of each side catches up once (an empty
                # channel); later runs only catch up when a test says so.
                await pair.settle()
                yield pair
        finally:
            deps.unregister_peer_content(KIND)
            await engine_b.dispose()


# ── Publish, deliver, fetch ───────────────────────────────────────────


async def test_a_published_item_is_delivered_fetched_and_applied(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    log = await pair.log("a")
    assert [(e.seq, e.type, e.item_id) for e in log] == [(1, ITEM_SHARED, "n1")]

    run = await pair.run_a()
    assert run.sent == 1
    assert pair.to_b.requests[-1] == "POST /events"
    queued = await pair.inbox("b")
    assert [(j.type, j.kind, j.item_id, j.seq, j.prev_seq) for j in queued] == [
        (ITEM_SHARED, KIND, "n1", 1, 0)
    ]

    await pair.run_b()
    assert pair.world.held["b"]["n1"] == ('"1"', "Soup")
    assert await pair.inbox("b") == []
    assert (await pair.channel("b")).in_seq == 1
    assert (await pair.channel("a")).delivered_seq == 1


async def test_an_unchanged_item_is_not_fetched_again(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    assert pair.world.fetched["b"] == ["n1"]
    # A repeated update of the same revision answers 304.
    await pair.publish("a", ITEM_UPDATED, "n1", "1")
    await pair.settle()
    assert pair.world.fetched["b"] == ["n1"]
    assert "GET /items/note/n1" in pair.to_a.requests


async def test_updates_collapse_into_the_latest_state_per_item(pair: Pair) -> None:
    pair.to_b.offline = True
    await pair.share("a", "n1", "1", "Soup")
    await pair.run_a()
    await pair.share("a", "n1", "2", "Better soup")
    await pair.share("a", "n1", "3", "Best soup")
    await pair.share("a", "n2", "1", "Bread")
    log = await pair.log("a")
    assert [(e.seq, e.item_id, e.revision) for e in log] == [(3, "n1", "3"), (4, "n2", "1")]

    pair.to_b.offline = False
    await pair.retry_now("a")
    run = await pair.run_a()
    assert run.sent == 2
    jobs = await pair.inbox("b")
    assert [(j.item_id, j.seq, j.prev_seq) for j in jobs] == [("n1", 3, 0), ("n2", 4, 3)]
    await pair.run_b()
    assert pair.world.held["b"]["n1"] == ('"3"', "Best soup")
    assert pair.world.fetched["b"] == ["n1", "n2"]


async def test_a_withdrawal_removes_the_copy(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    pair.world.source["a"]["n1"].shared = False
    await pair.publish("a", ITEM_WITHDRAWN, "n1", None)
    await pair.settle()
    assert "n1" not in pair.world.held["b"]
    assert pair.world.withdrawn["b"] == ["n1"]


async def test_a_fetch_answering_not_shared_withdraws(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    # The source stopped sharing without publishing a withdrawal, then an
    # update event arrives: the fetch answers 404 marked withdrawn.
    pair.world.source["a"]["n1"] = Note("2", "Soup", shared=False)
    await pair.publish("a", ITEM_UPDATED, "n1", "2")
    await pair.settle()
    assert "n1" not in pair.world.held["b"]


async def test_a_disabled_source_does_not_withdraw_anything(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    await pair.publish("a", ITEM_UPDATED, "n1", "2")
    await pair.run_a()
    async with SessionLocal() as db:
        await SqlAlchemySettingsRepository(db).save_features(FeatureSettings(peering=False))
        await db.commit()
    # The plain 404 of a switched off instance is a failure, not a
    # withdrawal: the event waits for its next attempt.
    await pair.run_b()
    assert pair.world.held["b"]["n1"] == ('"1"', "Soup")
    (job,) = await pair.inbox("b")
    assert (job.attempts, job.error) == (1, "refused")
    assert job.next_attempt_at > now_utc() + timedelta(seconds=50)


# ── Never giving up ───────────────────────────────────────────────────


async def test_an_offline_receiver_is_retried_forever(pair: Pair) -> None:
    pair.to_b.offline = True
    await pair.share("a", "n1", "1", "Soup")
    waits: list[timedelta] = []
    for _ in range(7):
        before = now_utc()
        assert (await pair.run_a()).sent == 0
        channel = await pair.channel("a")
        assert channel.next_send_at is not None
        waits.append(channel.next_send_at - before)
        await pair.retry_now("a")
    minutes = [round(w.total_seconds() / 60) for w in waits]
    assert minutes == [1, 5, 30, 120, 60, 60, 60]
    channel = await pair.channel("a")
    assert channel.send_attempts == 7
    assert channel.last_delivery_error == "unreachable"
    status = (await pair.admin_peer("a"))["channel"]
    assert status["pending_outgoing"] == 1
    assert status["last_delivery_error"] == "unreachable"

    pair.to_b.offline = False
    assert (await pair.run_a()).sent == 1
    channel = await pair.channel("a")
    assert (channel.send_attempts, channel.last_delivery_error) == (0, None)
    await pair.run_b()
    assert "n1" in pair.world.held["b"]


async def test_a_refusing_receiver_is_retried_too(pair: Pair) -> None:
    async with pair.sessions_b() as db:
        await SqlAlchemySettingsRepository(db).save_features(FeatureSettings(peering=False))
        await db.commit()
    await pair.share("a", "n1", "1", "Soup")
    await pair.run_a()
    channel = await pair.channel("a")
    assert (channel.last_delivery_status, channel.last_delivery_error) == (404, "refused")
    assert channel.delivered_seq == 0
    await enable_peering(pair.sessions_b)
    await pair.retry_now("a")
    assert (await pair.run_a()).sent == 1


# ── Sequence numbers ──────────────────────────────────────────────────


async def test_a_gap_is_filled_by_catching_up(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    pair.to_b.lose_events = 1
    await pair.share("a", "n2", "1", "Bread")
    await pair.run_a()
    assert await pair.inbox("b") == []
    await pair.share("a", "n3", "1", "Salad")
    await pair.run_a()
    (job,) = await pair.inbox("b")
    assert (job.seq, job.prev_seq) == (3, 2)
    assert (await pair.channel("b")).in_seq == 1

    await pair.run_b()
    assert "GET /changes" in pair.to_a.requests
    assert set(pair.world.held["b"]) == {"n1", "n2", "n3"}
    assert (await pair.channel("b")).in_seq == 3


async def test_a_duplicate_event_is_dropped(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    # The sender lost the answer and sends the same event again.
    await pair.set_channel("a", delivered_seq=0)
    await pair.run_a()
    assert len(await pair.inbox("b")) == 1
    await pair.run_b()
    assert pair.world.fetched["b"] == ["n1"]
    assert await pair.inbox("b") == []
    assert (await pair.channel("b")).in_seq == 1


async def test_a_lower_sequence_means_a_restored_source_and_reconciles(pair: Pair) -> None:
    for item_id in ("n1", "n2", "n3"):
        await pair.share("a", item_id, "1", item_id)
    await pair.settle()
    assert (await pair.channel("b")).in_seq == 3
    # A is restored from a backup taken after n1 was shared.
    async with SessionLocal() as db:
        await db.execute(delete(PeerChannelEventModel).where(PeerChannelEventModel.item_id != "n1"))
        await db.commit()
    await pair.set_channel("a", out_seq=1, delivered_seq=1)
    pair.world.source["a"] = {"n1": Note("1", "n1")}

    await pair.share("a", "n4", "1", "n4")
    await pair.run_a()
    (job,) = await pair.inbox("b")
    assert (job.seq, job.prev_seq) == (2, 1)
    await pair.run_b()
    assert set(pair.world.held["b"]) == {"n1", "n4"}
    assert sorted(pair.world.withdrawn["b"]) == ["n2", "n3"]
    channel = await pair.channel("b")
    assert channel.in_seq == 2
    assert channel.last_reconcile_at is not None

    # The channel continues from the source's new sequence.
    await pair.share("a", "n5", "1", "n5")
    await pair.settle()
    assert set(pair.world.held["b"]) == {"n1", "n4", "n5"}
    assert (await pair.channel("b")).in_seq == 3


# ── Timers ────────────────────────────────────────────────────────────


async def test_the_timer_catches_up_without_events(pair: Pair) -> None:
    # B cannot receive events, for example behind NAT at home.
    pair.to_b.events_offline = True
    await pair.share("a", "n1", "1", "Soup")
    await pair.run_a()
    await pair.run_b()
    assert pair.world.held["b"] == {}

    await pair.make_due("b", "catch_up")
    run = await pair.run_b()
    assert run.catch_ups == 1
    assert pair.world.held["b"]["n1"] == ('"1"', "Soup")
    channel = await pair.channel("b")
    assert channel.in_seq == 1
    assert channel.catch_up_due_at is not None
    assert channel.catch_up_due_at > now_utc() + timedelta(minutes=14)
    # Not due again until the interval passed.
    await pair.share("a", "n2", "1", "Bread")
    assert (await pair.run_b()).catch_ups == 0
    assert "n2" not in pair.world.held["b"]


async def test_sync_now_makes_the_catch_up_due(pair: Pair) -> None:
    pair.to_b.events_offline = True
    await pair.share("a", "n1", "1", "Soup")
    await pair.run_a()
    response = await pair.b.post(f"{WEB}/admin/peers/{pair.a_on_b.public_id}/sync", headers=CSRF)
    assert response.status_code == 200, response.text
    assert response.json()["channel"]["last_received_seq"] == 0
    await pair.run_b()
    assert "n1" in pair.world.held["b"]
    status = (await pair.admin_peer("b"))["channel"]
    assert status["last_received_seq"] == 1
    assert status["last_catch_up_at"] is not None


async def test_the_daily_comparison_repairs_both_sides(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    # B holds something A never shared (or withdrew without telling), and
    # A shares something it never published.
    pair.world.held["b"]["stale"] = ('"1"', "Old")
    pair.world.source["a"]["n9"] = Note("1", "Unpublished")

    await pair.make_due("b", "reconcile")
    run = await pair.run_b()
    assert run.reconciles == 1
    assert "stale" not in pair.world.held["b"]
    assert "n1" in pair.world.held["b"]

    await pair.make_due("a", "reconcile")
    await pair.run_a()
    assert [e.item_id for e in await pair.log("a")] == ["n1", "n9"]
    await pair.settle()
    assert pair.world.held["b"]["n9"] == ('"1"', "Unpublished")


async def test_a_daily_ping_proves_contact(pair: Pair) -> None:
    await pair.make_due("a", "ping")
    run = await pair.run_a()
    assert run.pings == 1
    assert run.sent == 1
    assert (await pair.stored_peer("b")).last_contact_at is not None
    await pair.run_b()
    assert await pair.inbox("b") == []
    assert (await pair.channel("b")).in_seq == 1
    channel = await pair.channel("a")
    assert channel.ping_due_at is not None
    assert channel.ping_due_at > now_utc() + timedelta(hours=23)


# ── Versions ──────────────────────────────────────────────────────────


async def test_peer_updated_makes_the_receiver_renegotiate(pair: Pair) -> None:
    # The first start announces; nothing changes on the second.
    assert await announce_peer_changes_once(base_url=A_URL) == 1
    assert await announce_peer_changes_once(base_url=A_URL) == 0
    async with SessionLocal() as db:
        settings = SqlAlchemySettingsRepository(db)
        general = await settings.get_general()
        general.instance_name = "Renamed kitchen"
        await settings.save_general(general)
        state = dict(await settings.get_job_state())
        state["peering_announced"] = {"app_version": "0.0.1"}
        await settings.save_job_state(state)
        await db.commit()
    assert await announce_peer_changes_once(base_url=A_URL) == 1
    (event,) = [e for e in await pair.log("a") if e.type == PEER_UPDATED]
    assert event.data["capabilities"]

    await pair.run_a()
    await pair.run_b()
    assert (await pair.stored_peer("b")).name == "Renamed kitchen"
    assert "GET /hello" in pair.to_a.requests


async def test_another_protocol_version_queues_a_renegotiation(
    pair: Pair, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(authenticate_peer, "SUPPORTED_PROTOCOL_VERSIONS", (1, 2))
    # Plays B calling A with protocol version 2, signed with the secret A
    # issued to B.
    b_peer = await pair.stored_peer("b")
    headers = signed_headers(b_peer.outbound_secret, pair.a_on_b, "GET", "/hello", version="2")
    headers["Cuisine-Peer"] = str(await instance_id("b", pair))
    response = await pair.a.get(f"{PEERING}/hello", headers=headers)
    assert response.status_code == 200, response.text
    (job,) = await pair.inbox("a")
    assert (job.type, job.seq) == (PEER_UPDATED, None)
    await pair.run_a()
    assert await pair.inbox("a") == []
    assert "GET /hello" in pair.to_b.requests


# ── Revoke and the feature switch ─────────────────────────────────────


async def test_revoking_purges_the_channel_and_tells_the_peer(pair: Pair) -> None:
    pair.to_b.events_offline = True
    await pair.share("a", "n1", "1", "Soup")
    await pair.run_a()
    assert await pair.log("a")
    revoked = await pair.a.post(f"{WEB}/admin/peers/{pair.b_on_a.public_id}/revoke", headers=CSRF)
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["peer_notified"] is True
    assert revoked.json()["peer"]["channel"] is None
    assert await pair.log("a") == []
    async with SessionLocal() as db:
        assert await db.get(PeerChannelModel, pair.b_on_a.id) is None
    assert (await pair.stored_peer("b")).status.value == "revoked"
    async with pair.sessions_b() as db:
        assert await db.get(PeerChannelModel, pair.a_on_b.id) is None
    # Nothing is sent any more.
    assert (await pair.run_a()).sent == 0


async def test_a_peer_revoked_event_revokes(pair: Pair) -> None:
    b_peer = await pair.stored_peer("b")
    body = json.dumps({"type": "peer.revoked", "seq": 1, "prev_seq": 0}).encode()
    headers = signed_headers(b_peer.outbound_secret, pair.a_on_b, "POST", "/events", body)
    headers["Cuisine-Peer"] = str(await instance_id("b", pair))
    headers["Content-Type"] = "application/json"
    response = await pair.a.post(f"{PEERING}/events", content=body, headers=headers)
    assert response.status_code == 202, response.text
    peer = await pair.stored_peer("a")
    assert (peer.status.value, peer.revoked_by and peer.revoked_by.value) == ("revoked", "remote")


async def test_nothing_is_sent_while_the_switch_is_off(pair: Pair) -> None:
    async with SessionLocal() as db:
        await SqlAlchemySettingsRepository(db).save_features(FeatureSettings(peering=False))
        await db.commit()
    await pair.share("a", "n1", "1", "Soup")
    requests = len(pair.to_b.requests)
    run = await pair.run_a()
    assert (run.sent, run.catch_ups) == (0, 0)
    assert len(pair.to_b.requests) == requests
    await enable_peering()
    assert (await pair.run_a()).sent == 1


# ── Authentication and contact ────────────────────────────────────────


async def instance_id(side: str, pair: Pair) -> uuid.UUID:
    async with pair.sessions(side)() as db:
        return await SqlAlchemySettingsRepository(db).instance_id()


def signed_headers(
    secret: str,
    _peer: Peer,
    method: str,
    target: str,
    body: bytes = b"",
    *,
    message_id: str | None = None,
    version: str = "1",
) -> dict[str, str]:
    message_id = message_id or str(uuid.uuid4())
    timestamp = int(time.time())
    return {
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
        "Cuisine-Peering-Version": version,
    }


@pytest.mark.parametrize(
    ("method", "target"),
    [("POST", "/events"), ("GET", "/changes?since=0"), ("GET", "/items/note/n1")],
)
async def test_channel_routes_need_a_valid_signature_and_refuse_replays(
    pair: Pair, method: str, target: str
) -> None:
    pair.world.source["a"]["n1"] = Note("1", "Soup")
    b_peer = await pair.stored_peer("b")
    sender = str(await instance_id("b", pair))
    body = (
        json.dumps({"type": "ping", "seq": 1, "prev_seq": 0}).encode() if method == "POST" else b""
    )
    url = f"{PEERING}{target}"
    unsigned = await pair.a.request(
        method, url, content=body or None, headers={"Cuisine-Peering-Version": "1"}
    )
    assert unsigned.status_code == 401

    wrong = signed_headers("cuisine_ps_" + "x" * 43, pair.a_on_b, method, target, body)
    wrong["Cuisine-Peer"] = sender
    assert (
        await pair.a.request(method, url, content=body or None, headers=wrong)
    ).status_code == 401

    good = signed_headers(b_peer.outbound_secret, pair.a_on_b, method, target, body)
    good["Cuisine-Peer"] = sender
    if body:
        good["Content-Type"] = "application/json"
    first = await pair.a.request(method, url, content=body or None, headers=good)
    assert first.status_code in (200, 202), first.text
    replayed = await pair.a.request(method, url, content=body or None, headers=good)
    assert replayed.status_code == 401
    peer = await pair.stored_peer("a")
    assert peer.last_contact_at is not None


async def test_items_and_changes_answer_only_what_is_shared(pair: Pair) -> None:
    pair.world.source["a"]["n1"] = Note("1", "Soup")
    pair.world.source["a"]["secret"] = Note("1", "Hidden", shared=False)
    b_peer = await pair.stored_peer("b")
    sender = str(await instance_id("b", pair))

    async def get(target: str, **extra: str) -> httpx.Response:
        headers = signed_headers(b_peer.outbound_secret, pair.a_on_b, "GET", target)
        headers["Cuisine-Peer"] = sender
        headers.update(extra)
        return await pair.a.get(f"{PEERING}{target}", headers=headers)

    found = await get("/items/note/n1")
    assert found.status_code == 200
    assert found.headers["ETag"] == '"1"'
    assert found.json() == {"text": "Soup"}
    assert (await get("/items/note/n1", **{"If-None-Match": '"1"'})).status_code == 304
    hidden = await get("/items/note/secret")
    assert hidden.status_code == 404
    assert hidden.json()["withdrawn"] is True
    assert (await get("/items/unknown/n1")).status_code == 404
    assert (await get("/items/note/bad%20id")).status_code in (401, 404)

    await pair.share("a", "n1", "2", "Soup")
    changes = (await get("/changes?since=0")).json()
    assert changes["max_seq"] == 1
    assert [(c["type"], c["id"], c["seq"]) for c in changes["changes"]] == [(ITEM_UPDATED, "n1", 1)]
    assert (await get("/changes?since=1")).json()["changes"] == []


async def test_a_malformed_event_is_refused(pair: Pair) -> None:
    b_peer = await pair.stored_peer("b")
    body = json.dumps({"type": ITEM_SHARED, "seq": 1, "prev_seq": 0, "kind": KIND}).encode()
    headers = signed_headers(b_peer.outbound_secret, pair.a_on_b, "POST", "/events", body)
    headers["Cuisine-Peer"] = str(await instance_id("b", pair))
    headers["Content-Type"] = "application/json"
    response = await pair.a.post(f"{PEERING}/events", content=body, headers=headers)
    assert response.status_code == 422
    assert await pair.inbox("a") == []


async def test_the_peer_page_shows_the_channel(pair: Pair) -> None:
    await pair.share("a", "n1", "1", "Soup")
    await pair.settle()
    on_a = (await pair.admin_peer("a"))["channel"]
    assert on_a["last_sent_seq"] == 1
    assert on_a["out_seq"] == 1
    assert on_a["pending_outgoing"] == 0
    assert on_a["last_delivery_status"] == 202
    on_b = (await pair.admin_peer("b"))["channel"]
    assert on_b["last_received_seq"] == 1
    assert on_b["pending_incoming"] == 0


# ── Protocol schemas ──────────────────────────────────────────────────


def schema(message: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (FORMATS / f"cuisine-peering.v1.{message}.schema.json").read_text()
    )
    return loaded


async def test_protocol_messages_match_their_schemas(pair: Pair) -> None:
    now = now_utc()
    item = PeerChannelEvent(
        peer_id=1, seq=4, type=ITEM_UPDATED, kind=KIND, item_id="n1", revision="2", created=now
    )
    control = PeerChannelEvent(
        peer_id=1,
        seq=5,
        type=PEER_UPDATED,
        kind="",
        item_id=PEER_UPDATED,
        data={
            "app_version": "1.0.0",
            "protocol_versions": [1],
            "formats": {"cuisine-recipes": [1]},
            "capabilities": ["variations"],
        },
        created=now,
    )
    jsonschema.validate(event_message(item, 3), schema("event"))
    jsonschema.validate(event_message(control, 4), schema("event"))
    jsonschema.validate(changes_message(0, 5, [item]), schema("changes-response"))

    b_peer = await pair.stored_peer("b")
    headers = signed_headers(b_peer.outbound_secret, pair.a_on_b, "GET", "/hello")
    headers["Cuisine-Peer"] = str(await instance_id("b", pair))
    hello = await pair.a.get(f"{PEERING}/hello", headers=headers)
    jsonschema.validate(hello.json(), schema("hello-response"))
    ((request, answer),) = pair.to_a.handshakes
    jsonschema.validate(json.loads(request), schema("handshake-request"))
    jsonschema.validate(json.loads(answer), schema("handshake-response"))
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"type": "ping"}, schema("event"))


def test_every_protocol_message_has_a_schema_file() -> None:
    for message in (
        "handshake-request",
        "handshake-response",
        "hello-response",
        "event",
        "changes-response",
    ):
        assert schema(message)["$id"].endswith(f":1:{message}")
