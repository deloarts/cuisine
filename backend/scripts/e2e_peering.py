"""
End to end run of peering between two real Cuisine instances, on demand and
never in CI.

It starts two backend processes, "A" and "B", each with uvicorn on a free port
and its own throwaway SQLite file in a fresh temporary folder, and drives
them over HTTP the way two administrators and their cooks would: pairing,
sharing a recipe with a variation, the accept dialog with its catalogue
decisions, an automatic update, a held update, a withdrawal, an offline
catch-up, a protocol version mismatch, a recipe set to paired instances,
"sync all from this peer" with "accept everything that waits", and a
revoke. Every step asserts what
the other side shows. The folder and both processes are removed at the end,
also after a failure; `--keep` keeps the folder with the logs.

Nothing here touches a real database, Redis or the dev stack: the child
processes get a clean environment without ENV_FILE, refuse any database URL
that is not a SQLite file in their own folder, and swap the Redis users
(login throttle, replay guard, rate limiter, live updates) for their
in-process versions, as the test suite does.

Peering requests go through the real target guard, which refuses loopback
addresses whatever the settings say. Both instances therefore listen on the
host's own private network address (found through the default route, or
`--host`), which the guard accepts with the private network switch of the
notification settings, on by default. Debug mode lets them talk plain http.

The version mismatch is simulated by restarting B with another protocol
support window (`serve --protocol-window`), which patches the window the
running process announces and accepts; nothing in the product reads it from
the environment.

Usage (from backend/, or `make e2e-peering` from the repo root):
    poetry run python scripts/e2e_peering.py [--host 192.168.1.20] [--keep]
"""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import TypeVar

import httpx
import pyotp

BACKEND_DIR = Path(__file__).resolve().parents[1]
WEB = "/api/v1/web"
AUTH = "/api/v1/auth"
CSRF = {"X-Requested-With": "cuisine"}
TOTP_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
ADMIN_PASSWORD = "e2e-admin-password-1"
COOK_PASSWORD = "e2e-cook-password-1"
# Environment variables the settings read; the children never inherit them.
SETTINGS_PREFIXES = (
    "ENV_FILE",
    "DEBUG",
    "DOMAIN",
    "LOG_",
    "MIGRATE_ON_STARTUP",
    "DATABASE__",
    "REDIS__",
    "SECURITY__",
    "INIT__",
    "STORAGE__",
    "LOCAL_STORAGE__",
    "BACKUP__",
)
WAIT_SECONDS = 90.0

T = TypeVar("T")


class ScenarioError(AssertionError):
    """A step of the run did not see what it expected."""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ScenarioError(message)


def wait_for(description: str, probe: Callable[[], T | None], timeout: float = WAIT_SECONDS) -> T:
    """Polls `probe` until it answers something other than None or False."""
    deadline = time.monotonic() + timeout
    while True:
        found = probe()
        if found is not None and found is not False:
            return found
        if time.monotonic() > deadline:
            raise ScenarioError(f"Timed out after {timeout:.0f} s waiting for: {description}")
        time.sleep(1.0)


# ── The instance processes ───────────────────────────────────────────


def serve(name: str, host: str, port: int, data_dir: Path, window: str | None) -> None:
    """Runs one instance in this process: schema, seed, then uvicorn."""
    database_url = os.environ.get("DATABASE__URL", "")
    expected = f"sqlite:///{data_dir / f'{name.lower()}.db'}"
    if database_url != expected or os.environ.get("ENV_FILE"):
        raise SystemExit(f"Refusing to start {name}: the database must be {expected}.")

    import asyncio

    import uvicorn

    from src.bootstrap import main as main_module
    from src.bootstrap import shopping_jobs
    from src.cookbook.adapters.inbound.api import deps as cookbook_deps
    from src.cookbook.adapters.outbound.external.live_updates import InMemoryLivePublisher
    from src.platform.adapters.inbound.api import deps
    from src.platform.adapters.outbound.external.login_attempts import InMemoryLoginAttemptTracker
    from src.platform.adapters.outbound.external.replay_guard import InMemoryReplayGuard
    from src.platform.adapters.outbound.external.request_rate_limiter import (
        InMemoryRequestRateLimiter,
    )

    if window:
        _patch_protocol_window(main_module, tuple(int(v) for v in window.split(",")))
    asyncio.run(_prepare(name))

    live = InMemoryLivePublisher()
    attempts = InMemoryLoginAttemptTracker()
    replay = InMemoryReplayGuard()
    limiter = InMemoryRequestRateLimiter()
    setattr(shopping_jobs, "get_live", lambda: live)  # noqa: B010
    app = main_module.create_app()
    app.dependency_overrides[deps.get_login_attempts] = lambda: attempts
    app.dependency_overrides[deps.get_replay_guard] = lambda: replay
    app.dependency_overrides[deps.get_request_rate_limiter] = lambda: limiter
    app.dependency_overrides[cookbook_deps.get_live] = lambda: live
    uvicorn.run(app, host=host, port=port, log_level="warning")


