"""Food restrictions are health data: only their user ever sees them, and
the warnings they cause reach that user only."""

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import grant_health_data
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id


async def _recipe_with_nuts(cook: httpx.AsyncClient) -> tuple[str, str]:
    nuts = await make_ingredient(cook, "Walnüsse", allergens=["nuts"])
    recipe = await make_recipe(
        cook,
        "Nusskuchen",
        [
            (
                "Backen",
                [{"ingredient_id": nuts["id"], "amount": 100, "unit_id": await unit_id(cook, "g")}],
            )
        ],
    )
    return recipe["id"], nuts["id"]


async def test_restrictions_warn_their_owner_only(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe_id, _ = await _recipe_with_nuts(cook)
    await grant_health_data(cook)
    added = await cook.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "allergy", "allergen": "nuts", "note": "schwer"},
    )
    assert added.status_code == 201
    mine = (await cook.get(f"{WEB}/recipes/{recipe_id}")).json()
    assert mine["has_warning"] is True
    assert mine["warnings"][0]["allergen"] == "nuts"
    assert mine["warnings"][0]["ingredient_names"] == ["Walnüsse"]
    listed = (await cook.get(f"{WEB}/recipes")).json()["items"][0]
    assert listed["has_warning"] is True

    await make_user("guest")
    await login(client, "guest@example.com", "cook-password-1")
    theirs = (await client.get(f"{WEB}/recipes/{recipe_id}")).json()
    assert theirs["has_warning"] is False
    assert theirs["warnings"] == []
    assert (await client.get(f"{WEB}/users/me/food-restrictions")).json() == []


async def test_nobody_reads_or_removes_another_users_restrictions(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    await grant_health_data(cook)
    added = (
        await cook.post(
            f"{WEB}/users/me/food-restrictions",
            headers=CSRF,
            json={"kind": "intolerance", "allergen": "milk"},
        )
    ).json()
    assert (await admin.get(f"{WEB}/users/me/food-restrictions")).json() == []
    refused = await admin.delete(f"{WEB}/users/me/food-restrictions/{added['id']}", headers=CSRF)
    assert refused.status_code == 404
    log = (await admin.get(f"{WEB}/security-events")).json()["items"]
    assert all("milk" not in str(e["detail"]) for e in log)


async def test_restriction_names_an_allergen_or_an_ingredient(cook: httpx.AsyncClient) -> None:
    _, nuts_id = await _recipe_with_nuts(cook)
    await grant_health_data(cook)
    both = await cook.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "allergy", "allergen": "nuts", "ingredient_id": nuts_id},
    )
    assert both.status_code == 422
    ingredient = await cook.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "intolerance", "ingredient_id": nuts_id},
    )
    assert ingredient.json()["ingredient_name"] == "Walnüsse"
    removed = await cook.delete(
        f"{WEB}/users/me/food-restrictions/{ingredient.json()['id']}", headers=CSRF
    )
    assert removed.status_code == 204
