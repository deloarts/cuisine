"""Diets, diet markers, restrictions by ingredient name and dinner guests.

The guest check must never tell the host which guest or which restriction
conflicts, nor whether a guest opted in."""

import json
from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import grant_health_data
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id


async def _ingredient(
    client: httpx.AsyncClient, name: str, markers: list[str], allergens: list[str] | None = None
) -> dict[str, Any]:
    created = await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": name}},
            "diet_markers": markers,
            "allergens": allergens or [],
        },
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


async def _recipes(cook: httpx.AsyncClient) -> dict[str, str]:
    g = await unit_id(cook, "g")
    bacon = await _ingredient(cook, "Speck", ["meat", "pork"])
    cheese = await _ingredient(cook, "Käse", ["dairy"], ["milk"])
    rice = await _ingredient(cook, "Reis", [])
    meat = await make_recipe(
        cook,
        "Speckknödel",
        [("Kochen", [{"ingredient_id": bacon["id"], "amount": 100, "unit_id": g}])],
    )
    veggie = await make_recipe(
        cook,
        "Käsespätzle",
        [("Kochen", [{"ingredient_id": cheese["id"], "amount": 100, "unit_id": g}])],
    )
    vegan = await make_recipe(
        cook, "Reis", [("Kochen", [{"ingredient_id": rice["id"], "amount": 100, "unit_id": g}])]
    )
    return {"meat": meat["id"], "veggie": veggie["id"], "vegan": vegan["id"]}


async def _guest(
    make_user: MakeUser,
    client: httpx.AsyncClient,
    name: str,
    restriction: dict[str, Any],
    *,
    opt_in: bool,
) -> str:
    """A user with one restriction, opted in or not; returns their id."""
    user = await make_user(name)
    await login(client, f"{name}@example.com", "cook-password-1")
    await grant_health_data(client)
    added = await client.post(f"{WEB}/users/me/food-restrictions", headers=CSRF, json=restriction)
    assert added.status_code == 201, added.text
    saved = await client.patch(
        f"{WEB}/users/me", headers=CSRF, json={"share_restrictions_with_hosts": opt_in}
    )
    assert saved.json()["share_restrictions_with_hosts"] is opt_in
    return str(user["id"])


def _by_id(page: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in page["items"]}


async def test_markers_derive_diets_and_filter(cook: httpx.AsyncClient) -> None:
    ids = await _recipes(cook)
    page = _by_id((await cook.get(f"{WEB}/recipes")).json())
    assert "vegetarian" not in page[ids["meat"]]["diets"]
    assert "no_pork" not in page[ids["meat"]]["diets"]
    assert "vegetarian" in page[ids["veggie"]]["diets"]
    assert "vegan" not in page[ids["veggie"]]["diets"]
    assert "vegan" in page[ids["vegan"]]["diets"]
    vegetarian = (await cook.get(f"{WEB}/recipes", params={"diets": "vegetarian"})).json()
    assert set(_by_id(vegetarian)) == {ids["veggie"], ids["vegan"]}
    both = (
        await cook.get(f"{WEB}/recipes", params=[("diets", "vegetarian"), ("diets", "vegan")])
    ).json()
    assert set(_by_id(both)) == {ids["vegan"]}
    detail = (await cook.get(f"{WEB}/recipes/{ids['veggie']}")).json()
    assert "vegetarian" in detail["diets"]


async def test_own_diet_restriction_warns(cook: httpx.AsyncClient) -> None:
    ids = await _recipes(cook)
    await grant_health_data(cook)
    await cook.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "diet", "diet": "vegetarian"},
    )
    detail = (await cook.get(f"{WEB}/recipes/{ids['meat']}")).json()
    assert detail["has_warning"] is True
    assert detail["warnings"][0]["diet"] == "vegetarian"
    assert detail["warnings"][0]["ingredient_names"] == ["Speck"]
    mismatched = await cook.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "allergy", "diet": "vegan"},
    )
    assert mismatched.status_code == 422


async def test_restriction_by_name_creates_or_reuses_an_ingredient(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    await make_user("reader")
    await login(client, "reader@example.com", "cook-password-1")
    await grant_health_data(client)
    first = await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "intolerance", "ingredient_name": "Apfel"},
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "intolerance", "ingredient_name": "APFEL"},
    )
    assert second.json()["ingredient_id"] == first.json()["ingredient_id"]
    ingredient = (await client.get(f"{WEB}/ingredients/{first.json()['ingredient_id']}")).json()
    assert ingredient["status"] == "draft"
    assert ingredient["name"] == "Apfel"
    # Only this path creates ingredients without write:ingredients.
    refused = await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={"original_locale": "de-AT", "translations": {"de-AT": {"name": "Birne"}}},
    )
    assert refused.status_code == 403


