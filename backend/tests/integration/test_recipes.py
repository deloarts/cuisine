"""Recipes: drafts and publishing, derived ingredients and nutrition,
translations, browsing filters and the viewer's personal layer."""

from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import tag_id
from tests.integration.cookbook_helpers import unit_id


async def _pancakes(cook: httpx.AsyncClient, *, publish: bool = True) -> dict[str, Any]:
    g = await unit_id(cook, "g")
    piece = await unit_id(cook, "piece")
    # Flour is uncountable, so its plural is its name: "300 g Mehl".
    flour = await make_ingredient(
        cook,
        "Mehl",
        kcal=350,
        allergens=["gluten"],
        english="Flour",
        plural="Mehl",
        english_plural="Flour",
    )
    egg = await make_ingredient(
        cook,
        "Ei",
        kcal=140,
        allergens=["eggs"],
        conversions=[{"unit_id": piece, "grams": 50}],
        english="Egg",
        plural="Eier",
        english_plural="Eggs",
    )
    return await make_recipe(
        cook,
        "Palatschinken",
        [
            (
                "Mehl und Eier verrühren",
                [
                    {"ingredient_id": flour["id"], "amount": 100, "unit_id": g},
                    {
                        "ingredient_id": egg["id"],
                        "amount": 2,
                        "unit_id": piece,
                        "notes": {"de-AT": {"note": "zimmerwarm"}},
                    },
                ],
            ),
            ("Mehr Mehl dazu", [{"ingredient_id": flour["id"], "amount": 50, "unit_id": g}]),
        ],
        publish=publish,
        tag_ids=[await tag_id(cook, "Dessert")],
    )


async def test_create_starts_as_draft_and_publishes(cook: httpx.AsyncClient) -> None:
    draft = await _pancakes(cook, publish=False)
    assert draft["status"] == "draft"
    assert draft["can_edit"] is True
    published = await cook.post(f"{WEB}/recipes/{draft['id']}/publish", headers=CSRF)
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None


async def test_drafts_are_invisible_to_others(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    draft = await _pancakes(cook, publish=False)
    await make_user("guest")
    await login(client, "guest@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/recipes/{draft['id']}")).status_code == 404
    listed = (await client.get(f"{WEB}/recipes")).json()
    assert listed["total"] == 0


