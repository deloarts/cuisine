"""An administrator edits someone else's profile: the nickname and whether it
is shown, and the avatar, which follows the same reach rule as the password
and the two-factor reset."""

from io import BytesIO

import httpx
from PIL import Image

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB


def _png(colour: tuple[int, int, int] = (30, 120, 200)) -> bytes:
    out = BytesIO()
    Image.new("RGB", (40, 40), colour).save(out, format="PNG")
    return out.getvalue()


async def _upload(
    client: httpx.AsyncClient, user_id: str, data: bytes, kind: str = "image/png"
) -> httpx.Response:
    return await client.put(
        f"{WEB}/users/{user_id}/avatar", headers=CSRF, files={"file": ("photo.png", data, kind)}
    )


async def test_an_admin_sets_and_clears_the_nickname(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    cook = await make_user("cook")
    saved = await admin.patch(
        f"{WEB}/users/{cook['id']}",
        headers=CSRF,
        json={"nickname": "  Bubu ", "show_nickname": True},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert (body["nickname"], body["show_nickname"], body["display_name"]) == ("Bubu", True, "Bubu")

    cleared = await admin.patch(f"{WEB}/users/{cook['id']}", headers=CSRF, json={"nickname": ""})
    body = cleared.json()
    assert (body["nickname"], body["display_name"]) == (None, "Cook")


async def test_a_new_account_can_start_with_a_nickname(make_user: MakeUser) -> None:
    created = await make_user("cook", nickname=" Bubu ", show_nickname=True)
    assert (created["nickname"], created["display_name"]) == ("Bubu", "Bubu")


async def test_an_admin_replaces_and_removes_an_avatar(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    cook = await make_user("cook")
    first = await _upload(admin, cook["id"], _png())
    assert first.status_code == 200, first.text
    first_id = first.json()["avatar_id"]
    assert first_id is not None

    # The user sees the new avatar on their own profile.
    await login(other_client, "cook@example.com", "cook-password-1")
    assert (await other_client.get(f"{WEB}/users/me")).json()["avatar_id"] == first_id

    second = await _upload(admin, cook["id"], _png((200, 30, 30)))
    second_id = second.json()["avatar_id"]
    assert second_id not in (None, first_id)
    assert (await admin.get(f"{WEB}/files/{first_id}")).status_code == 404

    removed = await admin.delete(f"{WEB}/users/{cook['id']}/avatar", headers=CSRF)
    assert removed.status_code == 200, removed.text
    assert removed.json()["avatar_id"] is None
    assert (await admin.get(f"{WEB}/files/{second_id}")).status_code == 404


async def test_an_avatar_set_by_an_admin_must_be_an_image(
    admin: httpx.AsyncClient, make_user: MakeUser
) -> None:
    cook = await make_user("cook")
    refused = await _upload(admin, cook["id"], b"%PDF-1.4 not an avatar", "application/pdf")
    assert refused.status_code == 415


async def test_a_manager_cannot_change_the_avatar_of_an_outranking_account(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("manager", "manager-password-1", permissions=["write:users"])
    boss = await make_user("boss", permissions=["write:users", "read:security_log"])
    await login(other_client, "manager@example.com", "manager-password-1")

    for response in (
        await _upload(other_client, boss["id"], _png()),
        await other_client.delete(f"{WEB}/users/{boss['id']}/avatar", headers=CSRF),
    ):
        assert response.status_code == 403, response.text
        assert response.json()["code"] == "UserOutranksActorError"
