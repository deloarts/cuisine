"""The signed-in user's own avatar."""

from io import BytesIO

import httpx
from PIL import Image

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login


def _png(colour: tuple[int, int, int] = (30, 120, 200)) -> bytes:
    out = BytesIO()
    Image.new("RGB", (40, 40), colour).save(out, format="PNG")
    return out.getvalue()


async def _upload(
    client: httpx.AsyncClient, data: bytes, kind: str = "image/png"
) -> httpx.Response:
    return await client.put(
        "/api/v1/web/users/me/avatar", headers=CSRF, files={"file": ("me.png", data, kind)}
    )


async def test_avatar_upload_replace_and_remove(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    assert (await other_client.get("/api/v1/web/users/me")).json()["avatar_id"] is None

    first = await _upload(other_client, _png())
    assert first.status_code == 200, first.text
    first_id = first.json()["avatar_id"]
    assert first_id is not None
    thumbnail = await other_client.get(
        f"/api/v1/web/files/{first_id}/content", params={"variant": "thumbnail"}
    )
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"] == "image/webp"

    # A new avatar replaces the old one, whose file is deleted.
    second = await _upload(other_client, _png((200, 30, 30)))
    second_id = second.json()["avatar_id"]
    assert second_id not in (None, first_id)
    assert (await other_client.get(f"/api/v1/web/files/{first_id}")).status_code == 404
    assert (await other_client.get("/api/v1/web/users/me")).json()["avatar_id"] == second_id

    removed = await other_client.delete("/api/v1/web/users/me/avatar", headers=CSRF)
    assert removed.status_code == 200
    assert removed.json()["avatar_id"] is None
    assert (await other_client.get(f"/api/v1/web/files/{second_id}")).status_code == 404


async def test_avatar_must_be_an_image(admin: httpx.AsyncClient) -> None:
    refused = await _upload(admin, b"%PDF-1.4 not an avatar", "application/pdf")
    assert refused.status_code == 415
    assert (await admin.get("/api/v1/web/users/me")).json()["avatar_id"] is None


async def test_avatar_needs_a_session(client: httpx.AsyncClient) -> None:
    assert (await _upload(client, _png())).status_code == 401


async def test_deleting_a_user_deletes_their_avatar(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    user = await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    avatar_id = (await _upload(other_client, _png())).json()["avatar_id"]
    listed = (await admin.get(f"/api/v1/web/users/{user['id']}")).json()
    assert listed["avatar_id"] == avatar_id

    deleted = await admin.delete(f"/api/v1/web/users/{user['id']}", headers=CSRF)
    assert deleted.status_code == 204
    assert (await admin.get(f"/api/v1/web/files/{avatar_id}")).status_code == 404


async def test_deleting_the_own_account_deletes_the_avatar(
    admin: httpx.AsyncClient, make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("leaver")
    await login(other_client, "leaver@example.com", "cook-password-1")
    avatar_id = (await _upload(other_client, _png())).json()["avatar_id"]

    deleted = await other_client.request(
        "DELETE",
        "/api/v1/web/users/me",
        headers=CSRF,
        json={"email": "leaver@example.com", "password": "cook-password-1"},
    )
    assert deleted.status_code == 204, deleted.text
    assert (await admin.get(f"/api/v1/web/files/{avatar_id}")).status_code == 404


async def test_directory_carries_the_avatar(
    make_user: MakeUser, other_client: httpx.AsyncClient
) -> None:
    await make_user("cook")
    await login(other_client, "cook@example.com", "cook-password-1")
    uploaded = (await _upload(other_client, _png())).json()["avatar_id"]

    directory = (await other_client.get("/api/v1/web/users/directory")).json()
    avatars = {u["display_name"]: u["avatar_id"] for u in directory}
    assert avatars == {"Test Admin": None, "Cook": uploaded}