def _patch_protocol_window(main_module: Any, window: tuple[int, ...]) -> None:
    """Makes this process announce and accept only `window`, as a release
    with another protocol support window would."""
    from src.platform.application.services import peering_identity
    from src.platform.application.use_cases.peering import authenticate_peer
    from src.platform.domain.value_objects import peering

    for module in (peering, peering_identity, authenticate_peer):
        setattr(module, "SUPPORTED_PROTOCOL_VERSIONS", window)  # noqa: B010
    for module in (peering, main_module):
        setattr(module, "CURRENT_PROTOCOL_VERSION", max(window))  # noqa: B010


async def _prepare(name: str) -> None:
    """Creates the schema of the fresh SQLite file and what an administrator
    would have set up before: the system user's authenticator, an instance
    name, and user choice of visibility (written straight to the settings,
    so no privacy statement version is published)."""
    from dataclasses import replace

    from src.bootstrap.models import Base
    from src.bootstrap.seed import ensure_system_user
    from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
        SqlAlchemySettingsRepository,
    )
    from src.platform.adapters.outbound.persistence.repositories.user_repository import (
        SqlAlchemyUserRepository,
    )
    from src.platform.adapters.outbound.persistence.session import SessionLocal
    from src.platform.adapters.outbound.persistence.session import engine
    from src.platform.domain.entities.settings import PrivacySettings

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_system_user()
    async with SessionLocal() as db:
        users = SqlAlchemyUserRepository(db)
        user = next((u for u in await users.list_all() if u.is_systemuser), None)
        if user is None:
            raise SystemExit("The system user was not created.")
        if not user.totp_enabled:
            user.totp_secret = TOTP_SECRET
            user.totp_enabled = True
            await users.save(user)
        settings = SqlAlchemySettingsRepository(db)
        general = await settings.get_general()
        await settings.save_general(replace(general, instance_name=f"E2E {name}"))
        privacy = await settings.get_privacy()
        if not privacy.users_may_change_visibility:
            await settings.save_privacy(
                PrivacySettings(
                    default_recipe_visibility="instance", users_may_change_visibility=True
                )
            )
        await db.commit()
    await engine.dispose()