async def test_drafts_stay_private_even_for_managers(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    draft = await _pancakes(cook, publish=False)
    drafts = (await admin.get(f"{WEB}/recipes", params={"status": "drafts"})).json()
    assert drafts["total"] == 0
    assert (await admin.get(f"{WEB}/recipes/{draft['id']}/edit")).status_code == 404
    await cook.post(f"{WEB}/recipes/{draft['id']}/publish", headers=CSRF)
    edit = (await admin.get(f"{WEB}/recipes/{draft['id']}/edit")).json()
    assert edit["can_edit"] is True
    assert edit["can_change_visibility"] is False


async def test_publishing_needs_a_step(cook: httpx.AsyncClient) -> None:
    created = await cook.post(f"{WEB}/recipes", headers=CSRF, json=recipe_payload("Leer", []))
    assert created.status_code == 201
    refused = await cook.post(f"{WEB}/recipes/{created.json()['id']}/publish", headers=CSRF)
    assert refused.status_code == 422


async def test_detail_derives_ingredients_and_nutrition(cook: httpx.AsyncClient) -> None:
    recipe = await _pancakes(cook)
    detail = (
        await cook.get(f"{WEB}/recipes/{recipe['id']}", params={"servings": 4, "locale": "de-AT"})
    ).json()
    assert detail["servings"] == 4
    lines = {line["name"]: line for line in detail["ingredients"]}
    # 150 g flour and 2 eggs for two servings, doubled.
    assert lines["Mehl"]["amount"] == 300
    assert lines["Mehl"]["unit"]["code"] == "g"
    # A count of pieces takes the plural: "4 Eier".
    assert lines["Eier"]["amount"] == 4
    first_step = detail["steps"][0]
    assert first_step["ingredients"][1]["note"] == "zimmerwarm"
    assert first_step["ingredients"][0]["amount"] == 200
    # 150 g flour (525 kcal) and 100 g egg (140 kcal) over two servings.
    assert detail["nutrition"]["per_serving"]["kcal"] == 332.5
    assert detail["nutrition"]["complete"] is True
    assert set(detail["allergens"]) == {"eggs", "gluten"}
    assert detail["total_minutes"] == 30
    assert [t["name"] for t in detail["tags"]] == ["Dessert"]


async def test_translation_fallback_and_adding_a_language(cook: httpx.AsyncClient) -> None:
    recipe = await _pancakes(cook)
    english = (await cook.get(f"{WEB}/recipes/{recipe['id']}", params={"locale": "en-GB"})).json()
    assert english["title"] == "Palatschinken"
    assert english["locale"] == "de-AT"
    assert english["available_locales"] == ["de-AT"]
    saved = await cook.put(
        f"{WEB}/recipes/{recipe['id']}/translation",
        headers=CSRF,
        json={
            "locale": "en-GB",
            "text": {"title": "Pancakes"},
            "steps": [{"text": "Whisk flour and eggs"}, {"text": "Add more flour"}],
        },
    )
    assert saved.status_code == 200, saved.text
    english = (await cook.get(f"{WEB}/recipes/{recipe['id']}", params={"locale": "en-GB"})).json()
    assert english["title"] == "Pancakes"
    assert english["steps"][0]["text"] == "Whisk flour and eggs"
    lines = {line["name"] for line in english["ingredients"]}
    assert lines == {"Flour", "Eggs"}


async def test_list_filters_and_search(cook: httpx.AsyncClient) -> None:
    recipe = await _pancakes(cook)
    by_title = (await cook.get(f"{WEB}/recipes", params={"search": "palat"})).json()
    assert by_title["total"] == 1
    by_ingredient = (await cook.get(f"{WEB}/recipes", params={"search": "flour"})).json()
    assert by_ingredient["total"] == 1
    by_tag = (
        await cook.get(f"{WEB}/recipes", params={"tag_id": await tag_id(cook, "Dinner")})
    ).json()
    assert by_tag["total"] == 0
    quick = (await cook.get(f"{WEB}/recipes", params={"max_minutes": 15})).json()
    assert quick["total"] == 0
    summary = (await cook.get(f"{WEB}/recipes")).json()["items"][0]
    assert summary["id"] == recipe["id"]
    assert summary["owner"]["display_name"] == "Cook"


async def test_editing_others_recipes_needs_manage(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _pancakes(cook)
    await make_user("other", permissions=["write:recipes"])
    await login(client, "other@example.com", "cook-password-1")
    refused = await client.put(
        f"{WEB}/recipes/{recipe['id']}", headers=CSRF, json=recipe_payload("X", [])
    )
    assert refused.status_code == 403
    assert (await client.delete(f"{WEB}/recipes/{recipe['id']}", headers=CSRF)).status_code == 403


async def test_unknown_references_answer_404(cook: httpx.AsyncClient) -> None:
    bad = recipe_payload(
        "X",
        [("Schritt", [{"ingredient_id": "00000000-0000-0000-0000-000000000000", "amount": 1}])],
    )
    assert (await cook.post(f"{WEB}/recipes", headers=CSRF, json=bad)).status_code == 404


async def test_favourite_rating_and_private_note(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _pancakes(cook)
    rid = recipe["id"]
    assert (
        await cook.put(f"{WEB}/recipes/{rid}/favourite", headers=CSRF, json={"favourite": True})
    ).status_code == 204
    rated = await cook.put(f"{WEB}/recipes/{rid}/rating", headers=CSRF, json={"stars": 4})
    assert rated.json()["rating_average"] == 4
    await cook.put(f"{WEB}/recipes/{rid}/note", headers=CSRF, json={"text": "weniger Zucker"})
    detail = (await cook.get(f"{WEB}/recipes/{rid}")).json()
    assert detail["is_favourite"] is True
    assert detail["own_rating"] == {"stars": 4, "comment": ""}
    assert detail["own_note"] == "weniger Zucker"
    favourites = (await cook.get(f"{WEB}/recipes", params={"favourites": True})).json()
    assert favourites["total"] == 1

    await make_user("guest")
    await login(client, "guest@example.com", "cook-password-1")
    theirs = (await client.get(f"{WEB}/recipes/{rid}")).json()
    assert theirs["own_note"] is None
    assert theirs["is_favourite"] is False
    assert theirs["rating_count"] == 1
    await client.put(f"{WEB}/recipes/{rid}/rating", headers=CSRF, json={"stars": 2})
    assert (await client.get(f"{WEB}/recipes/{rid}")).json()["rating_average"] == 3


async def test_ingredient_recipe_count(cook: httpx.AsyncClient) -> None:
    recipe = await _pancakes(cook)
    edit = (await cook.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    flour_id = edit["steps"][0]["ingredients"][0]["ingredient_id"]
    flour = (await cook.get(f"{WEB}/ingredients/{flour_id}")).json()
    assert flour["recipe_count"] == 1
