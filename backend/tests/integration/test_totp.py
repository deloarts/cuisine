"""Two-factor authentication: enrolment, the TOTP login step, replay
protection, trusted devices and enforced enrolment. The flows run on an
ordinary account, since the system user's two-factor authentication is
mandatory and set up by the fixtures already."""

import time

import httpx
import pyotp
import pytest

from src.platform.infrastructure.security.cookies import TRUSTED_DEVICE_COOKIE
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login

COOK = {"login": "cook@example.com", "password": "cook-password-1"}


def next_code(totp: pyotp.TOTP) -> str:
    return totp.at(int(time.time()) + 30)


@pytest.fixture
async def cook(admin: httpx.AsyncClient, make_user: MakeUser) -> httpx.AsyncClient:
    """The admin's client, signed in again as an ordinary account."""
    await make_user("cook", COOK["password"])
    await login(admin, **COOK)
    return admin


async def _enable_totp(client: httpx.AsyncClient) -> pyotp.TOTP:
    enrolment = await client.post(
        "/api/v1/web/users/me/totp/enroll", headers=CSRF, json={"password": COOK["password"]}
    )
    assert enrolment.status_code == 200
    totp = pyotp.TOTP(enrolment.json()["secret"])
    confirmed = await client.post(
        "/api/v1/web/users/me/totp/confirm", headers=CSRF, json={"code": totp.now()}
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["session_started"] is False
    return totp


async def test_login_with_totp(cook: httpx.AsyncClient, other_client: httpx.AsyncClient) -> None:
    totp = await _enable_totp(cook)

    step_one = await other_client.post("/api/v1/auth/login", json=COOK)
    body = step_one.json()
    assert body["status"] == "totp_required"
    assert (await other_client.get("/api/v1/web/users/me")).status_code == 401

    # The confirmation consumed the current code, so the login uses the
    # next step's, which the verifier still accepts.
    code = next_code(totp)
    step_two = await other_client.post(
        "/api/v1/auth/login/totp", json={"partial_token": body["partial_token"], "code": code}
    )
    assert step_two.status_code == 200, step_two.text
    assert (await other_client.get("/api/v1/web/users/me")).json()["totp_enabled"] is True


async def test_totp_code_cannot_be_replayed(
    cook: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    totp = await _enable_totp(cook)
    code = next_code(totp)

    first = (await other_client.post("/api/v1/auth/login", json=COOK)).json()
    ok = await other_client.post(
        "/api/v1/auth/login/totp", json={"partial_token": first["partial_token"], "code": code}
    )
    second = (await other_client.post("/api/v1/auth/login", json=COOK)).json()
    replayed = await other_client.post(
        "/api/v1/auth/login/totp", json={"partial_token": second["partial_token"], "code": code}
    )

    assert ok.status_code == 200
    assert replayed.status_code == 401


async def test_trusted_device_skips_the_code(
    cook: httpx.AsyncClient, other_client: httpx.AsyncClient
) -> None:
    totp = await _enable_totp(cook)
    code = next_code(totp)
    first = (await other_client.post("/api/v1/auth/login", json=COOK)).json()
    trusted = await other_client.post(
        "/api/v1/auth/login/totp",
        json={"partial_token": first["partial_token"], "code": code, "trust_device": True},
    )
    assert trusted.status_code == 200
    device_secret = trusted.cookies.get(TRUSTED_DEVICE_COOKIE)
    assert device_secret

    # The browser now holds the trusted-device cookie and sends it along.
    again = await other_client.post("/api/v1/auth/login", json=COOK)
    assert again.json()["status"] == "session"

    devices = (await other_client.get("/api/v1/web/users/me/trusted-devices")).json()
    assert len(devices) == 1


async def test_enforced_totp_walks_through_enrolment(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    security = (await admin.get("/api/v1/web/settings/security")).json()
    saved = await admin.put(
        "/api/v1/web/settings/security", headers=CSRF, json={**security, "enforce_totp": True}
    )
    assert saved.status_code == 200
    await make_user("cook")

    step = (
        await other_client.post(
            "/api/v1/auth/login", json={"login": "cook@example.com", "password": "cook-password-1"}
        )
    ).json()
    assert step["status"] == "totp_setup_required"
    bearer = {"Authorization": f"Bearer {step['setup_token']}"}

    # The setup token opens the enrolment endpoints and nothing else.
    assert (await other_client.get("/api/v1/web/users/me", headers=bearer)).status_code == 401
    enrolment = await other_client.post("/api/v1/web/users/me/totp/enroll", headers=bearer)
    totp = pyotp.TOTP(enrolment.json()["secret"])
    confirmed = await other_client.post(
        "/api/v1/web/users/me/totp/confirm", headers=bearer, json={"code": totp.now()}
    )
    assert confirmed.json()["session_started"] is True
    assert (await other_client.get("/api/v1/web/users/me")).status_code == 200


async def test_totp_cannot_be_disabled_when_enforced(
    cook: httpx.AsyncClient, other_client: httpx.AsyncClient, login_system: LoginSystem
) -> None:
    await _enable_totp(cook)
    await login_system(other_client)
    security = (await other_client.get("/api/v1/web/settings/security")).json()
    await other_client.put(
        "/api/v1/web/settings/security", headers=CSRF, json={**security, "enforce_totp": True}
    )
    refused = await cook.post(
        "/api/v1/web/users/me/totp/disable", headers=CSRF, json={"password": COOK["password"]}
    )
    assert refused.status_code == 403


async def test_disable_totp_needs_the_password(cook: httpx.AsyncClient) -> None:
    await _enable_totp(cook)
    wrong = await cook.post(
        "/api/v1/web/users/me/totp/disable", headers=CSRF, json={"password": "nope"}
    )
    right = await cook.post(
        "/api/v1/web/users/me/totp/disable", headers=CSRF, json={"password": COOK["password"]}
    )
    assert wrong.status_code == 403
    assert right.status_code == 204
    assert (await cook.get("/api/v1/web/users/me")).json()["totp_enabled"] is False
