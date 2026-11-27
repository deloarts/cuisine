"""The step image library: the images other steps show, offered for a step
in the editor, ranked by the ingredients and equipment the steps share."""

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

LIBRARY = f"{WEB}/step-images"


async def _upload(client: httpx.AsyncClient, colour: tuple[int, int, int]) -> str:
    out = BytesIO()
    Image.new("RGB", (64, 64), colour).save(out, format="PNG")
    uploaded = await client.post(
        f"{WEB}/files", headers=CSRF, files={"file": ("photo.png", out.getvalue(), "image/png")}
    )
    assert uploaded.status_code == 201, uploaded.text
    return str(uploaded.json()["id"])


def _step(
    text: str,
    image_id: str | None,
    ingredients: list[dict[str, Any]] | None = None,
    equipment: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "translations": {"de-AT": {"text": text}},
        "image_id": image_id,
        "ingredients": [{"ingredient_id": i["id"]} for i in ingredients or []],
        "equipment": [{"equipment_id": e["id"]} for e in equipment or []],
    }


async def _recipe(
    client: httpx.AsyncClient,
    title: str,
    steps: list[dict[str, Any]],
    *,
    visibility: str = "instance",
    publish: bool = True,
) -> dict[str, Any]:
    created = await client.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"title": title}},
            "base_servings": 2,
            "visibility": visibility,
            "steps": steps,
        },
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    if publish:
        published = await client.post(f"{WEB}/recipes/{body['id']}/publish", headers=CSRF)
        assert published.status_code == 200, published.text
        body = published.json()
    return body


async def _knife(admin: httpx.AsyncClient) -> dict[str, Any]:
    created = await admin.post(
        f"{WEB}/equipment",
        headers=CSRF,
        json={"kind": "utensil", "translations": {"de-AT": {"name": "Kochmesser"}}},
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


async def _library(client: httpx.AsyncClient, **params: Any) -> dict[str, Any]:
    response = await client.get(LIBRARY, params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _allow_visibility_changes() -> None:
    async with SessionLocal() as db:
        await SqlAlchemySettingsRepository(db).save_privacy(
            PrivacySettings(default_recipe_visibility="instance", users_may_change_visibility=True)
        )
        await db.commit()


@pytest.fixture
async def stranger(make_user: MakeUser, visitor: httpx.AsyncClient) -> httpx.AsyncClient:
    """A third browser, signed in as a member who shares nothing with the cook."""
    await make_user("stranger", permissions=["write:recipes", "write:ingredients"])
    await login(visitor, "stranger@example.com", "cook-password-1")
    return visitor


async def test_the_library_ranks_steps_sharing_ingredients_and_equipment_first(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    onion = await make_ingredient(cook, "Zwiebel")
    salt = await make_ingredient(cook, "Salz")
    knife = await _knife(admin)
    chopping = await _upload(cook, (200, 180, 40))
    boiling = await _upload(cook, (40, 90, 200))
    await _recipe(
        cook,
        "Gulasch",
        [
            _step("Die **Zwiebel** fein schneiden.", chopping, [onion], [knife]),
            _step("Mit Salz aufkochen.", boiling, [salt]),
        ],
    )
    # A second recipe that already reuses the chopping photo lists it once.
    await _recipe(cook, "Zwiebelsuppe", [_step("Zwiebel hacken.", chopping, [onion])])

    ranked = await _library(cook, ingredient_id=[onion["id"]], equipment_id=[knife["id"]])

    assert ranked["total"] == 2
    first, second = ranked["items"]
    assert first["image_id"] == chopping
    assert first["matches"] == 2
    assert first["recipe"]["title"] == "Gulasch"
    assert first["step_number"] == 1
    assert first["step_text"] == "Die Zwiebel fein schneiden."
    assert second["image_id"] == boiling
    assert second["matches"] == 0


async def test_the_library_searches_step_text_recipe_titles_and_ingredient_names(
    cook: httpx.AsyncClient,
) -> None:
    onion = await make_ingredient(cook, "Zwiebel")
    chopping = await _upload(cook, (200, 180, 40))
    boiling = await _upload(cook, (40, 90, 200))
    await _recipe(
        cook,
        "Gulasch",
        [_step("Fein würfeln.", chopping, [onion]), _step("Aufkochen.", boiling)],
    )

    by_text = await _library(cook, search="aufkoch")
    by_ingredient = await _library(cook, search="zwiebel")
    by_title = await _library(cook, search="gulasch")
    nothing = await _library(cook, search="risotto")

    assert [i["image_id"] for i in by_text["items"]] == [boiling]
    assert [i["image_id"] for i in by_ingredient["items"]] == [chopping]
    assert by_title["total"] == 2
    assert nothing == {"items": [], "total": 0}


async def test_the_library_offers_only_images_of_recipes_the_reader_may_see(
    cook: httpx.AsyncClient, stranger: httpx.AsyncClient
) -> None:
    await _allow_visibility_changes()
    shared = await _upload(cook, (200, 180, 40))
    private = await _upload(cook, (40, 90, 200))
    draft = await _upload(cook, (90, 200, 40))
    await _recipe(cook, "Offen", [_step("Schneiden.", shared)])
    await _recipe(cook, "Geheim", [_step("Rühren.", private)], visibility="private")
    await _recipe(cook, "Entwurf", [_step("Braten.", draft)], publish=False)

    own = {i["image_id"] for i in (await _library(cook))["items"]}
    seen = {i["image_id"] for i in (await _library(stranger))["items"]}

    assert own == {shared, private, draft}
    assert seen == {shared}
    # The image the stranger may see goes on their own recipe as it is.
    taken = await _recipe(stranger, "Mein Gericht", [_step("Schneiden.", shared)])
    assert taken["steps"][0]["image_id"] == shared


async def test_the_library_needs_write_recipes(
    make_user: MakeUser, visitor: httpx.AsyncClient
) -> None:
    await make_user("reader", permissions=[])
    await login(visitor, "reader@example.com", "cook-password-1")

    assert (await visitor.get(LIBRARY)).status_code == 403
