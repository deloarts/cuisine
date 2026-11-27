"""Who may read, attach and delete a stored file, and where avatars show."""

from io import BytesIO
from typing import Any

import httpx
import pytest
from PIL import Image

from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.domain.entities.settings import PrivacySettings
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import recipe_payload

PUBLIC = "/api/v1/public/recipes"


def _png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (64, 64), (90, 160, 60)).save(out, format="PNG")
    return out.getvalue()


async def _upload(client: httpx.AsyncClient) -> str:
    uploaded = await client.post(
        f"{WEB}/files", headers=CSRF, files={"file": ("photo.png", _png(), "image/png")}
    )
    assert uploaded.status_code == 201, uploaded.text
    return str(uploaded.json()["id"])


async def _avatar(client: httpx.AsyncClient) -> str:
    saved = await client.put(
        f"{WEB}/users/me/avatar", headers=CSRF, files={"file": ("me.png", _png(), "image/png")}
    )
    assert saved.status_code == 200, saved.text
    return str(saved.json()["avatar_id"])


async def _content(client: httpx.AsyncClient, file_id: str) -> int:
    return (await client.get(f"{WEB}/files/{file_id}/content")).status_code


def _steps(salt: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    return [("Würzen", [{"ingredient_id": salt["id"]}])]


async def _recipe(cook: httpx.AsyncClient, title: str, **extra: Any) -> dict[str, Any]:
    salt = await make_ingredient(cook, f"Salz {title}", english=f"Salt {title}")
    recipe = await make_recipe(cook, title, _steps(salt), **extra)
    return recipe | {"salt": salt}


async def _save(
    client: httpx.AsyncClient, recipe: dict[str, Any], title: str, **extra: Any
) -> httpx.Response:
    body = recipe_payload(title, _steps(recipe["salt"]), **extra)
    return await client.put(f"{WEB}/recipes/{recipe['id']}", headers=CSRF, json=body)


@pytest.fixture
async def stranger(make_user: MakeUser, visitor: httpx.AsyncClient) -> httpx.AsyncClient:
    """A third browser, signed in as a member who shares nothing with the cook."""
    await make_user("stranger", permissions=["write:recipes", "write:ingredients"])
    await login(visitor, "stranger@example.com", "cook-password-1")
    return visitor


async def test_an_upload_is_private_to_its_uploader(
    cook: httpx.AsyncClient, stranger: httpx.AsyncClient
) -> None:
    file_id = await _upload(cook)
    assert await _content(cook, file_id) == 200
    assert await _content(stranger, file_id) == 404
    assert (await stranger.get(f"{WEB}/files/{file_id}")).status_code == 404


@pytest.mark.usefixtures("user_choice_privacy")
async def test_a_recipe_image_follows_the_recipe_visibility(
    cook: httpx.AsyncClient, stranger: httpx.AsyncClient
) -> None:
    image = await _upload(cook)
    recipe = await _recipe(cook, "Geheim", visibility="private", cover_image_id=image)
    assert await _content(stranger, image) == 404

    widened = await _save(cook, recipe, "Geheim", visibility="instance", cover_image_id=image)
    assert widened.status_code == 200, widened.text
    assert await _content(stranger, image) == 200


@pytest.mark.usefixtures("user_choice_privacy")
async def test_a_file_the_editor_may_not_read_cannot_be_attached(
    cook: httpx.AsyncClient, stranger: httpx.AsyncClient
) -> None:
    private = await _upload(cook)
    await _recipe(cook, "Geheim", visibility="private", cover_image_id=private)
    unattached = await _upload(cook)

    salt = await make_ingredient(stranger, "Salz fremd", english="Salt foreign")
    for file_id in (private, unattached):
        body = recipe_payload("Fremd", _steps(salt), cover_image_id=file_id)
        refused = await stranger.post(f"{WEB}/recipes", headers=CSRF, json=body)
        assert refused.status_code == 404, refused.text
        assert refused.json()["code"] == "StoredFileNotFoundError"


async def test_an_avatar_shows_to_members_but_is_never_a_recipe_image(
    cook: httpx.AsyncClient, stranger: httpx.AsyncClient
) -> None:
    avatar = await _avatar(cook)
    assert await _content(stranger, avatar) == 200

    recipe = await _recipe(cook, "Kein Avatar")
    refused = await _save(cook, recipe, "Kein Avatar", cover_image_id=avatar)
    assert refused.status_code == 404, refused.text


async def test_the_author_avatar_travels_with_the_name(
    cook: httpx.AsyncClient, stranger: httpx.AsyncClient
) -> None:
    avatar = await _avatar(cook)
    recipe = await _recipe(cook, "Mit Gesicht")
    shown = (await stranger.get(f"{WEB}/recipes/{recipe['id']}")).json()
    assert shown["owner"]["avatar_id"] == avatar


async def test_only_the_uploader_deletes_a_file_and_only_while_unused(
    cook: httpx.AsyncClient, stranger: httpx.AsyncClient
) -> None:
    unused = await _upload(cook)
    assert (await stranger.delete(f"{WEB}/files/{unused}", headers=CSRF)).status_code == 404
    assert (await cook.delete(f"{WEB}/files/{unused}", headers=CSRF)).status_code == 204

    cover = await _upload(cook)
    await _recipe(cook, "Benutzt", cover_image_id=cover)
    in_use = await cook.delete(f"{WEB}/files/{cover}", headers=CSRF)
    assert in_use.status_code == 409
    assert in_use.json()["code"] == "FileInUseError"
    # A member who sees the recipe still may not delete its image.
    assert (await stranger.delete(f"{WEB}/files/{cover}", headers=CSRF)).status_code == 403

    avatar = await _avatar(cook)
    assert (await cook.delete(f"{WEB}/files/{avatar}", headers=CSRF)).status_code == 409


async def test_branding_cannot_publish_a_private_image(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    private = await _upload(cook)
    general = (await admin.get(f"{WEB}/settings/general")).json()
    refused = await admin.put(
        f"{WEB}/settings/general",
        headers=CSRF,
        json=general | {"login_background_file_id": private},
    )
    assert refused.status_code == 422, refused.text

    own = await _upload(admin)
    saved = await admin.put(
        f"{WEB}/settings/general", headers=CSRF, json=general | {"login_background_file_id": own}
    )
    assert saved.status_code == 200, saved.text


async def _allow_public() -> None:
    async with SessionLocal() as db:
        await SqlAlchemySettingsRepository(db).save_privacy(
            PrivacySettings(
                default_recipe_visibility="instance",
                users_may_change_visibility=True,
                allow_public_recipes=True,
            )
        )
        await db.commit()


async def test_a_public_author_avatar_shows_only_with_the_name(
    cook: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    await _allow_public()
    await _avatar(cook)
    recipe = await _recipe(cook, "Öffentlich", visibility="public")
    url = f"{PUBLIC}/{recipe['id']}/author-avatar"

    # The cook's browser holds a session, so a fresh client stands in for
    # the anonymous visitor.
    detail = (await client.get(f"{PUBLIC}/{recipe['id']}")).json()
    assert (detail["author"], detail["author_avatar"]) == (None, False)
    assert (await client.get(url)).status_code == 404

    await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"show_name_on_public_recipes": True})
    detail = (await client.get(f"{PUBLIC}/{recipe['id']}")).json()
    assert (detail["author"], detail["author_avatar"]) == ("Cook", True)
    served = await client.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/webp"
    assert served.headers["x-robots-tag"] == "noindex"
    listed = (await client.get(PUBLIC)).json()["items"][0]
    assert listed["author_avatar"] is True
