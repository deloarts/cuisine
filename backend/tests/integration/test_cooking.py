"""The cooking calendar and the meal plan."""

from datetime import date
from datetime import timedelta

import httpx

from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id

TODAY = date.today()


async def _soup(cook: httpx.AsyncClient) -> dict[str, str]:
    onion = await make_ingredient(cook, "Zwiebel")
    g = await unit_id(cook, "g")
    recipe = await make_recipe(
        cook,
        "Zwiebelsuppe",
        [("Kochen", [{"ingredient_id": onion["id"], "amount": 200, "unit_id": g}])],
    )
    return {"recipe": recipe["id"], "onion": onion["id"]}


async def test_cook_events_show_in_everyones_calendar(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    ids = await _soup(cook)
    created = await cook.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={"recipe_id": ids["recipe"], "cooked_on": TODAY.isoformat(), "servings": 3},
    )
    assert created.status_code == 201
    assert created.json()["is_own"] is True
    calendar = (
        await admin.get(
            f"{WEB}/cook-events",
            params={
                "date_from": (TODAY - timedelta(days=7)).isoformat(),
                "date_to": TODAY.isoformat(),
            },
        )
    ).json()
    assert calendar[0]["recipe"]["title"] == "Zwiebelsuppe"
    assert calendar[0]["user"]["display_name"] == "Cook"
    assert calendar[0]["is_own"] is False
    refused = await admin.delete(f"{WEB}/cook-events/{created.json()['id']}", headers=CSRF)
    assert refused.status_code == 404
    detail = (await admin.get(f"{WEB}/recipes/{ids['recipe']}")).json()
    assert detail["last_cooked"] == TODAY.isoformat()


async def test_on_this_day_finds_last_year(cook: httpx.AsyncClient) -> None:
    ids = await _soup(cook)
    last_year = (
        TODAY.replace(year=TODAY.year - 1)
        if not (TODAY.month == 2 and TODAY.day == 29)
        else TODAY.replace(year=TODAY.year - 1, day=28)
    )
    await cook.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={"recipe_id": ids["recipe"], "cooked_on": last_year.isoformat(), "servings": 2},
    )
    found = (await cook.get(f"{WEB}/cook-events/on-this-day")).json()
    assert len(found) == 1
    home = (await cook.get(f"{WEB}/home")).json()
    assert len(home["on_this_day"]) == 1
    assert home["newest"][0]["title"] == "Zwiebelsuppe"


async def test_cook_events_cannot_lie_in_the_future(cook: httpx.AsyncClient) -> None:
    ids = await _soup(cook)
    refused = await cook.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={
            "recipe_id": ids["recipe"],
            "cooked_on": (TODAY + timedelta(days=10)).isoformat(),
            "servings": 2,
        },
    )
    assert refused.status_code == 422


async def test_meal_plan_is_personal_and_fills_a_shopping_list(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    ids = await _soup(cook)
    for day in (0, 1):
        added = await cook.post(
            f"{WEB}/meal-plan",
            headers=CSRF,
            json={
                "plan_date": (TODAY + timedelta(days=day)).isoformat(),
                "slot": "dinner",
                "recipe_id": ids["recipe"],
                "servings": 4,
            },
        )
        assert added.status_code == 201, added.text
    await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": TODAY.isoformat(), "slot": "lunch", "title": "Reste"},
    )
    week = {"date_from": TODAY.isoformat(), "date_to": (TODAY + timedelta(days=6)).isoformat()}
    assert len((await cook.get(f"{WEB}/meal-plan", params=week)).json()) == 3
    assert (await admin.get(f"{WEB}/meal-plan", params=week)).json() == []

    shopping = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Woche"})
    ).json()
    filled = await cook.post(
        f"{WEB}/meal-plan/shopping-list", headers=CSRF, json={**week, "list_id": shopping["id"]}
    )
    assert filled.json() == {"added": 2}
    items = (await cook.get(f"{WEB}/shopping-lists/{shopping['id']}")).json()["items"]
    # Two dinners of four servings each from a recipe for two: 4 × 200 g.
    assert len(items) == 1
    assert items[0]["amount"] == 800
