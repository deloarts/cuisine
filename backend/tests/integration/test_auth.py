"""The password login, sessions, CSRF, lockout and logout."""

import httpx

from src.platform.infrastructure.security.cookies import SESSION_COOKIE
from tests.integration.conftest import ADMIN
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login


async def test_password_login_sets_httponly_session_cookie(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    response = await other_client.post(
        "/api/v1/auth/login", json={"login": "cook@example.com", "password": "cook-password-1"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "session"
    cookie = response.headers["set-cookie"]
    assert SESSION_COOKIE in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=strict" in cookie.lower()

    me = await other_client.get("/api/v1/web/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "cook@example.com"
    assert me.json()["is_systemuser"] is False


async def test_login_accepts_email_case_insensitively(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    await make_user("cook")
    response = await admin.post(
        "/api/v1/auth/login", json={"login": "COOK@example.com", "password": "cook-password-1"}
    )
    assert response.json()["status"] == "session"


async def test_wrong_password_and_unknown_user_answer_alike(admin: httpx.AsyncClient) -> None:
    wrong = await admin.post("/api/v1/auth/login", json={"login": "system", "password": "nope"})
    unknown = await admin.post(
        "/api/v1/auth/login", json={"login": "ghost@example.com", "password": "x"}
    )

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


async def test_unauthenticated_request_is_refused(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/v1/web/users/me")).status_code == 401


async def test_cookie_authenticated_write_needs_csrf_header(admin: httpx.AsyncClient) -> None:
    without = await admin.patch("/api/v1/web/users/me", json={"full_name": "X"})
    with_header = await admin.patch("/api/v1/web/users/me", json={"full_name": "X"}, headers=CSRF)

    assert without.status_code == 403
    assert with_header.status_code == 200


async def test_lockout_after_too_many_failures(admin: httpx.AsyncClient) -> None:
    for _ in range(5):
        await admin.post("/api/v1/auth/login", json={"login": "system", "password": "wrong"})

    locked = await admin.post("/api/v1/auth/login", json=ADMIN)

    assert locked.status_code == 429
    assert int(locked.headers["retry-after"]) > 0


async def test_logout_ends_the_session(admin: httpx.AsyncClient) -> None:
    token = admin.cookies[SESSION_COOKIE]
    assert (await admin.post("/api/v1/auth/logout", headers=CSRF)).status_code == 204

    reuse = await admin.get("/api/v1/web/users/me", headers={"Authorization": f"Bearer {token}"})
    assert reuse.status_code == 401


async def test_inactive_user_cannot_log_in(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("sleepy", is_active=False)
    response = await other_client.post(
        "/api/v1/auth/login", json={"login": "sleepy@example.com", "password": "cook-password-1"}
    )
    assert response.status_code == 401


async def test_password_change_signs_out_other_sessions(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    second = other_client.cookies[SESSION_COOKIE]

    third_login = await other_client.post(
        "/api/v1/auth/login", json={"login": "cook@example.com", "password": "cook-password-1"}
    )
    assert third_login.status_code == 200

    changed = await other_client.post(
        "/api/v1/web/users/me/password",
        headers=CSRF,
        json={"current_password": "cook-password-1", "new_password": "cook-password-2"},
    )
    assert changed.status_code == 204
    # The current session survives, the earlier one is gone.
    assert (await other_client.get("/api/v1/web/users/me")).status_code == 200
    old = await other_client.get(
        "/api/v1/web/users/me", headers={"Authorization": f"Bearer {second}"}
    )
    assert old.status_code == 401


async def test_sessions_are_listed_and_revocable(
    admin: httpx.AsyncClient, other_client: httpx.AsyncClient, login_system: LoginSystem
) -> None:
    await login_system(other_client)
    sessions = (await admin.get("/api/v1/web/users/me/sessions")).json()
    assert len(sessions) == 2
    assert sum(s["current"] for s in sessions) == 1

    other = next(s for s in sessions if not s["current"])
    revoked = await admin.delete(f"/api/v1/web/users/me/sessions/{other['id']}", headers=CSRF)
    assert revoked.status_code == 204
    assert (await other_client.get("/api/v1/web/users/me")).status_code == 401


async def test_security_headers_on_every_response(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["strict-transport-security"].startswith("max-age=")
