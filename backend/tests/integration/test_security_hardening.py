"""Security rules from the 2026-11 audit: a password change ends connected
apps, enrolling two-factor authentication from a session needs the password,
the guest list is capped before any lookup, the login lockout cannot be
switched off, and every refusal of the auth dependencies carries a `code`."""

import uuid

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.test_mcp import rpc
from tests.integration.test_oauth import _connect
from tests.integration.test_oauth import _refresh


async def test_changing_the_own_password_ends_connected_apps(
    make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    client_id, tokens = await _connect(make_user, client)
    changed = await client.post(
        f"{WEB}/users/me/password",
        headers=CSRF,
        json={"current_password": "cook-password-1", "new_password": "chef-password-2"},
    )
    assert changed.status_code == 204, changed.text

    # The session that made the change stays signed in; the app does not.
    assert (await client.get(f"{WEB}/users/me")).status_code == 200
    assert (await rpc(client, tokens["access_token"], "tools/list")).status_code == 401
    refreshed = await _refresh(client, client_id, tokens["refresh_token"])
    assert refreshed.json()["error"] == "invalid_grant"
    assert (await client.get(f"{WEB}/users/me/connected-apps")).json() == []
    events = (await client.get(f"{WEB}/users/me/security-events")).json()["items"]
    revoked = [e for e in events if e["event_type"] == "oauth_grant_revoked"]
    assert revoked and revoked[0]["detail"]["reason"] == "password_changed"


async def test_enrolling_totp_from_a_session_needs_the_password(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    url = f"{WEB}/users/me/totp/enroll"

    missing = await other_client.post(url, headers=CSRF)
    assert missing.status_code == 403, missing.text
    assert missing.json()["code"] == "PasswordConfirmationError"
    wrong = await other_client.post(url, headers=CSRF, json={"password": "not-my-password"})
    assert wrong.status_code == 403
    right = await other_client.post(url, headers=CSRF, json={"password": "cook-password-1"})
    assert right.status_code == 200, right.text
    assert right.json()["secret"]


async def test_too_many_guests_are_refused_before_any_lookup(cook: httpx.AsyncClient) -> None:
    # Unknown ids would answer 404 if any of them were looked up first.
    guests = [str(uuid.uuid4()) for _ in range(31)]
    refused = await cook.get(f"{WEB}/recipes", params={"guests": guests})
    assert refused.status_code == 422, refused.text
    assert refused.json()["code"] == "InvalidInputError"
    # Repeating one id does not count twice.
    same = await cook.get(f"{WEB}/recipes", params={"guests": [guests[0]] * 31})
    assert same.status_code == 404


async def test_the_login_lockout_cannot_be_switched_off(admin: httpx.AsyncClient) -> None:
    security = (await admin.get(f"{WEB}/settings/security")).json()
    refused = await admin.put(
        f"{WEB}/settings/security", headers=CSRF, json={**security, "max_login_attempts": 0}
    )
    assert refused.status_code == 422
    kept = await admin.put(
        f"{WEB}/settings/security", headers=CSRF, json={**security, "max_login_attempts": 1}
    )
    assert kept.status_code == 200, kept.text


async def test_auth_refusals_carry_a_code(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    no_csrf = await admin.patch(f"{WEB}/users/me", json={"full_name": "X"})
    assert (no_csrf.status_code, no_csrf.json()["code"]) == (403, "CsrfHeaderMissingError")

    bad_session = await other_client.get(
        f"{WEB}/users/me", headers={"Authorization": "Bearer not-a-token"}
    )
    assert (bad_session.status_code, bad_session.json()["code"]) == (401, "InvalidTokenError")

    bad_pat = await other_client.get("/api/v1/pat/users/me", headers={"X-Api-Key": "nope"})
    assert (bad_pat.status_code, bad_pat.json()["code"]) == (401, "InvalidTokenError")

    keys_off = await other_client.get("/api/v1/key/whoami", headers={"X-Api-Key": "nope"})
    assert (keys_off.status_code, keys_off.json()["code"]) == (403, "ApiKeyAuthDisabledError")

    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    denied = await other_client.get(f"{WEB}/users")
    assert (denied.status_code, denied.json()["code"]) == (403, "PermissionDeniedError")
    any_denied = await other_client.get(f"{WEB}/groups")
    assert (any_denied.status_code, any_denied.json()["code"]) == (403, "PermissionDeniedError")

    backwards = await admin.get(
        f"{WEB}/security-events", params={"date_from": "2026-02-01", "date_to": "2026-01-01"}
    )
    assert (backwards.status_code, backwards.json()["code"]) == (422, "InvalidDateRangeError")
