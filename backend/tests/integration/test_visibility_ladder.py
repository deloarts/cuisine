"""The visibility ladder through the API: the "allow public recipes" switch,
a stored public read as instance while it is off, the lock modes, the new
privacy statement version on switching, and the author name settings."""

from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select

from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.platform.adapters.outbound.persistence.session import SessionLocal
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe

PRIVACY = f"{WEB}/settings/privacy"


async def _privacy(admin: httpx.AsyncClient, **values: Any) -> httpx.Response:
    current = (await admin.get(PRIVACY)).json()
    return await admin.put(PRIVACY, headers=CSRF, json=current | values)


async def _recipe(cook: httpx.AsyncClient, title: str, **extra: Any) -> dict[str, Any]:
    salt = await make_ingredient(cook, f"Salz {title}")
    return await make_recipe(cook, title, [("Würzen", [{"ingredient_id": salt["id"]}])], **extra)


async def _save(
    cook: httpx.AsyncClient, recipe_id: str, visibility: str, extra_lines: list[dict[str, Any]]
) -> httpx.Response:
    edit = (await cook.get(f"{WEB}/recipes/{recipe_id}/edit")).json()
    body = {
        "original_locale": edit["original_locale"],
        "translations": edit["translations"],
        "base_servings": edit["base_servings"],
        "steps": [
            {
                "translations": s["translations"],
                "ingredients": [
                    {
                        "ingredient_id": i["ingredient_id"],
                        "sub_recipe_id": i["sub_recipe_id"],
                        "amount": i["amount"],
                        "unit_id": i["unit_id"],
                    }
                    for i in s["ingredients"]
                ]
                + extra_lines,
            }
            for s in edit["steps"]
        ],
        "visibility": visibility,
    }
    return await cook.put(f"{WEB}/recipes/{recipe_id}", headers=CSRF, json=body)


async def _stored_visibility(public_id: str) -> str:
    async with SessionLocal() as db:
        value = await db.scalar(
            select(RecipeModel.visibility).where(RecipeModel.public_id == UUID(public_id))
        )
    assert value is not None
    return value


@pytest.mark.usefixtures("user_choice_privacy")
async def test_public_is_refused_while_not_allowed(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    recipe = await _recipe(cook, "Suppe")
    refused = await _save(cook, recipe["id"], "public", [])
    assert refused.status_code == 422
    assert refused.json()["code"] == "PublicRecipesNotAllowedError"
    created = await cook.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"title": "Brot", "description": "", "tips": ""}},
            "base_servings": 2,
            "steps": [],
            "visibility": "public",
        },
    )
    assert created.status_code == 422
    assert created.json()["code"] == "PublicRecipesNotAllowedError"

    own = await cook.patch(
        f"{WEB}/users/me", headers=CSRF, json={"default_recipe_visibility": "public"}
    )
    assert own.status_code == 422
    assert own.json()["code"] == "PublicRecipesNotAllowedError"

    default = await _privacy(admin, default_recipe_visibility="public")
    assert default.status_code == 422
    assert default.json()["code"] == "PublicRecipesNotAllowedError"


