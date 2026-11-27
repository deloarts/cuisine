"""Account and group administration, escalation guards and the security log."""

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import enrol_at_login
from tests.integration.conftest import login


async def test_admin_creates_an_account_that_can_log_in(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    created = await make_user("cook")
    assert created["is_active"] is True
    assert created["permissions"] == []

    assert (await login(other_client, "cook@example.com", "cook-password-1"))["status"] == "session"


async def test_there_is_no_open_sign_up(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/web/users",
        headers=CSRF,
        json={
            "full_name": "I",
            "email": "i@example.com",
            "password": "intruder-password",
        },
    )
    assert response.status_code == 401


async def test_creating_accounts_needs_write_users(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    response = await other_client.get("/api/v1/web/users")
    assert response.status_code == 403


async def test_duplicate_email_is_a_conflict_regardless_of_case(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    await make_user("cook")
    again = await admin.post(
        "/api/v1/web/users",
        headers=CSRF,
        json={
            "full_name": "Other",
            "email": "COOK@example.com",
            "password": "cook-password-1",
        },
    )
    assert again.status_code == 409


async def test_weak_password_is_refused(admin: httpx.AsyncClient) -> None:
    response = await admin.post(
        "/api/v1/web/users",
        headers=CSRF,
        json={"full_name": "X", "email": "x@example.com", "password": "short"},
    )
    assert response.status_code == 422


async def test_user_admin_cannot_grant_what_they_lack(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("manager", "manager-password-1", permissions=["write:users"])
    await login(other_client, "manager@example.com", "manager-password-1")
    escalated = await other_client.post(
        "/api/v1/web/users",
        headers=CSRF,
        json={
            "full_name": "Boss",
            "email": "boss@example.com",
            "password": "boss-password-1",
            "permissions": ["write:settings"],
        },
    )
    assert escalated.status_code == 422


async def test_system_user_is_protected(admin: httpx.AsyncClient, make_user: MakeUser) -> None:
    me = (await admin.get("/api/v1/web/users/me")).json()
    await make_user("manager", "manager-password-1", permissions=["write:users"])

    # Nobody can delete the system user, not even itself.
    assert (await admin.delete(f"/api/v1/web/users/{me['id']}", headers=CSRF)).status_code == 403


async def test_group_permissions_reach_their_members(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    cook = await make_user("cook")
    group = await admin.post(
        "/api/v1/web/groups",
        headers=CSRF,
        json={"name": "Chefs", "permissions": ["read:settings"], "member_ids": [cook["id"]]},
    )
    assert group.status_code == 201
    assert group.json()["member_ids"] == [cook["id"]]

    # A settings permission makes two-factor authentication mandatory.
    step = await login(other_client, "cook@example.com", "cook-password-1")
    assert step["status"] == "totp_setup_required"
    await enrol_at_login(other_client, step["setup_token"])
    me = (await other_client.get("/api/v1/web/users/me")).json()
    assert me["permissions"] == []
    assert me["effective_permissions"] == ["read:settings"]
    assert me["group_ids"] == [group.json()["id"]]


async def test_group_names_are_unique(admin: httpx.AsyncClient) -> None:
    first = await admin.post("/api/v1/web/groups", headers=CSRF, json={"name": "Family"})
    second = await admin.post("/api/v1/web/groups", headers=CSRF, json={"name": "family"})
    assert first.status_code == 201
    assert second.status_code == 409


async def test_deactivating_signs_the_user_out(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    cook = await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    patched = await admin.patch(
        f"/api/v1/web/users/{cook['id']}", headers=CSRF, json={"is_active": False}
    )
    assert patched.status_code == 200
    assert (await other_client.get("/api/v1/web/users/me")).status_code == 401


async def test_force_logout(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    cook = await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    assert (
        await admin.post(f"/api/v1/web/users/{cook['id']}/logout", headers=CSRF)
    ).status_code == 204
    assert (await other_client.get("/api/v1/web/users/me")).status_code == 401


async def test_security_log_records_logins_and_changes(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    await make_user("cook")
    page = (await admin.get("/api/v1/web/security-events")).json()
    types = [e["event_type"] for e in page["items"]]
    assert "login" in types
    assert "user_created" in types
    created = next(e for e in page["items"] if e["event_type"] == "user_created")
    assert created["actor_name"] == "Test Admin"
    assert created["target_name"] == "Cook"


async def test_own_security_log_is_open_to_everyone(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    own = await other_client.get("/api/v1/web/users/me/security-events")
    full = await other_client.get("/api/v1/web/security-events")
    assert own.status_code == 200
    assert own.json()["total"] >= 1
    assert full.status_code == 403


async def test_directory_lists_names_for_everyone(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    directory = (await other_client.get("/api/v1/web/users/directory")).json()
    assert {u["display_name"] for u in directory} == {"Test Admin", "Cook"}
    assert "email" not in directory[0]
