"""The ingredient catalogue and the USDA nutrition lookup."""

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import FakeNutritionLookup
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id


async def test_create_and_read_with_language_fallback(cook: httpx.AsyncClient) -> None:
    created = await make_ingredient(cook, "Paradeiser", kcal=18, allergens=["celery"])
    assert created["status"] == "active"
    assert created["can_edit"] is True
    english = (
        await cook.get(f"{WEB}/ingredients/{created['id']}", params={"locale": "en-GB"})
    ).json()
    assert english["name"] == "Paradeiser"
    assert english["locale"] == "de-AT"
    assert english["recipe_count"] == 0


async def test_search_finds_names_in_any_language(cook: httpx.AsyncClient) -> None:
    await make_ingredient(cook, "Erdapfel", english="Potato")
    await make_ingredient(cook, "Zwiebel", english="Onion")
    found = (
        await cook.get(f"{WEB}/ingredients", params={"search": "potat", "locale": "de-AT"})
    ).json()
    assert found["total"] == 1
    assert found["items"][0]["name"] == "Erdapfel"


async def test_creating_needs_write_ingredients(
    make_user: MakeUser, other_client: httpx.AsyncClient, resources: None
) -> None:
    await make_user("reader")
    await login(other_client, "reader@example.com", "cook-password-1")
    refused = await other_client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={"original_locale": "de-AT", "translations": {"de-AT": {"name": "Salz"}}},
    )
    assert refused.status_code == 403


async def test_only_owner_or_manager_edits(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
) -> None:
    mine = await make_ingredient(cook, "Kren")
    body = {"original_locale": "de-AT", "translations": {"de-AT": {"name": "Meerrettich"}}}
    # The admin is the system user and holds manage:ingredients implicitly.
    managed = await admin.put(f"{WEB}/ingredients/{mine['id']}", headers=CSRF, json=body)
    assert managed.status_code == 200
    assert managed.json()["name"] == "Meerrettich"


async def test_other_writer_cannot_edit(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    theirs = await make_ingredient(cook, "Kren")
    await make_user("second", permissions=["write:ingredients"])
    await login(client, "second@example.com", "cook-password-1")
    body = {"original_locale": "de-AT", "translations": {"de-AT": {"name": "X"}}}
    refused = await client.put(f"{WEB}/ingredients/{theirs['id']}", headers=CSRF, json=body)
    assert refused.status_code == 403


async def test_used_ingredient_cannot_be_deleted(cook: httpx.AsyncClient) -> None:
    flour = await make_ingredient(cook, "Mehl")
    await make_recipe(
        cook,
        "Brot",
        [
            (
                "Kneten",
                [
                    {
                        "ingredient_id": flour["id"],
                        "amount": 500,
                        "unit_id": await unit_id(cook, "g"),
                    }
                ],
            )
        ],
    )
    refused = await cook.delete(f"{WEB}/ingredients/{flour['id']}", headers=CSRF)
    assert refused.status_code == 409
    unused = await make_ingredient(cook, "Germ")
    assert (await cook.delete(f"{WEB}/ingredients/{unused['id']}", headers=CSRF)).status_code == 204


async def test_original_language_is_required(cook: httpx.AsyncClient) -> None:
    refused = await cook.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={"original_locale": "de-AT", "translations": {"en-GB": {"name": "Salt"}}},
    )
    assert refused.status_code == 422


async def test_usda_lookup_uses_the_configured_key(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient, usda: FakeNutritionLookup
) -> None:
    found = (await cook.get(f"{WEB}/nutrition/usda/search", params={"query": "egg"})).json()
    assert found[0]["nutrition"]["kcal"] == 143
    assert usda.keys == ["DEMO_KEY"]
    saved = await admin.put(
        f"{WEB}/settings/integrations",
        headers=CSRF,
        json={"usda_enabled": True, "usda_api_key": "my-key"},
    )
    assert saved.json() == {
        "usda_enabled": True,
        "usda_api_key_set": True,
        "usda_uses_demo_key": False,
    }
    assert (await cook.get(f"{WEB}/nutrition/usda/171287")).status_code == 200
    assert usda.keys[-1] == "my-key"


async def test_usda_lookup_can_be_switched_off(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    await admin.put(f"{WEB}/settings/integrations", headers=CSRF, json={"usda_enabled": False})
    refused = await cook.get(f"{WEB}/nutrition/usda/search", params={"query": "egg"})
    assert refused.status_code == 503