@pytest.mark.usefixtures("user_choice_privacy")
async def test_a_stored_public_reads_as_instance_while_off(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
) -> None:
    assert (await _privacy(admin, allow_public_recipes=True)).status_code == 200
    recipe = await _recipe(cook, "Gulasch")
    saved = await _save(cook, recipe["id"], "public", [])
    assert saved.status_code == 200, saved.text
    assert (saved.json()["visibility"], saved.json()["effective_visibility"]) == (
        "public",
        "public",
    )

    assert (await _privacy(admin, allow_public_recipes=False)).status_code == 200
    # The row is untouched; responses report the stored and the applying value.
    assert await _stored_visibility(recipe["id"]) == "public"
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    assert (detail["visibility"], detail["effective_visibility"]) == ("public", "instance")
    edit = (await cook.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    assert (edit["visibility"], edit["effective_visibility"]) == ("public", "instance")
    # Saving it again keeps public, since it already was.
    again = await _save(cook, recipe["id"], "public", [])
    assert again.status_code == 200, again.text
    assert await _stored_visibility(recipe["id"]) == "public"

    assert (await _privacy(admin, allow_public_recipes=True)).status_code == 200
    restored = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    assert restored["effective_visibility"] == "public"
    assert await _stored_visibility(recipe["id"]) == "public"

    # Every signed-in user reads it while off, as an instance recipe. The
    # admin's client signs in as the reader, so this comes last.
    await _privacy(admin, allow_public_recipes=False)
    await make_user("reader")
    await login(client, "reader@example.com", "cook-password-1")
    listed = (await client.get(f"{WEB}/recipes", params={"search": "Gulasch"})).json()
    assert [(r["visibility"], r["effective_visibility"]) for r in listed["items"]] == [
        ("public", "instance")
    ]


@pytest.mark.usefixtures("user_choice_privacy")
async def test_sub_recipe_warning_follows_the_switch(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    await _privacy(admin, allow_public_recipes=True)
    sauce = await _recipe(cook, "Sauce", visibility="instance")
    bowl = await _recipe(cook, "Bowl")
    saved = await _save(cook, bowl["id"], "public", [{"sub_recipe_id": sauce["id"], "amount": 1}])
    assert saved.status_code == 200, saved.text
    assert saved.json()["less_visible_sub_recipe_ids"] == [sauce["id"]]

    await _privacy(admin, allow_public_recipes=False)
    edit = (await cook.get(f"{WEB}/recipes/{bowl['id']}/edit")).json()
    assert edit["less_visible_sub_recipe_ids"] == []


@pytest.mark.usefixtures("user_choice_privacy")
async def test_an_own_public_default_starts_new_recipes_as_instance_while_off(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    await _privacy(admin, allow_public_recipes=True)
    own = await cook.patch(
        f"{WEB}/users/me", headers=CSRF, json={"default_recipe_visibility": "public"}
    )
    assert own.status_code == 200
    assert (await _recipe(cook, "Erste"))["visibility"] == "public"
    await _privacy(admin, allow_public_recipes=False)
    # The own default stays stored as it is, and saving the profile again works.
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert me["default_recipe_visibility"] == "public"
    resaved = await cook.patch(
        f"{WEB}/users/me", headers=CSRF, json={"default_recipe_visibility": "public"}
    )
    assert resaved.status_code == 200
    assert (await _recipe(cook, "Zweite"))["visibility"] == "instance"


async def test_lock_modes(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    # A fresh instance runs in peers mode.
    info = (await client.get("/api/v1/public/info")).json()
    assert (info["privacy_mode"], info["default_recipe_visibility"]) == ("peers", "peers")
    assert (await _recipe(cook, "Erste", visibility="private"))["visibility"] == "peers"

    # Public mode: a public default, locked, with public recipes allowed.
    saved = await _privacy(
        admin,
        default_recipe_visibility="public",
        users_may_change_visibility=False,
        allow_public_recipes=True,
    )
    assert saved.status_code == 200, saved.text
    info = (await client.get("/api/v1/public/info")).json()
    assert (info["privacy_mode"], info["default_recipe_visibility"]) == ("public", "public")
    assert (await _recipe(cook, "Zweite", visibility="private"))["visibility"] == "public"
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert me["privacy_mode"] == {
        "mode": "public",
        "default_visibility": "public",
        "allow_public_recipes": True,
    }

    # The switch cannot go off while the default is public.
    refused = await _privacy(admin, allow_public_recipes=False)
    assert refused.status_code == 422
    assert refused.json()["code"] == "PublicRecipesNotAllowedError"


async def test_switching_public_recipes_publishes_a_new_statement_version(
    admin: httpx.AsyncClient, client: httpx.AsyncClient
) -> None:
    draft = (await admin.get(f"{WEB}/admin/legal/privacy/draft")).json()["body"]
    first = await admin.post(
        f"{WEB}/admin/legal/privacy", headers=CSRF, json={"texts": {"en-GB": draft}}
    )
    assert first.status_code == 201, first.text
    page = (await client.get("/api/v1/public/legal/privacy")).json()
    assert "Public recipes are not allowed on this instance" in page["body"]

    assert (await _privacy(admin, allow_public_recipes=True)).status_code == 200
    renewed = (await client.get("/api/v1/public/legal/privacy")).json()
    assert renewed["version"] == first.json()["version"] + 1
    assert "Anyone on the internet can read a public recipe" in renewed["body"]
    versions = (await admin.get(f"{WEB}/admin/legal/privacy/versions")).json()
    assert versions[0]["allow_public_recipes"] is True
    assert versions[0]["privacy_mode"] == "peers"
    # The draft mentions public recipes in the deletion rules while allowed.
    draft = (await admin.get(f"{WEB}/admin/legal/privacy/draft")).json()["body"]
    assert "recipes visible to every member or public stay online" in draft

    # Saving the same values again publishes nothing.
    await _privacy(admin, allow_public_recipes=True)
    same = (await client.get("/api/v1/public/legal/privacy")).json()
    assert same["version"] == renewed["version"]


async def test_author_name_settings(cook: httpx.AsyncClient) -> None:
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert (me["show_name_on_public_recipes"], me["show_name_on_paired_instances"]) == (
        False,
        True,
    )
    changed = await cook.patch(
        f"{WEB}/users/me",
        headers=CSRF,
        json={"show_name_on_public_recipes": True, "show_name_on_paired_instances": False},
    )
    assert changed.status_code == 200, changed.text
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert (me["show_name_on_public_recipes"], me["show_name_on_paired_instances"]) == (
        True,
        False,
    )
    # A partial update leaves the other one alone.
    await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"show_name_on_public_recipes": False})
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert (me["show_name_on_public_recipes"], me["show_name_on_paired_instances"]) == (
        False,
        False,
    )
