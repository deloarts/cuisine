"""Sub-recipes: cycles and depth, scaling by yield and by servings,
derivation through hidden sub-recipes, and shopping expansion."""

from typing import Any

import httpx
import pytest

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import grant_health_data
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import unit_id


async def _sheets(cook: httpx.AsyncClient, **extra: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Lasagna sheets: 250 g flour and 2 eggs make 500 g."""
    g = await unit_id(cook, "g")
    piece = await unit_id(cook, "piece")
    flour = await make_ingredient(cook, "Mehl", kcal=350, allergens=["gluten"])
    egg = await make_ingredient(
        cook, "Ei", kcal=140, allergens=["eggs"], conversions=[{"unit_id": piece, "grams": 50}]
    )
    sheets = await make_recipe(
        cook,
        "Lasagneblätter",
        [
            (
                "Teig kneten",
                [
                    {"ingredient_id": flour["id"], "amount": 250, "unit_id": g},
                    {"ingredient_id": egg["id"], "amount": 2, "unit_id": piece},
                ],
            )
        ],
        yield_amount=500,
        yield_unit_id=g,
        **extra,
    )
    return sheets, flour


async def _lasagna(
    cook: httpx.AsyncClient, sheets_id: str, amount: float = 250, **extra: Any
) -> dict[str, Any]:
    g = await unit_id(cook, "g")
    tomato = await make_ingredient(cook, "Paradeiser", kcal=20)
    return await make_recipe(
        cook,
        "Lasagne",
        [
            (
                "Schichten",
                [
                    {"sub_recipe_id": sheets_id, "amount": amount, "unit_id": g},
                    {"ingredient_id": tomato["id"], "amount": 400, "unit_id": g},
                ],
            )
        ],
        **extra,
    )


async def _edit_body(client: httpx.AsyncClient, recipe_id: str) -> dict[str, Any]:
    edit = (await client.get(f"{WEB}/recipes/{recipe_id}/edit")).json()
    return {
        "original_locale": edit["original_locale"],
        "translations": edit["translations"],
        "base_servings": edit["base_servings"],
        "steps": [
            {
                "translations": s["translations"],
                "ingredients": [
                    {
                        k: v
                        for k, v in {
                            "ingredient_id": i["ingredient_id"],
                            "sub_recipe_id": i["sub_recipe_id"],
                            "amount": i["amount"],
                            "unit_id": i["unit_id"],
                        }.items()
                        if v is not None
                    }
                    for i in s["ingredients"]
                ],
            }
            for s in edit["steps"]
        ],
    }


async def test_scaling_by_yield_and_derivation(cook: httpx.AsyncClient) -> None:
    sheets, _ = await _sheets(cook)
    lasagna = await _lasagna(cook, sheets["id"])
    detail = (await cook.get(f"{WEB}/recipes/{lasagna['id']}")).json()
    need = detail["needs"][0]
    assert need["sub_recipe"]["title"] == "Lasagneblätter"
    assert need["batches"] == 0.5
    assert set(detail["allergens"]) == {"gluten", "eggs"}
    # Half a batch of sheets (125 g flour, one egg) and 400 g tomatoes over
    # two servings: (437.5 + 70 + 80) / 2, rounded to one decimal.
    assert detail["nutrition"]["per_serving"]["kcal"] == 293.8
    sub_line = detail["steps"][0]["ingredients"][0]
    assert sub_line["ingredient_id"] is None and sub_line["sub_recipe"]["accessible"] is True
    # The recipe's own ingredient list leaves the sub-recipe to `needs`. A
    # weight takes the plural, which the test helper writes as name + "n".
    assert [line["name"] for line in detail["ingredients"]] == ["Paradeisern"]
    doubled = (await cook.get(f"{WEB}/recipes/{lasagna['id']}", params={"servings": 4})).json()
    assert doubled["needs"][0]["batches"] == 1.0
    assert doubled["needs"][0]["amount"] == 500


async def test_scaling_by_servings_without_a_yield(cook: httpx.AsyncClient) -> None:
    g = await unit_id(cook, "g")
    oil = await make_ingredient(cook, "Öl", kcal=900)
    sauce = await make_recipe(
        cook,
        "Sauce",
        [("Rühren", [{"ingredient_id": oil["id"], "amount": 40, "unit_id": g}])],
    )
    # recipe_payload makes two base servings; one serving of sauce is half.
    bowl = await make_recipe(
        cook, "Bowl", [("Anrichten", [{"sub_recipe_id": sauce["id"], "amount": 1}])]
    )
    detail = (await cook.get(f"{WEB}/recipes/{bowl['id']}")).json()
    assert detail["needs"][0]["batches"] == 0.5
    # 20 g oil over two servings.
    assert detail["nutrition"]["per_serving"]["kcal"] == 90


async def test_cycles_are_refused(cook: httpx.AsyncClient) -> None:
    sheets, _ = await _sheets(cook)
    lasagna = await _lasagna(cook, sheets["id"])
    body = await _edit_body(cook, sheets["id"])
    body["steps"][0]["ingredients"].append({"sub_recipe_id": lasagna["id"], "amount": 1})
    refused = await cook.put(f"{WEB}/recipes/{sheets['id']}", headers=CSRF, json=body)
    assert refused.status_code == 422
    assert refused.json()["code"] == "SubRecipeCycleError"
    itself = await _edit_body(cook, sheets["id"])
    itself["steps"][0]["ingredients"].append({"sub_recipe_id": sheets["id"], "amount": 1})
    assert (
        await cook.put(f"{WEB}/recipes/{sheets['id']}", headers=CSRF, json=itself)
    ).status_code == 422


async def test_nesting_is_capped_at_three_levels(cook: httpx.AsyncClient) -> None:
    salt = await make_ingredient(cook, "Salz")
    bottom = await make_recipe(cook, "Ebene 3", [("x", [{"ingredient_id": salt["id"]}])])
    chain = bottom
    for level in (2, 1, 0):
        chain = await make_recipe(
            cook, f"Ebene {level}", [("x", [{"sub_recipe_id": chain["id"], "amount": 1}])]
        )
    # Ebene 0 > 1 > 2 > 3: three levels below the top are allowed.
    too_deep = await cook.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json=recipe_payload("Ebene -1", [("x", [{"sub_recipe_id": chain["id"], "amount": 1}])]),
    )
    assert too_deep.status_code == 422
    assert too_deep.json()["code"] == "SubRecipeTooDeepError"
    # Hanging another level under the bottom breaks the cap from below.
    deeper = await make_recipe(cook, "Ebene 4", [("x", [{"ingredient_id": salt["id"]}])])
    body = await _edit_body(cook, bottom["id"])
    body["steps"][0]["ingredients"] = [{"sub_recipe_id": deeper["id"], "amount": 1}]
    refused = await cook.put(f"{WEB}/recipes/{bottom['id']}", headers=CSRF, json=body)
    assert refused.status_code == 422


@pytest.mark.usefixtures("user_choice_privacy")
async def test_hidden_sub_recipe_still_counts(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    sheets, _ = await _sheets(cook, visibility="private")
    lasagna = await _lasagna(cook, sheets["id"])
    edit = (await cook.get(f"{WEB}/recipes/{lasagna['id']}/edit")).json()
    assert edit["less_visible_sub_recipe_ids"] == [sheets["id"]]

    await make_user("guest")
    await login(client, "guest@example.com", "cook-password-1")
    await grant_health_data(client)
    await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "allergy", "allergen": "eggs"},
    )
    detail = (await client.get(f"{WEB}/recipes/{lasagna['id']}")).json()
    assert detail["needs"][0]["sub_recipe"] == {
        "id": None,
        "title": None,
        "accessible": False,
        "total_minutes": None,
        "cover_image_id": None,
    }
    assert detail["steps"][0]["ingredients"][0]["name"] == ""
    assert "eggs" in detail["allergens"]
    assert detail["has_warning"] is True
    assert detail["warnings"][0]["ingredient_names"] == ["Ei"]
    assert sheets["id"] not in str(detail)
    listed = (await client.get(f"{WEB}/recipes")).json()["items"][0]
    assert listed["has_warning"] is True


async def test_shopping_expands_sub_recipes_or_buys_them(cook: httpx.AsyncClient) -> None:
    sheets, flour = await _sheets(cook)
    lasagna = await _lasagna(cook, sheets["id"])
    expanded = (await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "A"})).json()
    await cook.post(
        f"{WEB}/shopping-lists/{expanded['id']}/recipes",
        headers=CSRF,
        json={"recipe_id": lasagna["id"]},
    )
    items = {
        i["name"]: i
        for i in (await cook.get(f"{WEB}/shopping-lists/{expanded['id']}")).json()["items"]
    }
    assert items["Mehl"]["amount"] == 125
    assert items["Mehl"]["recipe"]["title"] == "Lasagne"
    assert [p["title"] for p in items["Mehl"]["sub_recipe_path"]] == ["Lasagneblätter"]
    assert items["Paradeiser"]["sub_recipe_path"] == []

    bought = (await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "B"})).json()
    await cook.post(
        f"{WEB}/shopping-lists/{bought['id']}/recipes",
        headers=CSRF,
        json={"recipe_id": lasagna["id"], "bought_sub_recipe_ids": [sheets["id"]]},
    )
    names = {
        i["name"]: i
        for i in (await cook.get(f"{WEB}/shopping-lists/{bought['id']}")).json()["items"]
    }
    assert set(names) == {"Lasagneblätter", "Paradeiser"}
    assert names["Lasagneblätter"]["ingredient_id"] is None
    assert names["Lasagneblätter"]["amount"] == 250
    del flour


async def test_meal_plan_week_takes_bought_sub_recipes(cook: httpx.AsyncClient) -> None:
    sheets, _ = await _sheets(cook)
    lasagna = await _lasagna(cook, sheets["id"])
    other = await make_recipe(cook, "Suppe", [("Kochen.", [])])
    for recipe in (lasagna, other):
        planned = await cook.post(
            f"{WEB}/meal-plan",
            headers=CSRF,
            json={
                "plan_date": "2026-11-23",
                "slot": "dinner",
                "recipe_id": recipe["id"],
                "servings": 2,
            },
        )
        assert planned.status_code == 201, planned.text
    week = {"date_from": "2026-11-23", "date_to": "2026-11-29"}
    target = (await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "W"})).json()
    added = await cook.post(
        f"{WEB}/meal-plan/shopping-list",
        headers=CSRF,
        json={**week, "list_id": target["id"], "bought_sub_recipe_ids": [sheets["id"]]},
    )
    assert added.status_code == 200, added.text
    items = (await cook.get(f"{WEB}/shopping-lists/{target['id']}")).json()["items"]
    assert {i["name"] for i in items} == {"Lasagneblätter", "Paradeiser"}
    refused = await cook.post(
        f"{WEB}/meal-plan/shopping-list",
        headers=CSRF,
        json={**week, "list_id": target["id"], "bought_sub_recipe_ids": [other["id"]]},
    )
    assert refused.status_code == 404


async def test_a_used_sub_recipe_cannot_be_deleted(cook: httpx.AsyncClient) -> None:
    sheets, _ = await _sheets(cook)
    await _lasagna(cook, sheets["id"])
    refused = await cook.delete(f"{WEB}/recipes/{sheets['id']}", headers=CSRF)
    assert refused.status_code == 409


async def test_agent_links_a_sub_recipe(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    from tests.integration.test_mcp import _cook_token
    from tests.integration.test_mcp import call

    token = await _cook_token(make_user, client)
    sheets, _ = await _sheets(client)
    result = await call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "Lasagne",
            "steps": [
                {
                    "text": "Schichten",
                    "ingredients": [{"sub_recipe_id": sheets["id"], "amount": 500, "unit": "g"}],
                }
            ],
        },
    )
    assert result["isError"] is False, result
    detail = (await client.get(f"{WEB}/recipes/{result['structuredContent']['id']}")).json()
    assert detail["needs"][0]["batches"] == 1.0