@dataclass
class Instance:
    name: str
    host: str
    port: int
    data_dir: Path
    process: subprocess.Popen[bytes] | None = None
    admin: httpx.Client | None = None
    clients: list[httpx.Client] = field(default_factory=list)
    used_codes: set[str] = field(default_factory=set)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def admin_mail(self) -> str:
        """The system user's address, which it signs in with."""
        return f"admin-{self.name.lower()}@example.com"

    @property
    def log_path(self) -> Path:
        return self.data_dir / f"{self.name.lower()}.log"

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith(SETTINGS_PREFIXES)}
        env.update(
            {
                "DEBUG": "true",
                "DOMAIN": self.base_url,
                "LOG_LEVEL": "INFO",
                "DATABASE__URL": f"sqlite:///{self.data_dir / f'{self.name.lower()}.db'}",
                # Never contacted: every Redis user is swapped for an in-process one.
                "REDIS__URL": "redis://127.0.0.1:1/0",
                "SECURITY__SECRET_KEY": f"e2e-secret-key-{self.name}-" + "x" * 24,
                "SECURITY__ENCRYPTION_KEY": f"e2e-encryption-key-{self.name}-" + "y" * 24,
                "INIT__FULL_NAME": f"Admin {self.name}",
                "INIT__MAIL": self.admin_mail,
                "INIT__PASSWORD": ADMIN_PASSWORD,
                "STORAGE__PROVIDER": "postgres",
                "PYTHONUNBUFFERED": "1",
            }
        )
        return env

    def start(self, window: str | None = None) -> None:
        wait_for(f"port {self.port} to be free", lambda: port_is_free(self.host, self.port), 30)
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "serve",
            "--name",
            self.name,
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--data",
            str(self.data_dir),
        ]
        if window:
            command += ["--protocol-window", window]
        log = self.log_path.open("ab")
        self.process = subprocess.Popen(
            command,
            cwd=BACKEND_DIR,
            env=self.env(),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log.close()

        def ready() -> bool:
            if self.process is not None and self.process.poll() is not None:
                raise ScenarioError(f"{self.name} exited at startup, see {self.log_path}")
            try:
                return httpx.get(f"{self.base_url}/health", timeout=2).status_code == 200
            except httpx.HTTPError:
                return False

        wait_for(f"{self.name} to answer /health", ready, 60)

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self.process = None

    def client(self) -> httpx.Client:
        made = httpx.Client(base_url=self.base_url, headers=CSRF, timeout=30)
        self.clients.append(made)
        return made

    def login_admin(self) -> httpx.Client:
        if self.admin is None:
            self.admin = self.client()
        step_one = self.admin.post(
            f"{AUTH}/login", json={"login": "system", "password": ADMIN_PASSWORD}
        )
        check(step_one.status_code == 200, f"{self.name} admin login: {step_one.text}")
        check(step_one.json().get("status") == "totp_required", f"{self.name}: {step_one.text}")
        totp = pyotp.TOTP(TOTP_SECRET)
        code = wait_for(
            "an unused authenticator code",
            lambda: next(
                (
                    c
                    for c in (totp.at(time.time() + offset) for offset in (0, -30))
                    if c not in self.used_codes
                ),
                None,
            ),
            40,
        )
        self.used_codes.add(code)
        step_two = self.admin.post(
            f"{AUTH}/login/totp",
            json={"partial_token": step_one.json()["partial_token"], "code": code},
        )
        check(step_two.status_code == 200, f"{self.name} admin code: {step_two.text}")
        return self.admin

    def admin_client(self) -> httpx.Client:
        """The admin's client, signed in again when a restart lost the session."""
        if self.admin is not None and self.admin.get(f"{WEB}/users/me").status_code == 200:
            return self.admin
        return self.login_admin()

    def make_user(self, handle: str, full_name: str, permissions: list[str]) -> httpx.Client:
        email = f"{handle}@example.com"
        created = self.admin_client().post(
            f"{WEB}/users",
            json={
                "full_name": full_name,
                "email": email,
                "password": COOK_PASSWORD,
                "permissions": permissions,
            },
        )
        check(created.status_code == 201, f"{self.name} user {email}: {created.text}")
        return self.user_client(email)

    def user_client(self, email: str) -> httpx.Client:
        made = self.client()
        signed_in = made.post(f"{AUTH}/login", json={"login": email, "password": COOK_PASSWORD})
        check(signed_in.status_code == 200, f"{self.name} login {email}: {signed_in.text}")
        return made

    def close_clients(self) -> None:
        for made in self.clients:
            made.close()
        self.clients.clear()
        self.admin = None


def port_is_free(host: str, port: int) -> bool:
    """Whether a server could listen on the port now. Connections of the
    previous run in TIME_WAIT do not count, as uvicorn reuses the address."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


# The ports of the dev stacks (backend and frontend of two instances), never
# taken even when free, so a run cannot stand in for a developer's stack.
DEV_PORTS = frozenset({3000, 3001, 5173, 5174})


def free_port(host: str) -> int:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((host, 0))
            port: int = probe.getsockname()[1]
        if port not in DEV_PORTS:
            return port


def private_address() -> str:
    """The host's own address on its default route, which the target guard
    accepts as a private network address."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("10.255.255.255", 1))
        address: str = probe.getsockname()[0]
    if address.startswith("127."):
        raise SystemExit("No non-loopback address found; pass --host.")
    return address


# ── The scenario ─────────────────────────────────────────────────────


def ok(response: httpx.Response, *expected: int) -> Any:
    codes = expected or (200,)
    check(
        response.status_code in codes,
        f"{response.request.method} {response.request.url.path} answered "
        f"{response.status_code}: {response.text[:500]}",
    )
    return response.json() if response.content else None


class Scenario:
    def __init__(self, a: Instance, b: Instance) -> None:
        self.a = a
        self.b = b
        self.steps: list[tuple[str, bool, str]] = []

    def step(self, title: str, run: Callable[[], None]) -> None:
        print(f"-- {title}", flush=True)
        started = time.monotonic()
        try:
            run()
        except Exception as error:
            self.steps.append((title, False, str(error)))
            print(f"   FAILED: {error}", flush=True)
            raise
        self.steps.append((title, True, f"{time.monotonic() - started:.1f} s"))
        print(f"   ok ({time.monotonic() - started:.1f} s)", flush=True)

    # Shared state between the steps.
    b_on_a: str = ""
    a_on_b: str = ""
    cook: httpx.Client
    reader: httpx.Client
    forker: httpx.Client
    ingredients: dict[str, str]
    unit_g: str = ""
    recipe_id: str = ""
    mirror_id: str = ""
    second_id: str = ""

    def run(self) -> None:
        self.step("start A and B", self.start)
        self.step("admins enable peering", self.enable_peering)
        self.step("A invites, B accepts the invitation", self.pair)
        self.step("A's cook shares a recipe with a variation", self.share)
        self.step("B's admin accepts it with create, map and plain", self.accept)
        self.step("B's users see the mirror with attribution", self.mirror_visible)
        self.step("an update on A reaches the mirror by itself", self.update)
        self.step("a new unknown ingredient holds the update", self.held_update)
        self.step("unsharing on A removes the mirror", self.unshare)
        self.step("B catches up after being offline", self.offline_catch_up)
        self.step("a protocol version mismatch is refused and recovers", self.version_mismatch)
        self.step("a recipe set to paired instances reaches B", self.peers_visibility)
        self.step("sync all on B takes A's recipes in at once", self.sync_all)
        self.step("revoking on A clears B", self.revoke)

    # ── Steps ────────────────────────────────────────────────────────

    def start(self) -> None:
        self.a.start()
        self.b.start()
        for side in (self.a, self.b):
            side.login_admin()

    def enable_peering(self) -> None:
        for side in (self.a, self.b):
            admin = side.admin_client()
            features = ok(admin.get(f"{WEB}/settings/features"))
            ok(admin.put(f"{WEB}/settings/features", json={**features, "peering": True}))
            notifications = ok(admin.get(f"{WEB}/settings/notifications"))
            check(
                notifications["allow_private_webhook_targets"] is True,
                "private network targets are off by default",
            )
            own = ok(admin.get(f"{WEB}/admin/peers/self"))
            check(own["base_url"] == side.base_url, f"{side.name} announces {own['base_url']}")

    def pair(self) -> None:
        a, b = self.a.admin_client(), self.b.admin_client()
        invitation = ok(a.post(f"{WEB}/admin/peers/invitations"), 200, 201)
        link = invitation["link"]
        check(link.startswith(f"{self.a.base_url}/peering/accept?code="), link)
        ok(b.post(f"{WEB}/admin/peers/accept", json={"invitation_url": link}), 200, 201)
        (peer_b,) = ok(a.get(f"{WEB}/admin/peers"))
        (peer_a,) = ok(b.get(f"{WEB}/admin/peers"))
        check(peer_b["name"] == "E2E B" and peer_b["status"] == "active", str(peer_b))
        check(peer_a["name"] == "E2E A" and peer_a["status"] == "active", str(peer_a))
        check(peer_a["protocol_version"] == 1, str(peer_a))
        self.b_on_a, self.a_on_b = peer_b["id"], peer_a["id"]
        # A new pairing takes the peer's recipes in at once; the next steps
        # drive B's accept queue, so B's admin switches that off first.
        check(peer_a["sync_all"] is True, "a new pairing does not start with sync all on")
        self._switches(sync_all=False)
        # A used invitation cannot pair again.
        again = b.post(f"{WEB}/admin/peers/accept", json={"invitation_url": link})
        check(again.status_code >= 400, "a used invitation paired again")

    def _ingredient(self, side: Instance, name: str) -> str:
        created = ok(
            side.admin_client().post(
                f"{WEB}/ingredients",
                json={
                    "original_locale": "de-AT",
                    "translations": {"de-AT": {"name": name, "plural_name": name}},
                    "nutrition": {"kcal": 120},
                    "allergens": ["celery"] if "gewürz" in name.lower() else [],
                },
            ),
            201,
        )
        return str(created["id"])

    def _body(self, title: str, lines: list[tuple[str, float]], **extra: Any) -> dict[str, Any]:
        return {
            "original_locale": "de-AT",
            "translations": {"de-AT": {"title": title, "description": "Ein Test."}},
            "base_servings": 4,
            "steps": [
                {
                    "translations": {"de-AT": {"text": "Alles vermengen und kochen."}},
                    "ingredients": [
                        {
                            "ingredient_id": self.ingredients[n],
                            "amount": amount,
                            "unit_id": self.unit_g,
                        }
                        for n, amount in lines
                    ],
                }
            ],
            **extra,
        }

    def _shared(self) -> dict[str, Any]:
        return {"visibility": "shared", "shared_peer_ids": [self.b_on_a]}

    def share(self) -> None:
        self.cook = self.a.make_user("anna", "Anna Source", ["write:recipes", "write:ingredients"])
        self.reader = self.b.make_user("bert", "Bert Reader", [])
        self.forker = self.b.make_user("berta", "Berta Forker", ["write:recipes"])
        self.ingredients = {
            name: self._ingredient(self.a, name)
            for name in (
                "E2E Bergkräuter",
                "E2E Speck",
                "E2E Hausgewürz",
                "E2E Zitronengras",
                "E2E Kürbis",
                "E2E Ingwer",
            )
        }
        self.ingredients["local Speck"] = self._ingredient(self.b, "E2E Lokaler Speck")
        units = ok(self.a.admin_client().get(f"{WEB}/units"))
        self.unit_g = next(str(u["id"]) for u in units if u["code"] == "g")
        targets = ok(self.cook.get(f"{WEB}/peers/share-targets"))
        check([t["id"] for t in targets] == [self.b_on_a], f"share targets: {targets}")
        body = self._body(
            "E2E Knödel",
            [("E2E Bergkräuter", 20), ("E2E Speck", 100), ("E2E Hausgewürz", 5)],
            **self._shared(),
        )
        recipe = ok(self.cook.post(f"{WEB}/recipes", json=body), 201)
        self.recipe_id = recipe["id"]
        ok(self.cook.post(f"{WEB}/recipes/{self.recipe_id}/publish"))
        ok(
            self.cook.post(
                f"{WEB}/recipes/{self.recipe_id}/variations",
                json={"name": "Scharf", "locale": "de-AT", "note": "Mehr Gewürz", "changes": []},
            ),
            201,
        )

    def _incoming(self, status: str = "pending") -> list[dict[str, Any]]:
        listed: list[dict[str, Any]] = ok(
            self.b.admin_client().get(f"{WEB}/admin/incoming-recipes", params={"status": status})
        )
        return listed

    def _waiting(self, source_id: str, kind: str = "new") -> dict[str, Any]:
        def probe() -> dict[str, Any] | None:
            return next(
                (i for i in self._incoming() if i["source_id"] == source_id and i["kind"] == kind),
                None,
            )

        return wait_for(f"B to list {source_id} as a waiting {kind} recipe", probe)

    def _decisions(self, item: dict[str, Any], choices: dict[str, dict[str, Any]]) -> list[Any]:
        decisions = []
        for entry in item["entries"]:
            choice = choices.get(entry["name"])
            check(choice is not None, f"no decision for {entry['kind']} {entry['name']}")
            decisions.append(
                {"kind": entry["kind"], "source_id": entry["source_id"], **(choice or {})}
            )
        return decisions

    def accept(self) -> None:
        item = self._waiting(self.recipe_id)
        check(item["author_name"] == "Anna Source", f"author: {item['author_name']}")
        names = {e["name"] for e in item["entries"]}
        check(
            names == {"E2E Bergkräuter", "E2E Speck", "E2E Hausgewürz"},
            f"entries needing a decision: {names} (the unit g matches by seed key)",
        )
        # Nothing is visible to B's users before the admin accepted.
        listed = ok(self.reader.get(f"{WEB}/recipes"))["items"]
        check(all(r["title"] != "E2E Knödel" for r in listed), "visible before acceptance")
        decisions = self._decisions(
            item,
            {
                "E2E Bergkräuter": {"action": "create"},
                "E2E Speck": {"action": "map", "target_id": self.ingredients["local Speck"]},
                "E2E Hausgewürz": {"action": "plain"},
            },
        )
        accepted = ok(
            self.b.admin_client().post(
                f"{WEB}/admin/incoming-recipes/{item['id']}/accept", json={"decisions": decisions}
            )
        )
        self.mirror_id = accepted["id"]
        check(self._incoming() == [], "the accepted recipe is still waiting")

    def _mirror(self, client: httpx.Client | None = None) -> httpx.Response:
        return (client or self.reader).get(f"{WEB}/recipes/{self.mirror_id}")

    def mirror_visible(self) -> None:
        listed = ok(self.reader.get(f"{WEB}/recipes"))["items"]
        card = next((r for r in listed if r["id"] == self.mirror_id), None)
        check(card is not None, "the mirror is not in B's recipe list")
        assert card is not None
        check(
            {k: card["mirror"].get(k) for k in ("instance_name", "author_name")}
            == {"instance_name": "E2E A", "author_name": "Anna Source"},
            str(card["mirror"]),
        )
        detail = ok(self._mirror())
        details = detail["mirror_details"]
        check(details["instance_name"] == "E2E A", str(details))
        check(details["source_url"].startswith(self.a.base_url), details["source_url"])
        check(detail["can_edit"] is False and detail["can_delete"] is False, "mirror is editable")
        check([p["name"] for p in details["plain_lines"]] == ["E2E Hausgewürz"], str(details))
        check("celery" in details["plain_lines"][0]["allergens"], "plain line lost its allergen")
        lines = [i["name"] for i in detail.get("ingredients", [])]
        check(
            any("Lokaler Speck" in n for n in lines) and any("Bergkräuter" in n for n in lines),
            f"mapped and created lines: {lines}",
        )

        # The variation was added after publishing, so it may reach B as a
        # later update of the accepted mirror.
        def mirrored_variations() -> list[tuple[str, bool]] | None:
            variations = ok(self.reader.get(f"{WEB}/recipes/{self.mirror_id}/variations"))
            names = [(v["name"], v["mirrored"]) for v in variations]
            return names if names == [("Scharf", True)] else None

        wait_for("the mirrored variation on B", mirrored_variations, 60)
        refused = self.forker.put(
            f"{WEB}/recipes/{self.mirror_id}", json=self._body("Geändert", [])
        )
        check(refused.status_code in (403, 409), f"mirror write answered {refused.status_code}")

    def _wait_title(self, title: str) -> None:
        def probe() -> bool:
            answer = self._mirror()
            return answer.status_code == 200 and answer.json()["title"] == title

        wait_for(f"B's mirror to read {title!r}", probe)

    def update(self) -> None:
        body = self._body(
            "E2E Knödel mit mehr Speck",
            [("E2E Bergkräuter", 20), ("E2E Speck", 150), ("E2E Hausgewürz", 5)],
            **self._shared(),
        )
        ok(self.cook.put(f"{WEB}/recipes/{self.recipe_id}", json=body))
        self._wait_title("E2E Knödel mit mehr Speck")
        check(self._incoming() == [], "an all-mapped update waited for the admin")

    def held_update(self) -> None:
        body = self._body(
            "E2E Knödel mit Zitronengras",
            [
                ("E2E Bergkräuter", 20),
                ("E2E Speck", 150),
                ("E2E Hausgewürz", 5),
                ("E2E Zitronengras", 3),
            ],
            **self._shared(),
        )
        ok(self.cook.put(f"{WEB}/recipes/{self.recipe_id}", json=body))
        item = self._waiting(self.recipe_id, kind="update")
        check([e["name"] for e in item["entries"]] == ["E2E Zitronengras"], str(item["entries"]))
        check(item["mirror_id"] == self.mirror_id, "the held update names another mirror")
        check(
            ok(self._mirror())["title"] == "E2E Knödel mit mehr Speck",
            "the mirror changed before the admin decided",
        )
        decisions = self._decisions(item, {"E2E Zitronengras": {"action": "create"}})
        ok(
            self.b.admin_client().post(
                f"{WEB}/admin/incoming-recipes/{item['id']}/accept", json={"decisions": decisions}
            )
        )
        self._wait_title("E2E Knödel mit Zitronengras")

    def _lines(self) -> list[tuple[str, float]]:
        return [
            ("E2E Bergkräuter", 20),
            ("E2E Speck", 150),
            ("E2E Hausgewürz", 5),
            ("E2E Zitronengras", 3),
        ]

    def unshare(self) -> None:
        body = self._body("E2E Knödel mit Zitronengras", self._lines(), visibility="instance")
        ok(self.cook.put(f"{WEB}/recipes/{self.recipe_id}", json=body))
        wait_for("B's mirror to be removed", lambda: self._mirror().status_code == 404)
        listed = ok(self.reader.get(f"{WEB}/recipes"))["items"]
        check(all(r["id"] != self.mirror_id for r in listed), "the withdrawn mirror is listed")

    def offline_catch_up(self) -> None:
        # Shared again: a new mirror after the admin accepts, with the
        # earlier decisions reused, so nothing needs a decision.
        body = self._body("E2E Knödel wieder da", self._lines(), **self._shared())
        ok(self.cook.put(f"{WEB}/recipes/{self.recipe_id}", json=body))
        item = self._waiting(self.recipe_id)
        check(item["entries"] == [], f"saved mappings were not reused: {item['entries']}")
        accepted = ok(
            self.b.admin_client().post(
                f"{WEB}/admin/incoming-recipes/{item['id']}/accept", json={"decisions": []}
            )
        )
        self.mirror_id = accepted["id"]
        self._wait_title("E2E Knödel wieder da")

        self.b.stop()
        body = self._body("E2E Knödel offline geändert", self._lines(), **self._shared())
        ok(self.cook.put(f"{WEB}/recipes/{self.recipe_id}", json=body))
        second = ok(
            self.cook.post(
                f"{WEB}/recipes",
                json=self._body("E2E Zweites Rezept", [("E2E Speck", 50)], **self._shared()),
            ),
            201,
        )
        self.second_id = second["id"]
        ok(self.cook.post(f"{WEB}/recipes/{self.second_id}/publish"))

        def delivery_failed() -> bool:
            (peer,) = ok(self.a.admin_client().get(f"{WEB}/admin/peers"))
            channel = peer["channel"] or {}
            return bool(channel.get("last_delivery_error")) and channel["pending_outgoing"] > 0

        wait_for("A to notice that B is unreachable", delivery_failed, 30)
        self.b.start()
        # A retries only after a minute; B's catch-up, made due by its
        # admin's "sync now" as its timer would, gets there first.
        ok(self.b.admin_client().post(f"{WEB}/admin/peers/{self.a_on_b}/sync"), 200, 202, 204)
        self._wait_title("E2E Knödel offline geändert")
        self._waiting(self.second_id)
        # A's own retry, made due by its admin, then delivers what B already
        # has; B takes those events as duplicates.
        ok(self.a.admin_client().post(f"{WEB}/admin/peers/{self.b_on_a}/sync"), 200, 202, 204)
        wait_for("A to deliver its queued events", self._a_delivered, 30)

    def _a_delivered(self) -> bool:
        (peer,) = ok(self.a.admin_client().get(f"{WEB}/admin/peers"))
        channel = peer["channel"] or {}
        return channel.get("pending_outgoing") == 0 and not channel.get("last_delivery_error")

    def version_mismatch(self) -> None:
        a_admin = self.a.admin_client()
        self.b.stop()
        self.b.start(window="2,3")
        # B's identity changed, so it tells A at startup; A reads B's /hello,
        # which B now refuses for protocol 1.
        hello = httpx.get(f"{self.b.base_url}/api/peering/v1/hello", timeout=5)
        check(hello.headers.get("Cuisine-Peering-Version") == "3", str(hello.headers))
        refreshed = a_admin.post(f"{WEB}/admin/peers/{self.b_on_a}/refresh")
        check(refreshed.status_code >= 400, f"refresh with B on 2..3 answered {refreshed.text}")
        print(f"   refresh refused: {refreshed.status_code} {refreshed.json().get('code')}")
        (peer,) = ok(a_admin.get(f"{WEB}/admin/peers"))
        check(peer["protocol_version"] == 1 and peer["status"] == "active", str(peer))

        body = self._body("E2E Knödel nach dem Update", self._lines(), **self._shared())
        ok(self.cook.put(f"{WEB}/recipes/{self.recipe_id}", json=body))
        ok(a_admin.post(f"{WEB}/admin/peers/{self.b_on_a}/sync"), 200, 202, 204)

        def refused() -> dict[str, Any] | None:
            (peer,) = ok(a_admin.get(f"{WEB}/admin/peers"))
            channel: dict[str, Any] = peer["channel"] or {}
            return channel if channel.get("last_delivery_status") == 422 else None

        channel = wait_for("B to refuse A's event for protocol 1", refused, 30)
        print(
            "   delivery refused:",
            channel["last_delivery_status"],
            channel["last_delivery_error"],
        )
        check(
            ok(self._mirror())["title"] == "E2E Knödel offline geändert",
            "the mirror changed while the versions did not overlap",
        )

        self.b.stop()
        self.b.start()

        def renegotiated() -> bool:
            (peer,) = ok(a_admin.get(f"{WEB}/admin/peers"))
            return peer["protocol_version"] == 1 and bool(peer["last_contact_at"])

        wait_for("A to talk to B again", renegotiated, 30)
        ok(a_admin.post(f"{WEB}/admin/peers/{self.b_on_a}/refresh"))
        ok(a_admin.post(f"{WEB}/admin/peers/{self.b_on_a}/sync"), 200, 202, 204)
        self._wait_title("E2E Knödel nach dem Update")
        wait_for("A to deliver its queued events", self._a_delivered, 30)

    def _switches(self, *, sync_all: bool) -> dict[str, Any]:
        answer: dict[str, Any] = ok(
            self.b.admin_client().put(
                f"{WEB}/admin/peers/{self.a_on_b}/switches",
                json={
                    "users_may_share": True,
                    "accept_incoming": True,
                    "mirror_visibility": "instance",
                    "sync_all": sync_all,
                },
            )
        )
        check(answer["sync_all"] is sync_all, str(answer))
        check("send_all_public" not in answer, "the removed switch is still answered")
        return answer

    def _listed_on_b(self, title: str) -> dict[str, Any] | None:
        items: list[dict[str, Any]] = ok(self.reader.get(f"{WEB}/recipes"))["items"]
        return next((r for r in items if r["title"] == title), None)

    def peers_visibility(self) -> None:
        # Not shared with B one by one: the visibility alone sends it.
        body = self._body(
            "E2E Für alle Instanzen",
            [("E2E Speck", 80), ("E2E Kürbis", 200)],
            visibility="peers",
        )
        recipe = ok(self.cook.post(f"{WEB}/recipes", json=body), 201)
        check(recipe["visibility"] == "peers", f"stored as {recipe['visibility']}")
        ok(self.cook.post(f"{WEB}/recipes/{recipe['id']}/publish"))
        detail = ok(self.cook.get(f"{WEB}/recipes/{recipe['id']}"))
        check(detail["effective_visibility"] == "peers", str(detail["effective_visibility"]))
        item = self._waiting(recipe["id"])
        check(
            [e["name"] for e in item["entries"]] == ["E2E Kürbis"],
            f"only the new ingredient needs a decision: {item['entries']}",
        )

    def sync_all(self) -> None:
        # Switched on, nothing that waits is taken in by itself; the admin's
        # "accept everything that waits" takes the second recipe and the
        # peers recipe, with automatic decisions.
        self._switches(sync_all=True)
        check(len(self._incoming()) == 2, f"waiting: {self._incoming()}")
        accepted = ok(
            self.b.admin_client().post(f"{WEB}/admin/peers/{self.a_on_b}/incoming-recipes/accept")
        )
        check(accepted == {"accepted": 2}, str(accepted))
        check(self._incoming() == [], "recipes still wait after accepting everything")
        check(
            self._listed_on_b("E2E Für alle Instanzen") is not None, "the peers recipe is missing"
        )

        # A new recipe with an unknown ingredient becomes a mirror at once;
        # the ingredient is created as a draft for B's review queue.
        body = self._body("E2E Sofort da", [("E2E Ingwer", 15)], **self._shared())
        created = ok(self.cook.post(f"{WEB}/recipes", json=body), 201)
        ok(self.cook.post(f"{WEB}/recipes/{created['id']}/publish"))
        wait_for("B to show the recipe at once", lambda: self._listed_on_b("E2E Sofort da"))
        check(self._incoming() == [], "a recipe waited although sync all is on")
        found = ok(self.b.admin_client().get(f"{WEB}/ingredients", params={"search": "E2E Ingwer"}))
        check(
            [i["status"] for i in found["items"]] == ["draft"],
            f"the created ingredient: {found['items']}",
        )
        mappings = ok(self.b.admin_client().get(f"{WEB}/admin/peers/{self.a_on_b}/mappings"))
        ginger = next((m for m in mappings if m["name"] == "E2E Ingwer"), None)
        check(
            ginger is not None and ginger["action"] == "map" and ginger["created_here"],
            f"the automatic decision is not saved: {ginger}",
        )

        # Off again: the next recipe waits for the admin.
        self._switches(sync_all=False)
        body = self._body("E2E Wartet wieder", [("E2E Speck", 40)], **self._shared())
        waiting = ok(self.cook.post(f"{WEB}/recipes", json=body), 201)
        ok(self.cook.post(f"{WEB}/recipes/{waiting['id']}/publish"))
        self._waiting(waiting["id"])

    def revoke(self) -> None:
        fork = ok(self.forker.post(f"{WEB}/recipes/{self.mirror_id}/copy"), 201)
        check(fork["peer_capped"] is True, "the fork of a mirror is not capped")
        check(len(self._incoming()) == 1, "the last shared recipe is not waiting on B")
        mappings = ok(self.b.admin_client().get(f"{WEB}/admin/peers/{self.a_on_b}/mappings"))
        check(len(mappings) > 0, "B holds no mappings before the revoke")

        revoked = ok(self.a.admin_client().post(f"{WEB}/admin/peers/{self.b_on_a}/revoke"))
        check(revoked["peer_notified"] is True, "B was not told about the revoke")
        b_admin = self.b.admin_client()
        (peer,) = ok(b_admin.get(f"{WEB}/admin/peers"))
        check(peer["status"] == "revoked" and peer["revoked_by"] == "remote", str(peer))
        check(self._mirror().status_code == 404, "the mirror survived the revoke")
        check(self._incoming() == [], "a waiting recipe survived the revoke")
        after = b_admin.get(f"{WEB}/admin/peers/{self.a_on_b}/mappings")
        check(
            after.status_code == 404 or after.json() == [],
            f"mappings survived the revoke: {after.text[:300]}",
        )
        check(
            self.forker.get(f"{WEB}/recipes/{fork['id']}").status_code == 200,
            "the fork went with the mirror",
        )
        targets = ok(self.cook.get(f"{WEB}/peers/share-targets"))
        check(targets == [], f"a revoked peer is still a share target: {targets}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command")
    serve_args = sub.add_parser("serve", help="internal: run one instance")
    serve_args.add_argument("--name", required=True)
    serve_args.add_argument("--host", required=True)
    serve_args.add_argument("--port", type=int, required=True)
    serve_args.add_argument("--data", type=Path, required=True)
    serve_args.add_argument("--protocol-window", default=None)
    parser.add_argument("--host", default=None, help="the address both instances listen on")
    parser.add_argument("--keep", action="store_true", help="keep the folder with the logs")
    args = parser.parse_args()

    if args.command == "serve":
        serve(args.name, args.host, args.port, args.data, args.protocol_window)
        return 0

    host = args.host or private_address()
    data_dir = Path(tempfile.mkdtemp(prefix="cuisine-e2e-peering-"))
    port_a = free_port(host)
    port_b = free_port(host)
    while port_b == port_a:
        port_b = free_port(host)
    a = Instance("A", host, port_a, data_dir)
    b = Instance("B", host, port_b, data_dir)
    print(f"A on {a.base_url}, B on {b.base_url}, data in {data_dir}", flush=True)
    scenario = Scenario(a, b)
    failed = False

    def stop_on_term(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_on_term)
    try:
        scenario.run()
    except (Exception, KeyboardInterrupt) as error:
        failed = True
        print(f"\nThe run stopped: {type(error).__name__}: {error}", flush=True)
        for side in (a, b):
            if side.log_path.exists():
                tail = side.log_path.read_text(errors="replace").splitlines()[-40:]
                print(f"\n--- last lines of {side.name}'s log ---\n" + "\n".join(tail))
    finally:
        for side in (a, b):
            side.close_clients()
            side.stop()
        if args.keep:
            print(f"Kept {data_dir}")
        else:
            shutil.rmtree(data_dir, ignore_errors=True)
    print("\nSummary:")
    for title, passed, note in scenario.steps:
        print(f"  {'PASS' if passed else 'FAIL'}  {title}  ({note})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
