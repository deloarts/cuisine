"""The system user: found by its flag, its sync to the INIT__ values on every
start, its mandatory second factor and its sessions that end 15 minutes after
sign-in."""

from datetime import datetime
from datetime import timedelta

import httpx
import pyotp

from src.bootstrap.seed import ensure_system_user
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.infrastructure.config.settings import InitSettings
from src.platform.infrastructure.security.cookies import SESSION_COOKIE
from src.platform.infrastructure.security.cookies import TRUSTED_DEVICE_COOKIE
from src.platform.infrastructure.security.hashing import BcryptPasswordHasher
from tests.integration.conftest import ADMIN
from tests.integration.conftest import CSRF
from tests.integration.conftest import SYSTEM_TOTP_SECRET
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.conftest import system_user

WEB = "/api/v1/web"


async def test_the_system_user_signs_in_as_system_or_with_the_init_address(
    client: httpx.AsyncClient,
) -> None:
    assert await ensure_system_user()
    assert not await ensure_system_user()
    async with SessionLocal() as db:
        users = SqlAlchemyUserRepository(db)
        by_name = await users.get_by_login("System")
        by_mail = await users.get_by_login("admin@example.com")
    assert by_name is not None and by_name.is_systemuser
    assert by_mail is not None and by_mail.id == by_name.id
    assert (await login(client, "system", ADMIN["password"]))["status"] == "totp_setup_required"
    assert (await login(client, "admin@example.com", ADMIN["password"]))["status"] == (
        "totp_setup_required"
    )


async def test_only_the_system_user_signs_in_as_system(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    refused = await other_client.post(
        "/api/v1/auth/login", json={"login": "system", "password": "cook-password-1"}
    )
    assert refused.status_code == 401


async def test_every_start_syncs_it_back_to_the_init_values(
    client: httpx.AsyncClient,
) -> None:
    await ensure_system_user()
    async with SessionLocal() as db:
        users = SqlAlchemyUserRepository(db)
        user = await system_user(users)
        assert user is not None
        user.full_name = "Someone Else"
        user.email = "drifted@example.com"
        user.hashed_password = await BcryptPasswordHasher().hash("changed-in-the-app-1")
        user.is_active = False
        await users.save(user)
        await db.commit()

    assert not await ensure_system_user()
    async with SessionLocal() as db:
        synced = await system_user(SqlAlchemyUserRepository(db))
    assert synced is not None
    assert synced.full_name == "Test Admin"
    assert synced.email == "admin@example.com"
    assert synced.is_active
    assert (await login(client, **ADMIN))["status"] == "totp_setup_required"
    refused = await client.post(
        "/api/v1/auth/login",
        json={"login": "system", "password": "changed-in-the-app-1"},
    )
    assert refused.status_code == 401


async def test_a_new_init_password_takes_over_at_the_next_start() -> None:
    await ensure_system_user()
    rotated = InitSettings(
        full_name="Test Admin", mail="admin@example.com", password="rotated-password-1"
    )
    assert not await ensure_system_user(rotated)
    async with SessionLocal() as db:
        user = await system_user(SqlAlchemyUserRepository(db))
    assert user is not None
    assert await BcryptPasswordHasher().verify("rotated-password-1", user.hashed_password)


async def test_a_matching_system_user_is_left_as_it_is() -> None:
    await ensure_system_user()
    async with SessionLocal() as db:
        before = await system_user(SqlAlchemyUserRepository(db))
    await ensure_system_user()
    async with SessionLocal() as db:
        after = await system_user(SqlAlchemyUserRepository(db))
    assert before is not None and after is not None
    assert after.hashed_password == before.hashed_password


async def test_an_account_holding_the_init_address_blocks_the_sync(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    await make_user("cook")
    async with SessionLocal() as db:
        cook = await SqlAlchemyUserRepository(db).get_by_email("cook@example.com")
    assert cook is not None
    moved = InitSettings(full_name="Test Admin", mail=cook.email, password="admin-password-1")

    assert not await ensure_system_user(moved)
    async with SessionLocal() as db:
        user = await system_user(SqlAlchemyUserRepository(db))
    assert user is not None and user.email == "admin@example.com"


async def test_first_sign_in_walks_through_the_setup(client: httpx.AsyncClient) -> None:
    await ensure_system_user()
    step = await login(client, **ADMIN)
    assert step["status"] == "totp_setup_required"
    assert (await client.get(f"{WEB}/users/me")).status_code == 401

    bearer = {"Authorization": f"Bearer {step['setup_token']}"}
    enrolment = await client.post(f"{WEB}/users/me/totp/enroll", headers=bearer)
    totp = pyotp.TOTP(enrolment.json()["secret"])
    confirmed = await client.post(
        f"{WEB}/users/me/totp/confirm", headers=bearer, json={"code": totp.now()}
    )
    assert confirmed.json()["session_started"] is True
    assert (await client.get(f"{WEB}/users/me")).json()["is_systemuser"] is True


async def test_trust_this_device_never_skips_the_code(
    admin: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    step = await login(other_client, **ADMIN)
    assert step["status"] == "totp_required"
    assert step["trusted_device_days"] == 0

    code = pyotp.TOTP(SYSTEM_TOTP_SECRET).at(int(datetime.now().timestamp()) + 30)
    signed_in = await other_client.post(
        "/api/v1/auth/login/totp",
        json={"partial_token": step["partial_token"], "code": code, "trust_device": True},
    )
    assert signed_in.status_code == 200
    assert TRUSTED_DEVICE_COOKIE not in signed_in.cookies


async def test_its_second_factor_cannot_be_turned_off_in_the_app(
    admin: httpx.AsyncClient,
) -> None:
    me = (await admin.get(f"{WEB}/users/me")).json()
    disabled = await admin.post(
        f"{WEB}/users/me/totp/disable", headers=CSRF, json={"password": ADMIN["password"]}
    )
    reset = await admin.post(f"{WEB}/users/{me['id']}/reset-totp", headers=CSRF)
    assert disabled.status_code == 403
    assert reset.status_code == 403
    assert (await admin.get(f"{WEB}/users/me")).json()["totp_enabled"] is True


async def test_its_session_ends_15_minutes_after_sign_in(
    client: httpx.AsyncClient, login_system: LoginSystem
) -> None:
    await login_system(client)
    current = (await client.get(f"{WEB}/users/me/sessions/current")).json()
    expires_at = datetime.fromisoformat(current["expires_at"])
    server_time = datetime.fromisoformat(current["server_time"])
    assert timedelta(minutes=14) < expires_at - server_time <= timedelta(minutes=15)


async def test_the_cookie_lives_only_as_long_as_the_session(
    admin: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    step = await login(other_client, **ADMIN)
    code = pyotp.TOTP(SYSTEM_TOTP_SECRET).at(int(datetime.now().timestamp()) + 30)
    signed_in = await other_client.post(
        "/api/v1/auth/login/totp", json={"partial_token": step["partial_token"], "code": code}
    )
    cookie = signed_in.headers["set-cookie"]
    assert SESSION_COOKIE in cookie
    assert "max-age=900" in cookie.lower()


async def test_ordinary_sessions_follow_the_configured_lifetime(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    current = (await other_client.get(f"{WEB}/users/me/sessions/current")).json()
    expires_at = datetime.fromisoformat(current["expires_at"])
    server_time = datetime.fromisoformat(current["server_time"])
    assert expires_at - server_time > timedelta(days=1)
