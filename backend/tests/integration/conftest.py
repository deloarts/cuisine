"""
The app under test: a fresh schema per test on the throwaway SQLite file,
the in-process throttle and replay guard, and an httpx client that talks to
the ASGI app directly. The lifespan is not run; the system user is seeded
by the `login_system` fixture instead, with two-factor authentication already
set up, since the system user never gets a session without its code.
"""

import time
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

import httpx
import pyotp
import pytest

from src.bootstrap.cookbook_seed import ensure_reference_data
from src.bootstrap.main import create_app
from src.bootstrap.models import Base
from src.bootstrap.seed import ensure_system_user
from src.cookbook.adapters.inbound.api import deps as cookbook_deps
from src.cookbook.adapters.outbound.external.live_updates import InMemoryLivePublisher
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.ports.outbound.nutrition_lookup import FoodMatch
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.inbound.api.middleware.maintenance import maintenance_state
from src.platform.adapters.inbound.api.privacy_gate import privacy_state
from src.platform.adapters.outbound.external.authorization_codes import (
    InMemoryAuthorizationCodeStore,
)
from src.platform.adapters.outbound.external.login_attempts import InMemoryLoginAttemptTracker
from src.platform.adapters.outbound.external.replay_guard import InMemoryReplayGuard
from src.platform.adapters.outbound.external.request_rate_limiter import InMemoryRequestRateLimiter
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.session import engine
from src.platform.const import CSRF_HEADER_NAME
from src.platform.const import CSRF_HEADER_VALUE
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.user import User
from src.platform.infrastructure.config.settings import cfg

ADMIN = {"login": "system", "password": "admin-password-1"}
# The authenticator secret the `login_system` fixture sets up for the system user.
SYSTEM_TOTP_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
CSRF = {CSRF_HEADER_NAME: CSRF_HEADER_VALUE}


@pytest.fixture(autouse=True)
def _fresh_request_caches() -> None:
    """The per-worker caches of maintenance mode and the privacy statement
    version read the database of the test before; forget them."""
    maintenance_state.forget()
    privacy_state.forget()


@pytest.fixture(autouse=True)
async def _schema() -> AsyncIterator[None]:
    assert cfg.database.url.startswith("sqlite"), "Tests only ever run on SQLite."
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
def attempts() -> InMemoryLoginAttemptTracker:
    return InMemoryLoginAttemptTracker()


@pytest.fixture
def replay() -> InMemoryReplayGuard:
    return InMemoryReplayGuard()


class FakeNutritionLookup:
    """Stands in for USDA FoodData Central; records the key it was given."""

    def __init__(self) -> None:
        self.keys: list[str] = []
        self.food = FoodMatch(
            fdc_id=171287,
            description="Egg, whole, raw, fresh",
            data_type="SR Legacy",
            brand=None,
            nutrition=Nutrition(kcal=143, protein=12.6, fat=9.5, carbohydrates=0.7, salt=0.36),
        )

    async def search(self, query: str, *, api_key: str, limit: int) -> list[FoodMatch]:
        self.keys.append(api_key)
        return [self.food] if "egg" in query.lower() else []

    async def get(self, fdc_id: int, *, api_key: str) -> FoodMatch | None:
        self.keys.append(api_key)
        return self.food if fdc_id == self.food.fdc_id else None


@pytest.fixture
def live() -> InMemoryLivePublisher:
    return InMemoryLivePublisher()


@pytest.fixture
def usda() -> FakeNutritionLookup:
    return FakeNutritionLookup()


def _app(
    attempts: InMemoryLoginAttemptTracker,
    replay: InMemoryReplayGuard,
    live: InMemoryLivePublisher,
    usda: FakeNutritionLookup,
) -> Any:
    app = create_app()
    app.dependency_overrides[deps.get_login_attempts] = lambda: attempts
    app.dependency_overrides[deps.get_replay_guard] = lambda: replay
    limiter = InMemoryRequestRateLimiter()
    app.dependency_overrides[deps.get_request_rate_limiter] = lambda: limiter
    codes = InMemoryAuthorizationCodeStore()
    app.dependency_overrides[deps.get_authorization_codes] = lambda: codes
    app.dependency_overrides[cookbook_deps.get_live] = lambda: live
    app.dependency_overrides[cookbook_deps.get_nutrition_lookup] = lambda: usda
    return app


@pytest.fixture
async def client(
    attempts: InMemoryLoginAttemptTracker,
    replay: InMemoryReplayGuard,
    live: InMemoryLivePublisher,
    usda: FakeNutritionLookup,
) -> AsyncIterator[httpx.AsyncClient]:
    app = _app(attempts, replay, live, usda)
    transport = httpx.ASGITransport(app=app)
    # https, so the Secure session cookie is sent back like a browser would.
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as c:
        yield c


type LoginSystem = Callable[[httpx.AsyncClient], Awaitable[dict[str, Any]]]


async def system_user(users: SqlAlchemyUserRepository) -> User | None:
    """The system user of the database behind the repository, found by its
    flag, so a test may change its address."""
    return next((u for u in await users.list_all() if u.is_systemuser), None)