async def test_opted_in_guest_marks_unsuitable_recipes_only(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    ids = await _recipes(cook)
    anna = await _guest(
        make_user, client, "anna", {"kind": "diet", "diet": "vegetarian"}, opt_in=True
    )
    page = (await cook.get(f"{WEB}/recipes", params={"guests": anna})).json()
    flags = {r["id"]: r["unsuitable_for_guests"] for r in page["items"]}
    assert flags == {ids["meat"]: True, ids["veggie"]: False, ids["vegan"]: False}
    hidden = (
        await cook.get(
            f"{WEB}/recipes", params={"guests": anna, "hide_unsuitable_for_guests": True}
        )
    ).json()
    assert set(_by_id(hidden)) == {ids["veggie"], ids["vegan"]}
    assert hidden["total"] == 2
    detail = (await cook.get(f"{WEB}/recipes/{ids['meat']}", params={"guests": anna})).json()
    assert detail["unsuitable_for_guests"] is True
    # The host's own view carries no warning of the guest's.
    assert detail["has_warning"] is False
    assert detail["warnings"] == []


async def test_guest_responses_reveal_nothing_per_guest(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    ids = await _recipes(cook)
    anna = await _guest(
        make_user, client, "anna", {"kind": "diet", "diet": "vegetarian"}, opt_in=True
    )
    plain = (await cook.get(f"{WEB}/recipes/{ids['meat']}")).json()
    with_guest = (await cook.get(f"{WEB}/recipes/{ids['meat']}", params={"guests": anna})).json()
    # The only difference is the one boolean.
    assert {k: v for k, v in with_guest.items() if k != "unsuitable_for_guests"} == {
        k: v for k, v in plain.items() if k != "unsuitable_for_guests"
    }
    text = json.dumps(with_guest)
    assert anna not in text
    assert "vegetarian" not in json.dumps(with_guest["warnings"])


async def test_opted_out_guest_counts_as_having_no_restrictions(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    ids = await _recipes(cook)
    ben = await _guest(
        make_user, client, "ben", {"kind": "allergy", "allergen": "milk"}, opt_in=False
    )
    plain = (await cook.get(f"{WEB}/recipes")).json()
    with_ben = (await cook.get(f"{WEB}/recipes", params={"guests": ben})).json()
    # Indistinguishable from a guest without restrictions.
    assert with_ben == plain
    assert all(r["unsuitable_for_guests"] is False for r in with_ben["items"])
    hidden = (
        await cook.get(f"{WEB}/recipes", params={"guests": ben, "hide_unsuitable_for_guests": True})
    ).json()
    assert hidden["total"] == 3
    assert ids["veggie"] in _by_id(hidden)


async def test_own_restrictions_still_warn_with_guests(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    ids = await _recipes(cook)
    anna = await _guest(
        make_user, client, "anna", {"kind": "diet", "diet": "vegetarian"}, opt_in=True
    )
    await grant_health_data(cook)
    await cook.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "allergy", "allergen": "milk"},
    )
    detail = (await cook.get(f"{WEB}/recipes/{ids['veggie']}", params={"guests": anna})).json()
    assert detail["has_warning"] is True
    assert detail["warnings"][0]["allergen"] == "milk"
    assert detail["unsuitable_for_guests"] is False


async def test_guests_must_be_active_people_and_opt_in_stays_private(
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    await _recipes(cook)
    unknown = await cook.get(
        f"{WEB}/recipes", params={"guests": "00000000-0000-0000-0000-000000000000"}
    )
    assert unknown.status_code == 404
    anna = await _guest(
        make_user, client, "anna", {"kind": "diet", "diet": "vegetarian"}, opt_in=True
    )
    await login_system(client)
    deactivated = await client.patch(f"{WEB}/users/{anna}", headers=CSRF, json={"is_active": False})
    assert deactivated.status_code == 200, deactivated.text
    assert "share_restrictions_with_hosts" not in deactivated.json()
    inactive = await cook.get(f"{WEB}/recipes", params={"guests": anna})
    assert inactive.status_code == 404
    directory = (await cook.get(f"{WEB}/users/directory")).json()
    assert all("share_restrictions_with_hosts" not in u for u in directory)


async def test_agent_sets_diet_markers(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    from tests.integration.test_mcp import _cook_token
    from tests.integration.test_mcp import call

    token = await _cook_token(make_user, client)
    result = await call(
        client,
        token,
        "create_ingredient",
        {
            "original_locale": "en-GB",
            "names": {"en-GB": {"name": "gelatine"}},
            "diet_markers": ["gelatin"],
        },
    )
    assert result["isError"] is False, result
    ingredient = (await client.get(f"{WEB}/ingredients/{result['structuredContent']['id']}")).json()
    assert ingredient["diet_markers"] == ["gelatin"]
