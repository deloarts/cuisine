"""Extended nutrients on ingredients and recipes, and seasonality: ingredient
season months, a recipe's season, the in-season filter and the home section."""

from datetime import UTC
from datetime import datetime
from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id
from tests.integration.test_mcp import EXPIRES
from tests.integration.test_mcp import call


async def agent_token(make_user: MakeUser, client: httpx.AsyncClient) -> str:
    """A cook with the AI agents consent and an agent token."""
    permissions = ["write:recipes", "write:ingredients", "use:mcp", "write:pat"]
    await make_user("chef", permissions=permissions)
    await login(client, "chef@example.com", "cook-password-1")
    consent = await client.put(f"{WEB}/users/me/consents/ai_agents", headers=CSRF)
    assert consent.status_code == 200, consent.text
    created = await client.post(
        f"{WEB}/users/me/personal-access-tokens",
        headers=CSRF,
        json={
            "name": "agent",
            "permissions": ["use:mcp", "write:recipes", "write:ingredients"],
            "expires_at": EXPIRES,
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["token"])


THIS_MONTH = datetime.now(UTC).month
OTHER_MONTH = THIS_MONTH % 12 + 1


async def _ingredient(
    client: httpx.AsyncClient,
    name: str,
    *,
    extended: dict[str, Any] | None = None,
    season: list[int] | None = None,
    kcal: float | None = 100,
) -> dict[str, Any]:
    response = await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": name}},
            "nutrition": {"kcal": kcal},
            "extended_nutrition": extended or {},
            "season_months": season or [],
        },
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _line(ingredient: dict[str, Any], grams_unit: str, amount: float) -> dict[str, Any]:
    return {"ingredient_id": ingredient["id"], "amount": amount, "unit_id": grams_unit}


async def test_the_catalogue_lists_every_key_with_its_unit(cook: httpx.AsyncClient) -> None:
    nutrients = (await cook.get(f"{WEB}/nutrition/nutrients")).json()
    keys = [n["key"] for n in nutrients]
    assert len(keys) == 22
    assert keys[:2] == ["cholesterol_mg", "caffeine_mg"]
    vitamin_c = next(n for n in nutrients if n["key"] == "vitamin_c_mg")
    assert vitamin_c == {
        "key": "vitamin_c_mg",
        "unit": "mg",
        "label_key": "nutrients.vitamin_c_mg",
        "usda_nutrient_id": 1162,
    }


