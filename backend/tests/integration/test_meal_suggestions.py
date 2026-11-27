"""Meal plan suggestions: only recipes the viewer may see, ranked from the
cooking history of the plan's scope, without what the week already plans
and with what was just cooked at the bottom."""

from datetime import date
from datetime import timedelta
from typing import Any

import httpx
import pytest

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import tag_id
from tests.integration.cookbook_helpers import unit_id

pytestmark = pytest.mark.usefixtures("user_choice_privacy")

TODAY = date.today()
MONDAY = TODAY - timedelta(days=TODAY.weekday())
WEEK = {"date_from": MONDAY.isoformat(), "date_to": (MONDAY + timedelta(days=6)).isoformat()}


async def _recipe(client: httpx.AsyncClient, title: str, **extra: Any) -> dict[str, Any]:
    ingredient = await make_ingredient(client, f"Zutat {title}")
    g = await unit_id(client, "g")
    return await make_recipe(
        client,
        title,
        [("Kochen", [{"ingredient_id": ingredient["id"], "amount": 100, "unit_id": g}])],
        **extra,
    )


async def _cooked(client: httpx.AsyncClient, recipe_id: str, *days_ago: int) -> None:
    for days in days_ago:
        response = await client.post(
            f"{WEB}/cook-events",
            headers=CSRF,
            json={
                "recipe_id": recipe_id,
                "cooked_on": (TODAY - timedelta(days=days)).isoformat(),
                "servings": 2,
            },
        )
        assert response.status_code == 201, response.text


async def _suggest(client: httpx.AsyncClient, **params: Any) -> list[dict[str, Any]]:
    response = await client.get(f"{WEB}/meal-plan/suggestions", params={**WEEK, **params})
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


def _titles(suggestions: list[dict[str, Any]]) -> list[str]:
    return [s["recipe"]["title"] for s in suggestions]


async def _household_of_two(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    partner = await make_user("partner")
    await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "Zuhause"})
    invitation = (
        await cook.post(
            f"{WEB}/households/mine/invitations", headers=CSRF, json={"user_id": partner["id"]}
        )
    ).json()
    await login(client, "partner@example.com", "cook-password-1")
    joined = await client.post(
        f"{WEB}/households/invitations/{invitation['id']}/accept", headers=CSRF
    )
    assert joined.status_code == 200, joined.text


async def test_only_visible_published_recipes_are_suggested(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await _recipe(cook, "Eigenes Geheimnis", visibility="private")
    await _recipe(cook, "Entwurf", publish=False)
    await _recipe(cook, "Für alle")
    await make_user("other", permissions=["write:recipes", "write:ingredients"])
    await login(client, "other@example.com", "cook-password-1")
    foreign = await _recipe(client, "Fremdes Geheimnis", visibility="private")
    # Even cooked often by its owner, a private recipe stays theirs.
    await _cooked(client, foreign["id"], 20, 40, 60)

    mine = await _suggest(cook)
    assert set(_titles(mine)) == {"Eigenes Geheimnis", "Für alle"}
    # The summary shape of the home page, with a reason.
    assert {"id", "title", "is_favourite", "in_season"} <= set(mine[0]["recipe"])
    assert all(s["reason"] for s in mine)
    assert set(_titles(await _suggest(client))) == {"Für alle", "Fremdes Geheimnis"}


async def test_cold_start_prefers_favourites_then_the_newest(cook: httpx.AsyncClient) -> None:
    first = await _recipe(cook, "Erstes")
    await _recipe(cook, "Zweites")
    await _recipe(cook, "Drittes")
    favourite = await cook.put(
        f"{WEB}/recipes/{first['id']}/favourite", headers=CSRF, json={"favourite": True}
    )
    assert favourite.status_code == 204, favourite.text

    suggestions = await _suggest(cook)
    assert _titles(suggestions) == ["Erstes", "Drittes", "Zweites"]
    assert suggestions[0]["reason"] == "favourite"
    assert suggestions[1]["reason"] == "new_recipe"
    assert len(await _suggest(cook, limit=2)) == 2


async def test_planned_recipes_drop_out_and_just_cooked_ones_sink(
    cook: httpx.AsyncClient,
) -> None:
    planned = await _recipe(cook, "Geplant")
    yesterday = await _recipe(cook, "Gestern gekocht")
    regular = await _recipe(cook, "Klassiker")
    await _recipe(cook, "Neu")
    await _cooked(cook, yesterday["id"], 1)
    await _cooked(cook, regular["id"], 30, 60, 90, 120)
    added = await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": WEEK["date_to"], "slot": "dinner", "recipe_id": planned["id"]},
    )
    assert added.status_code == 201, added.text

    suggestions = await _suggest(cook)
    titles = _titles(suggestions)
    assert "Geplant" not in titles
    assert titles[0] == "Klassiker"
    assert suggestions[0]["reason"] in {"often_cooked", "not_cooked_lately"}
    assert titles[-1] == "Gestern gekocht"
    # Another week does not plan it.
    later = {
        "date_from": (MONDAY + timedelta(days=7)).isoformat(),
        "date_to": (MONDAY + timedelta(days=13)).isoformat(),
    }
    assert "Geplant" in _titles(await _suggest(cook, **later))


async def test_the_scope_decides_whose_history_counts(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    await _household_of_two(cook, make_user, client)
    stew = await _recipe(cook, "Eintopf")
    await _recipe(cook, "Etwas Neues")
    # The partner cooks the stew regularly; the cook never did.
    await _cooked(client, stew["id"], 14, 28, 42, 56, 70)

    household = await _suggest(cook, scope="household")
    assert _titles(household)[0] == "Eintopf"
    assert household[0]["reason"] in {"often_cooked", "not_cooked_lately"}
    personal = await _suggest(cook, scope="personal")
    assert _titles(personal)[0] == "Etwas Neues"
    assert personal[1]["reason"] == "new_recipe"


async def test_slot_and_last_year(cook: httpx.AsyncClient) -> None:
    breakfast = await tag_id(cook, "Breakfast")
    main = await tag_id(cook, "Main course")
    await _recipe(cook, "Müsli", tag_ids=[breakfast])
    await _recipe(cook, "Braten", tag_ids=[main])
    goose = await _recipe(cook, "Gans", tag_ids=[main])
    await _cooked(cook, goose["id"], 365, 366 * 2)

    morning = await _suggest(cook, slot="breakfast")
    assert _titles(morning)[0] == "Müsli"
    assert morning[0]["reason"] == "fits_slot"
    assert _titles(morning)[-1] == "Braten"
    evening = await _suggest(cook, slot="dinner")
    assert _titles(evening)[0] == "Gans"
    assert evening[0]["reason"] == "cooked_this_time_last_year"


async def test_scope_and_range_are_checked(
    cook: httpx.AsyncClient, visitor: httpx.AsyncClient
) -> None:
    signed_out = await visitor.get(f"{WEB}/meal-plan/suggestions", params=WEEK)
    assert signed_out.status_code == 401
    no_household = await cook.get(
        f"{WEB}/meal-plan/suggestions", params={**WEEK, "scope": "household"}
    )
    assert no_household.status_code == 422
    too_long = await cook.get(
        f"{WEB}/meal-plan/suggestions",
        params={
            "date_from": MONDAY.isoformat(),
            "date_to": (MONDAY + timedelta(days=90)).isoformat(),
        },
    )
    assert too_long.status_code == 422
    assert (
        await cook.get(f"{WEB}/meal-plan/suggestions", params={**WEEK, "limit": 99})
    ).status_code == 422
