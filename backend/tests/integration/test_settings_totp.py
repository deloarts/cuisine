"""Two-factor authentication for whoever may read or change the settings:
such an account enrols at sign-in whatever the security settings say, the
settings refuse it until it has enrolled, and it cannot turn two-factor
authentication off while it holds a settings permission."""

import httpx
import pyotp

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import enrol_at_login
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB

READER = {"login": "reader@example.com", "password": "cook-password-1"}


async def test_a_settings_reader_enrols_at_sign_in(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("reader", permissions=["read:settings"])
    step = await login(other_client, **READER)
    assert step["status"] == "totp_setup_required"

    await enrol_at_login(other_client, step["setup_token"])
    me = (await other_client.get(f"{WEB}/users/me")).json()
    assert (me["totp_enabled"], me["totp_mandatory"]) == (True, True)
    assert (await other_client.get(f"{WEB}/settings/security")).status_code == 200


async def test_a_group_grant_counts_too(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    reader = await make_user("reader")
    plain = await login(other_client, **READER)
    assert plain["status"] != "totp_setup_required"
    me = (await other_client.get(f"{WEB}/users/me")).json()
    assert me["totp_mandatory"] is False

    # Granted while signed in: the session goes on, but the settings wait
    # for the enrolment, which the account page offers.
    group = await admin.post(
        f"{WEB}/groups",
        headers=CSRF,
        json={
            "name": "Admins",
            "permissions": ["read:settings", "write:settings"],
            "member_ids": [reader["id"]],
        },
    )
    assert group.status_code == 201, group.text
    refused = await other_client.get(f"{WEB}/settings/security")
    assert refused.status_code == 403, refused.text
    assert refused.json()["code"] == "TotpSetupRequiredError"
    assert (await other_client.get(f"{WEB}/users/me")).json()["totp_mandatory"] is True

    enrolment = await other_client.post(
        f"{WEB}/users/me/totp/enroll", headers=CSRF, json={"password": READER["password"]}
    )
    totp = pyotp.TOTP(enrolment.json()["secret"])
    await other_client.post(f"{WEB}/users/me/totp/confirm", headers=CSRF, json={"code": totp.now()})
    assert (await other_client.get(f"{WEB}/settings/security")).status_code == 200


async def test_totp_stays_on_while_a_settings_permission_is_held(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    reader = await make_user("reader", permissions=["read:settings"])
    step = await login(other_client, **READER)
    await enrol_at_login(other_client, step["setup_token"])

    refused = await other_client.post(
        f"{WEB}/users/me/totp/disable", headers=CSRF, json={"password": READER["password"]}
    )
    assert refused.status_code == 403
    assert refused.json()["code"] == "TotpRequiredError"

    # Without the permission it may go again.
    await admin.patch(f"{WEB}/users/{reader['id']}", headers=CSRF, json={"permissions": []})
    allowed = await other_client.post(
        f"{WEB}/users/me/totp/disable", headers=CSRF, json={"password": READER["password"]}
    )
    assert allowed.status_code == 204, allowed.text
