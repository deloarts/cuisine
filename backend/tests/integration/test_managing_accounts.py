"""Who may act on an account: a holder of write:users reaches only accounts
whose effective permissions they all hold themselves, and groups cap taking
rights away like they cap handing them out."""

from typing import Any

import httpx
import pytest

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB

MANAGER = {"login": "manager@example.com", "password": "manager-password-1"}


@pytest.fixture
async def manager(make_user: MakeUser, other_client: httpx.AsyncClient) -> httpx.AsyncClient:
    """A second browser signed in as a household member who manages
    accounts and nothing else."""
    await make_user("manager", MANAGER["password"], permissions=["write:users"])
    await login(other_client, **MANAGER)
    return other_client


async def _boss(make_user: MakeUser) -> dict[str, Any]:
    """An account that holds more than the manager does."""
    return await make_user("boss", permissions=["write:users", "read:security_log"])


def _outranked(response: httpx.Response) -> None:
    assert response.status_code == 403, response.text
    assert response.json()["code"] == "UserOutranksActorError"


@pytest.mark.parametrize(
    "change",
    [
        {"password": "taken-over-password-1"},
        {"email": "mine@example.com"},
        {"is_active": False},
        {"permissions": ["write:users"]},
    ],
    ids=["password", "email", "activity", "demotion"],
)
async def test_a_manager_cannot_change_an_account_that_outranks_them(
    manager: httpx.AsyncClient, make_user: MakeUser, change: dict[str, Any]
) -> None:
    boss = await _boss(make_user)
    _outranked(await manager.patch(f"{WEB}/users/{boss['id']}", headers=CSRF, json=change))


async def test_leaving_the_groups_of_an_outranking_account_is_refused(
    admin: httpx.AsyncClient, manager: httpx.AsyncClient, make_user: MakeUser
) -> None:
    boss = await make_user("boss")
    group = await admin.post(
        f"{WEB}/groups",
        headers=CSRF,
        json={"name": "Auditors", "permissions": ["read:security_log"], "member_ids": [boss["id"]]},
    )
    assert group.status_code == 201, group.text
    # The group permission alone puts the boss above the manager.
    _outranked(
        await manager.patch(f"{WEB}/users/{boss['id']}", headers=CSRF, json={"group_ids": []})
    )


async def test_a_manager_cannot_reset_sign_out_or_delete_an_outranking_account(
    manager: httpx.AsyncClient, make_user: MakeUser
) -> None:
    boss = await _boss(make_user)
    _outranked(await manager.post(f"{WEB}/users/{boss['id']}/reset-totp", headers=CSRF))
    _outranked(await manager.post(f"{WEB}/users/{boss['id']}/logout", headers=CSRF))
    _outranked(await manager.delete(f"{WEB}/users/{boss['id']}", headers=CSRF))


async def test_a_manager_still_manages_peers_and_lesser_accounts(
    manager: httpx.AsyncClient, make_user: MakeUser
) -> None:
    peer = await make_user("peer", permissions=["write:users"])
    cook = await make_user("cook")
    renamed = await manager.patch(
        f"{WEB}/users/{peer['id']}", headers=CSRF, json={"password": "new-peer-password-1"}
    )
    assert renamed.status_code == 200, renamed.text
    assert (await manager.post(f"{WEB}/users/{cook['id']}/logout", headers=CSRF)).status_code == 204
    assert (await manager.delete(f"{WEB}/users/{cook['id']}", headers=CSRF)).status_code == 204


async def test_the_name_of_an_outranking_account_stays_editable(
    manager: httpx.AsyncClient, make_user: MakeUser
) -> None:
    boss = await _boss(make_user)
    renamed = await manager.patch(
        f"{WEB}/users/{boss['id']}", headers=CSRF, json={"full_name": "The Boss"}
    )
    assert renamed.status_code == 200, renamed.text


async def test_nobody_but_the_system_user_signs_the_system_user_out(
    admin: httpx.AsyncClient, manager: httpx.AsyncClient
) -> None:
    system = (await admin.get(f"{WEB}/users/me")).json()
    _outranked(await manager.post(f"{WEB}/users/{system['id']}/logout", headers=CSRF))


async def test_groups_cap_taking_rights_away(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("keeper", "keeper-password-1", permissions=["write:groups"])
    cook = await make_user("cook")
    group = await admin.post(
        f"{WEB}/groups",
        headers=CSRF,
        json={"name": "Auditors", "permissions": ["read:security_log"], "member_ids": [cook["id"]]},
    )
    group_id = group.json()["id"]
    await login(other_client, "keeper@example.com", "keeper-password-1")

    stripped = await other_client.patch(
        f"{WEB}/groups/{group_id}", headers=CSRF, json={"permissions": []}
    )
    assert stripped.status_code == 422, stripped.text
    assert stripped.json()["code"] == "InvalidPermissionError"
    removed = await other_client.patch(
        f"{WEB}/groups/{group_id}", headers=CSRF, json={"member_ids": []}
    )
    assert removed.status_code == 422, removed.text
    deleted = await other_client.delete(f"{WEB}/groups/{group_id}", headers=CSRF)
    assert deleted.status_code == 422, deleted.text
    # Renaming takes nothing away.
    renamed = await other_client.patch(
        f"{WEB}/groups/{group_id}", headers=CSRF, json={"name": "Readers"}
    )
    assert renamed.status_code == 200, renamed.text
