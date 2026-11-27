"""The nickname on the own profile: it is shown to others instead of the full
name only while the user chose to go by it, and an empty nickname falls back
to the full name."""

from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_recipe


async def _names_seen_by_admin(admin: httpx.AsyncClient, recipe_id: str) -> tuple[str, str]:
    """The cook's name on the recipe and in the people directory."""
    owner = (await admin.get(f"{WEB}/recipes/{recipe_id}")).json()["owner"]
    directory = (await admin.get(f"{WEB}/users/directory")).json()
    listed = next(u for u in directory if u["id"] == owner["id"])
    return owner["display_name"], listed["display_name"]


async def test_a_new_account_shows_its_full_name(cook: httpx.AsyncClient) -> None:
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert (me["nickname"], me["show_nickname"], me["display_name"]) == (None, False, "Cook")


async def test_others_see_the_nickname_only_when_chosen(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    recipe: dict[str, Any] = await make_recipe(cook, "Gulasch", [("Schmoren.", [])])

    saved = await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"nickname": "  Bubu  "})
    assert saved.status_code == 200, saved.text
    assert (saved.json()["nickname"], saved.json()["display_name"]) == ("Bubu", "Cook")
    assert await _names_seen_by_admin(admin, recipe["id"]) == ("Cook", "Cook")

    await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"show_nickname": True})
    assert await _names_seen_by_admin(admin, recipe["id"]) == ("Bubu", "Bubu")
    # The full name stays on the own profile, where the user can still edit it.
    me = (await cook.get(f"{WEB}/users/me")).json()
    assert (me["full_name"], me["display_name"]) == ("Cook", "Bubu")


async def test_an_empty_nickname_falls_back_to_the_full_name(cook: httpx.AsyncClient) -> None:
    await cook.patch(
        f"{WEB}/users/me", headers=CSRF, json={"nickname": "Bubu", "show_nickname": True}
    )
    cleared = await cook.patch(f"{WEB}/users/me", headers=CSRF, json={"nickname": " "})
    assert cleared.status_code == 200, cleared.text
    body = cleared.json()
    assert (body["nickname"], body["show_nickname"], body["display_name"]) == (None, True, "Cook")
