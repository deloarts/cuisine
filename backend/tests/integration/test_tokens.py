"""Personal access tokens and API keys."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login

# The default settings cap tokens at a year, so every token needs an expiry.
EXPIRES = (datetime.now(UTC) + timedelta(days=30)).isoformat()


async def test_pat_acts_as_its_owner_with_its_own_permissions(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    created = await admin.post(
        "/api/v1/web/users/me/personal-access-tokens",
        headers=CSRF,
        json={"name": "script", "permissions": ["read:settings"], "expires_at": EXPIRES},
    )
    assert created.status_code == 201
    secret = created.json()["token"]
    assert secret.startswith("cuisine_pat_")
    assert created.json()["token_prefix"] in secret

    me = await client.get("/api/v1/pat/users/me", headers={"X-Api-Key": secret})
    assert me.status_code == 200
    assert me.json()["display_name"] == "Test Admin"

    listed = (await admin.get("/api/v1/web/users/me/personal-access-tokens")).json()
    assert "token" not in listed[0]


async def test_pat_cannot_carry_instance_control_permissions(admin: httpx.AsyncClient) -> None:
    refused = await admin.post(
        "/api/v1/web/users/me/personal-access-tokens",
        headers=CSRF,
        json={"name": "root", "permissions": ["write:settings"], "expires_at": EXPIRES},
    )
    assert refused.status_code == 422


async def test_revoked_pat_is_refused(admin: httpx.AsyncClient, client: httpx.AsyncClient) -> None:
    created = (
        await admin.post(
            "/api/v1/web/users/me/personal-access-tokens",
            headers=CSRF,
            json={"name": "t", "expires_at": EXPIRES},
        )
    ).json()
    await admin.delete(f"/api/v1/web/users/me/personal-access-tokens/{created['id']}", headers=CSRF)
    response = await client.get("/api/v1/pat/version", headers={"X-Api-Key": created["token"]})
    assert response.status_code == 401


async def test_pats_need_write_pat(make_user: MakeUser, other_client: httpx.AsyncClient) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    assert (
        await other_client.get("/api/v1/web/users/me/personal-access-tokens")
    ).status_code == 403


async def test_api_keys_are_off_until_enabled(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    created = await admin.post(
        "/api/v1/web/api-keys", headers=CSRF, json={"name": "importer", "expires_at": EXPIRES}
    )
    assert created.status_code == 201
    secret = created.json()["token"]
    headers = {"X-Api-Key": secret}

    assert (await client.get("/api/v1/key/whoami", headers=headers)).status_code == 403

    security = (await admin.get("/api/v1/web/settings/security")).json()
    await admin.put(
        "/api/v1/web/settings/security",
        headers=CSRF,
        json={**security, "enable_api_key_auth": True},
    )
    whoami = await client.get("/api/v1/key/whoami", headers=headers)
    assert whoami.status_code == 200
    assert whoami.json()["display_name"] == "importer"

    # A service account never appears among the people.
    users = (await admin.get("/api/v1/web/users")).json()
    assert all(u["full_name"] != "importer" for u in users)

    await admin.delete(f"/api/v1/web/api-keys/{created.json()['id']}", headers=CSRF)
    assert (await client.get("/api/v1/key/whoami", headers=headers)).status_code == 401


async def test_token_without_expiry_is_refused_under_a_cap(admin: httpx.AsyncClient) -> None:
    refused = await admin.post(
        "/api/v1/web/users/me/personal-access-tokens", headers=CSRF, json={"name": "t"}
    )
    assert refused.status_code == 422


async def test_token_expiry_must_be_within_the_cap(admin: httpx.AsyncClient) -> None:
    refused = await admin.post(
        "/api/v1/web/users/me/personal-access-tokens",
        headers=CSRF,
        json={"name": "forever", "expires_at": "2999-01-01T00:00:00Z"},
    )
    assert refused.status_code == 422