async def test_ingredient_round_trips_extended_nutrients_and_season(
    cook: httpx.AsyncClient,
) -> None:
    created = await _ingredient(
        cook,
        "Marille",
        extended={"vitamin_c_mg": 10, "potassium_mg": 259, "iron_mg": None},
        season=[8, 7, 7],
    )
    assert created["extended_nutrition"] == {"vitamin_c_mg": 10.0, "potassium_mg": 259.0}
    assert created["season_months"] == [7, 8]
    read = (await cook.get(f"{WEB}/ingredients/{created['id']}")).json()
    assert read["extended_nutrition"] == created["extended_nutrition"]
    updated = await cook.put(
        f"{WEB}/ingredients/{created['id']}",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": "Marille"}},
            "extended_nutrition": {"zinc_mg": 0.2},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["extended_nutrition"] == {"zinc_mg": 0.2}
    assert updated.json()["season_months"] == []


async def test_unknown_nutrients_and_months_are_refused(cook: httpx.AsyncClient) -> None:
    base = {"original_locale": "de-AT", "translations": {"de-AT": {"name": "Kriecherl"}}}
    unknown = await cook.post(
        f"{WEB}/ingredients", headers=CSRF, json={**base, "extended_nutrition": {"vitamin_x": 1}}
    )
    assert unknown.status_code == 422
    assert "vitamin_x" in unknown.text
    negative = await cook.post(
        f"{WEB}/ingredients", headers=CSRF, json={**base, "extended_nutrition": {"iron_mg": -1}}
    )
    assert negative.status_code == 422
    month = await cook.post(
        f"{WEB}/ingredients", headers=CSRF, json={**base, "season_months": [13]}
    )
    assert month.status_code == 422


async def test_recipe_sums_extended_nutrients_per_serving_through_sub_recipes(
    cook: httpx.AsyncClient,
) -> None:
    g = await unit_id(cook, "g")
    flour = await _ingredient(cook, "Mehl", extended={"iron_mg": 1.0, "zinc_mg": 2.0})
    egg = await _ingredient(cook, "Ei", extended={"iron_mg": 2.0})
    dough = await make_recipe(cook, "Teig", [("Kneten.", [_line(egg, g, 100)])], base_servings=1)
    recipe = await make_recipe(
        cook,
        "Nockerl",
        [
            (
                "Mischen.",
                [
                    _line(flour, g, 200),
                    {"sub_recipe_id": dough["id"], "amount": 1, "unit_id": None},
                ],
            )
        ],
    )
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    extended = {e["key"]: e for e in detail["nutrition"]["extended"]}
    # 200 g flour (2 mg iron, 4 mg zinc) plus one serving of dough (100 g
    # egg, 2 mg iron); two servings.
    assert extended["iron_mg"] == {
        "key": "iron_mg",
        "unit": "mg",
        "total": 4.0,
        "per_serving": 2.0,
        "complete": True,
    }
    assert extended["zinc_mg"]["total"] == 4.0
    assert extended["zinc_mg"]["complete"] is False
    assert "vitamin_c_mg" not in extended
    doubled = (await cook.get(f"{WEB}/recipes/{recipe['id']}", params={"servings": 4})).json()
    iron = next(e for e in doubled["nutrition"]["extended"] if e["key"] == "iron_mg")
    assert iron["total"] == 8.0
    assert iron["per_serving"] == 2.0


async def test_an_unweighable_line_makes_every_extended_value_incomplete(
    cook: httpx.AsyncClient,
) -> None:
    g = await unit_id(cook, "g")
    piece = await unit_id(cook, "piece")
    flour = await _ingredient(cook, "Grieß", extended={"iron_mg": 1.0})
    lemon = await _ingredient(cook, "Zitrone", extended={"iron_mg": 1.0})
    recipe = await make_recipe(
        cook,
        "Grießnockerl",
        [("Rühren.", [_line(flour, g, 100), _line(lemon, piece, 1)])],
    )
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    iron = next(e for e in detail["nutrition"]["extended"] if e["key"] == "iron_mg")
    assert iron["total"] == 1.0
    assert iron["complete"] is False


async def test_recipe_season_filter_and_home_section(cook: httpx.AsyncClient) -> None:
    g = await unit_id(cook, "g")
    now = await _ingredient(cook, "Spargel", season=[THIS_MONTH, OTHER_MONTH])
    later = await _ingredient(cook, "Kürbis", season=[OTHER_MONTH])
    salt = await _ingredient(cook, "Salz")
    fresh = await make_recipe(
        cook, "Spargelsalat", [("Schneiden.", [_line(now, g, 300), _line(salt, g, 2)])]
    )
    mixed = await make_recipe(
        cook, "Gemüsepfanne", [("Braten.", [_line(now, g, 100), _line(later, g, 100)])]
    )
    plain = await make_recipe(cook, "Salzwasser", [("Kochen.", [_line(salt, g, 5)])])
    # A recipe whose only seasonal ingredient comes through a sub-recipe.
    wrapped = await make_recipe(
        cook,
        "Spargelquiche",
        [("Backen.", [{"sub_recipe_id": fresh["id"], "amount": 1, "unit_id": None}])],
    )

    detail = (await cook.get(f"{WEB}/recipes/{fresh['id']}")).json()
    assert detail["season_months"] == sorted([THIS_MONTH, OTHER_MONTH])
    assert detail["in_season"] is True
    mixed_detail = (await cook.get(f"{WEB}/recipes/{mixed['id']}")).json()
    assert mixed_detail["season_months"] == [OTHER_MONTH]
    assert mixed_detail["in_season"] is False
    plain_detail = (await cook.get(f"{WEB}/recipes/{plain['id']}")).json()
    assert plain_detail["season_months"] == []
    assert plain_detail["in_season"] is False

    listed = (await cook.get(f"{WEB}/recipes", params={"in_season": "true"})).json()
    assert {r["id"] for r in listed["items"]} == {fresh["id"], wrapped["id"]}
    assert listed["total"] == 2

    home = (await cook.get(f"{WEB}/home")).json()
    assert {r["id"] for r in home["in_season"]} == {fresh["id"], wrapped["id"]}


async def test_agent_creates_an_ingredient_with_extended_nutrients(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await agent_token(make_user, client)
    result = await call(
        client,
        token,
        "create_ingredient",
        {
            "original_locale": "de-AT",
            "names": {"de-AT": {"name": "Ribisel"}},
            "extended_nutrition_per_100g": {"vitamin_c_mg": 41},
            "season_months": [6, 7],
        },
    )
    assert not result.get("isError"), result
    ingredient_id = result["structuredContent"]["id"]
    read = (await client.get(f"{WEB}/ingredients/{ingredient_id}")).json()
    assert read["extended_nutrition"] == {"vitamin_c_mg": 41.0}
    assert read["season_months"] == [6, 7]
    refused = await call(
        client,
        token,
        "create_ingredient",
        {
            "original_locale": "de-AT",
            "names": {"de-AT": {"name": "Stachelbeere"}},
            "extended_nutrition_per_100g": {"sugar_free": 1},
        },
    )
    assert refused.get("isError")