async def _enrol_system_totp() -> None:
    async with SessionLocal() as db:
        users = SqlAlchemyUserRepository(db)
        user = await users.get_by_login(ADMIN["login"])
        assert user is not None
        if not user.totp_enabled:
            user.totp_secret = SYSTEM_TOTP_SECRET
            user.totp_enabled = True
            await users.save(user)
            await db.commit()


@pytest.fixture
def login_system() -> LoginSystem:
    """Signs a client in as the system user: password, then a code. The
    replay guard accepts each code once, so every sign-in within a test uses
    the code of another 30 second step the verifier still accepts."""
    used: set[str] = set()

    async def _login(client: httpx.AsyncClient) -> dict[str, Any]:
        await ensure_system_user()
        await _enrol_system_totp()
        step_one = await login(client, **ADMIN)
        assert step_one["status"] == "totp_required", step_one
        totp = pyotp.TOTP(SYSTEM_TOTP_SECRET)
        now = time.time()
        code = next(c for c in (totp.at(now + offset) for offset in (0, 30, -30)) if c not in used)
        used.add(code)
        response = await client.post(
            "/api/v1/auth/login/totp",
            json={"partial_token": step_one["partial_token"], "code": code},
        )
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    return _login


@pytest.fixture
async def admin(client: httpx.AsyncClient, login_system: LoginSystem) -> httpx.AsyncClient:
    """The client, signed in as the system user."""
    await login_system(client)
    return client


async def login(client: httpx.AsyncClient, login: str, password: str) -> dict[str, Any]:
    """Step one of the web login with an e-mail address, or `system`."""
    response = await client.post("/api/v1/auth/login", json={"login": login, "password": password})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def enrol_at_login(client: httpx.AsyncClient, setup_token: str) -> pyotp.TOTP:
    """Completes the enrolment a login forced with `totp_setup_required`,
    which starts the session, and returns the account's authenticator."""
    bearer = {"Authorization": f"Bearer {setup_token}"}
    enrolment = await client.post("/api/v1/web/users/me/totp/enroll", headers=bearer)
    assert enrolment.status_code == 200, enrolment.text
    totp = pyotp.TOTP(enrolment.json()["secret"])
    confirmed = await client.post(
        "/api/v1/web/users/me/totp/confirm", headers=bearer, json={"code": totp.now()}
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["session_started"] is True
    return totp


type MakeUser = Callable[..., Awaitable[dict[str, Any]]]


@pytest.fixture
def make_user(admin: httpx.AsyncClient) -> MakeUser:
    """Creates an account through the admin API and returns it. The name
    gives the full name and the address, `cook` becomes `cook@example.com`."""

    async def _make(
        name: str = "cook",
        password: str = "cook-password-1",
        permissions: list[str] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        response = await admin.post(
            "/api/v1/web/users",
            headers=CSRF,
            json={
                "full_name": name.title(),
                "email": f"{name}@example.com",
                "password": password,
                "permissions": permissions or [],
                **extra,
            },
        )
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body

    return _make


@pytest.fixture
async def other_client(
    attempts: InMemoryLoginAttemptTracker,
    replay: InMemoryReplayGuard,
    live: InMemoryLivePublisher,
    usda: FakeNutritionLookup,
) -> AsyncIterator[httpx.AsyncClient]:
    """A second browser, with its own cookie jar."""
    app = _app(attempts, replay, live, usda)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as c:
        yield c


@pytest.fixture
async def visitor(
    attempts: InMemoryLoginAttemptTracker,
    replay: InMemoryReplayGuard,
    live: InMemoryLivePublisher,
    usda: FakeNutritionLookup,
) -> AsyncIterator[httpx.AsyncClient]:
    """A browser that never signs in, for the public pages."""
    app = _app(attempts, replay, live, usda)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as c:
        yield c


@pytest.fixture
async def resources() -> None:
    """The default units, tags and categories, as the app seeds them. The
    base ingredients are left out, so tests see only their own."""
    await ensure_reference_data(ingredients=False)


COOK_PERMISSIONS = ["write:recipes", "write:ingredients"]


@pytest.fixture
async def cook(
    make_user: MakeUser, other_client: httpx.AsyncClient, resources: None
) -> httpx.AsyncClient:
    """A second browser signed in as "cook", who writes recipes and
    ingredients but manages nothing."""
    await make_user("cook", permissions=COOK_PERMISSIONS)
    await login(other_client, "cook@example.com", "cook-password-1")
    return other_client


@pytest.fixture
async def user_choice_privacy() -> None:
    """Lets users choose a recipe's visibility, for tests of private,
    household and shared recipes; a fresh instance runs in instance mode.
    Written straight to the settings, so no privacy statement version is
    published."""
    async with SessionLocal() as db:
        await SqlAlchemySettingsRepository(db).save_privacy(
            PrivacySettings(default_recipe_visibility="instance", users_may_change_visibility=True)
        )
        await db.commit()
