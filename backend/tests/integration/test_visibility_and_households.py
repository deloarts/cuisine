"""Recipe visibility and households.

A private recipe stays private for administrators and managers too, in every
read path; shared recipes reach the chosen users and group members;
narrowing a recipe hides it from others while keeping their own data."""

from datetime import date
from datetime import timedelta
from typing import Any

import httpx
import pytest

from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id

# Written for user choice, the privacy mode in which owners pick each
# recipe's visibility; a fresh instance runs in instance mode.
pytestmark = pytest.mark.usefixtures("user_choice_privacy")

TODAY = date.today()


async def _recipe(cook: httpx.AsyncClient, title: str, **extra: Any) -> dict[str, Any]:
    flour = await make_ingredient(cook, f"Mehl {title}")
    g = await unit_id(cook, "g")
    return await make_recipe(
        cook,
        title,
        [("Backen", [{"ingredient_id": flour["id"], "amount": 100, "unit_id": g}])],
        **extra,
    )


async def _set_visibility(
    cook: httpx.AsyncClient, recipe_id: str, visibility: str, **shares: list[str]
) -> dict[str, Any]:
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
                        "amount": i["amount"],
                        "unit_id": i["unit_id"],
                    }
                    for i in s["ingredients"]
                ],
            }
            for s in edit["steps"]
        ],
        "visibility": visibility,
        **shares,
    }
    saved = await cook.put(f"{WEB}/recipes/{recipe_id}", headers=CSRF, json=body)
    assert saved.status_code == 200, saved.text
    result: dict[str, Any] = saved.json()
    return result


async def test_private_recipes_are_private_for_admins_everywhere(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    recipe = await _recipe(cook, "Geheimrezept", visibility="private")
    assert recipe["visibility"] == "private"
    rid = recipe["id"]
    await cook.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={"recipe_id": rid, "cooked_on": TODAY.isoformat(), "servings": 2},
    )
    assert (await cook.get(f"{WEB}/recipes/{rid}")).status_code == 200

    # The admin is the system user and holds manage:recipes.
    assert (await admin.get(f"{WEB}/recipes/{rid}")).status_code == 404
    assert (await admin.get(f"{WEB}/recipes/{rid}/edit")).status_code == 404
    assert (await admin.delete(f"{WEB}/recipes/{rid}", headers=CSRF)).status_code == 404
    assert (await admin.get(f"{WEB}/recipes")).json()["total"] == 0
    assert (await admin.get(f"{WEB}/recipes", params={"search": "geheim"})).json()["total"] == 0
    home = (await admin.get(f"{WEB}/home")).json()
    assert home["newest"] == [] and home["recently_cooked"] == []
    window = {"date_from": (TODAY - timedelta(days=1)).isoformat(), "date_to": TODAY.isoformat()}
    assert (await admin.get(f"{WEB}/cook-events", params=window)).json() == []
    assert (
        await admin.get(f"{WEB}/cook-events", params={**window, "recipe_id": rid})
    ).status_code == 404
    assert (
        await admin.put(f"{WEB}/recipes/{rid}/favourite", headers=CSRF, json={"favourite": True})
    ).status_code == 404
    assert (
        await admin.post(
            f"{WEB}/meal-plan",
            headers=CSRF,
            json={"plan_date": TODAY.isoformat(), "slot": "dinner", "recipe_id": rid},
        )
    ).status_code == 404
    listed = (await admin.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "x"})).json()
    assert (
        await admin.post(
            f"{WEB}/shopping-lists/{listed['id']}/recipes", headers=CSRF, json={"recipe_id": rid}
        )
    ).status_code == 404


async def test_shared_with_users_and_groups(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    friend = await make_user("friend")
    relative = await make_user("relative")
    group = (
        await admin.post(
            f"{WEB}/groups",
            headers=CSRF,
            json={"name": "Family", "permissions": [], "member_ids": [relative["id"]]},
        )
    ).json()
    recipe = await _recipe(cook, "Omas Torte")
    saved = await _set_visibility(
        cook, recipe["id"], "shared", shared_user_ids=[friend["id"]], shared_group_ids=[group["id"]]
    )
    assert saved["shared_user_ids"] == [friend["id"]]
    assert saved["shared_group_ids"] == [group["id"]]
    for name, expected in (("friend", 200), ("relative", 200)):
        await login(client, f"{name}@example.com", "cook-password-1")
        assert (await client.get(f"{WEB}/recipes/{recipe['id']}")).status_code == expected
        assert (await client.get(f"{WEB}/recipes")).json()["total"] == 1
    await login_system(client)
    await make_user("stranger")
    await login(client, "stranger@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/recipes/{recipe['id']}")).status_code == 404


async def test_narrowing_hides_the_recipe_but_keeps_others_data(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    recipe = await _recipe(cook, "Gulasch")
    rid = recipe["id"]
    await make_user("guest")
    await login(client, "guest@example.com", "cook-password-1")
    await client.put(f"{WEB}/recipes/{rid}/favourite", headers=CSRF, json={"favourite": True})
    await client.put(f"{WEB}/recipes/{rid}/note", headers=CSRF, json={"text": "scharf"})
    await client.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={"recipe_id": rid, "cooked_on": TODAY.isoformat(), "servings": 2},
    )

    await _set_visibility(cook, rid, "private")
    window = {"date_from": TODAY.isoformat(), "date_to": TODAY.isoformat()}
    assert (await client.get(f"{WEB}/cook-events", params=window)).json() == []
    assert (await client.get(f"{WEB}/recipes", params={"favourites": True})).json()["total"] == 0
    assert (await client.get(f"{WEB}/recipes", params={"search": "gulasch"})).json()["total"] == 0
    assert (await client.get(f"{WEB}/home")).json()["recently_cooked"] == []
    # The owner still sees the guest's cook event of their own recipe.
    assert len((await cook.get(f"{WEB}/cook-events", params=window)).json()) == 1

    await _set_visibility(cook, rid, "instance")
    back = (await client.get(f"{WEB}/recipes/{rid}")).json()
    assert back["is_favourite"] is True
    assert back["own_note"] == "scharf"
    assert len((await client.get(f"{WEB}/cook-events", params=window)).json()) == 1


async def test_locked_privacy_forces_the_default(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    saved = await admin.put(
        f"{WEB}/settings/privacy",
        headers=CSRF,
        json={"default_recipe_visibility": "private", "users_may_change_visibility": False},
    )
    assert saved.status_code == 200
    assert (await cook.get(f"{WEB}/settings/privacy")).json()[
        "users_may_change_visibility"
    ] is False
    recipe = await _recipe(cook, "Suppe", visibility="instance")
    assert recipe["visibility"] == "private"
    assert recipe["can_change_visibility"] is False


async def test_own_default_visibility(cook: httpx.AsyncClient) -> None:
    profile = await cook.patch(
        f"{WEB}/users/me", headers=CSRF, json={"default_recipe_visibility": "household"}
    )
    assert profile.json()["default_recipe_visibility"] == "household"
    recipe = await _recipe(cook, "Salat")
    assert recipe["visibility"] == "household"


async def _household_of_two(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> tuple[dict[str, Any], dict[str, Any]]:
    partner = await make_user("partner")
    household = (
        await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "Zuhause"})
    ).json()
    invitation = (
        await cook.post(
            f"{WEB}/households/mine/invitations", headers=CSRF, json={"user_id": partner["id"]}
        )
    ).json()
    await login(client, "partner@example.com", "cook-password-1")
    received = (await client.get(f"{WEB}/households/invitations")).json()
    assert received[0]["household"]["name"] == "Zuhause"
    joined = await client.post(
        f"{WEB}/households/invitations/{invitation['id']}/accept", headers=CSRF
    )
    assert joined.status_code == 200, joined.text
    assert len(joined.json()["members"]) == 2
    return household, partner


async def test_household_shares_plan_list_and_household_recipes(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    household, _ = await _household_of_two(cook, make_user, client)
    recipe = await _recipe(cook, "Familienessen", visibility="household")
    assert (await client.get(f"{WEB}/recipes/{recipe['id']}")).status_code == 200

    added = await client.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": TODAY.isoformat(), "slot": "dinner", "recipe_id": recipe["id"]},
    )
    assert added.status_code == 201, added.text
    window = {"date_from": TODAY.isoformat(), "date_to": TODAY.isoformat()}
    assert len((await cook.get(f"{WEB}/meal-plan", params=window)).json()) == 1

    lists = (await client.get(f"{WEB}/shopping-lists")).json()
    assert [entry["id"] for entry in lists] == [household["shopping_list_id"]]
    shared_list = household["shopping_list_id"]
    assert (
        await client.delete(f"{WEB}/shopping-lists/{shared_list}", headers=CSRF)
    ).status_code == 422

    # The partner leaves: plan and list stay with the household.
    assert (await client.post(f"{WEB}/households/mine/leave", headers=CSRF)).status_code == 204
    assert (await client.get(f"{WEB}/meal-plan", params=window)).json() == []
    assert (await client.get(f"{WEB}/shopping-lists")).json() == []
    assert (await client.get(f"{WEB}/recipes/{recipe['id']}")).status_code == 404
    assert len((await cook.get(f"{WEB}/meal-plan", params=window)).json()) == 1

    # The last member leaving dissolves it.
    assert (await cook.post(f"{WEB}/households/mine/leave", headers=CSRF)).status_code == 204
    assert (await cook.get(f"{WEB}/households/mine")).json() == {"household": None}
    assert (await cook.get(f"{WEB}/shopping-lists")).json() == []


async def test_members_switch_between_household_and_personal_plan(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    window = {"date_from": TODAY.isoformat(), "date_to": TODAY.isoformat()}
    # Planned before joining: personal, and still reachable as a member.
    before = await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": TODAY.isoformat(), "slot": "lunch", "title": "Vorher"},
    )
    assert before.json()["scope"] == "personal"
    assert (
        await cook.get(f"{WEB}/meal-plan", params={**window, "scope": "household"})
    ).status_code == 422

    await _household_of_two(cook, make_user, client)
    shared = await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": TODAY.isoformat(), "slot": "dinner", "title": "Gemeinsam"},
    )
    assert shared.json()["scope"] == "household"
    mine = await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={
            "plan_date": TODAY.isoformat(),
            "slot": "snack",
            "title": "Nur ich",
            "scope": "personal",
        },
    )
    assert mine.status_code == 201, mine.text
    assert mine.json()["scope"] == "personal"

    def titles(response: httpx.Response) -> set[str]:
        return {e["title"] for e in response.json()}

    assert titles(await cook.get(f"{WEB}/meal-plan", params=window)) == {"Gemeinsam"}
    personal = await cook.get(f"{WEB}/meal-plan", params={**window, "scope": "personal"})
    assert titles(personal) == {"Vorher", "Nur ich"}
    # The partner sees the household plan, never someone else's personal one.
    assert titles(await client.get(f"{WEB}/meal-plan", params=window)) == {"Gemeinsam"}
    assert (
        await client.get(f"{WEB}/meal-plan", params={**window, "scope": "personal"})
    ).json() == []
    assert (
        await client.delete(f"{WEB}/meal-plan/{mine.json()['id']}", headers=CSRF)
    ).status_code == 404

    # A personal entry is changed and deleted without naming its plan, and
    # an update keeps it in that plan.
    changed = await cook.put(
        f"{WEB}/meal-plan/{before.json()['id']}",
        headers=CSRF,
        json={"plan_date": TODAY.isoformat(), "slot": "lunch", "title": "Geändert"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["scope"] == "personal"
    assert (
        await cook.delete(f"{WEB}/meal-plan/{mine.json()['id']}", headers=CSRF)
    ).status_code == 204


async def test_one_household_per_user_and_declining(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    other = await make_user("other")
    await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "A"})
    assert (
        await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "B"})
    ).status_code == 409
    invitation = (
        await cook.post(
            f"{WEB}/households/mine/invitations", headers=CSRF, json={"user_id": other["id"]}
        )
    ).json()
    await login(client, "other@example.com", "cook-password-1")
    assert (
        await client.post(f"{WEB}/households/invitations/{invitation['id']}/decline", headers=CSRF)
    ).status_code == 204
    assert (await client.get(f"{WEB}/households/invitations")).json() == []
    assert (await client.get(f"{WEB}/households/mine")).json() == {"household": None}


async def test_admins_see_membership_not_plans(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    await _household_of_two(cook, make_user, client)
    await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": TODAY.isoformat(), "slot": "lunch", "title": "Reste"},
    )
    await login_system(admin)
    overview = (await admin.get(f"{WEB}/admin/households")).json()
    assert overview[0]["name"] == "Zuhause"
    assert len(overview[0]["members"]) == 2
    window = {"date_from": TODAY.isoformat(), "date_to": TODAY.isoformat()}
    assert (await admin.get(f"{WEB}/meal-plan", params=window)).json() == []
    assert (await cook.get(f"{WEB}/admin/households")).status_code == 403


async def test_shopping_items_lose_the_link_to_a_hidden_recipe(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    friend = await make_user("friend")
    recipe = await _recipe(cook, "Kuchen")
    shared = (
        await cook.post(
            f"{WEB}/shopping-lists",
            headers=CSRF,
            json={"name": "Markt", "member_ids": [friend["id"]]},
        )
    ).json()
    await cook.post(
        f"{WEB}/shopping-lists/{shared['id']}/recipes",
        headers=CSRF,
        json={"recipe_id": recipe["id"]},
    )
    await _set_visibility(cook, recipe["id"], "private")
    await login(client, "friend@example.com", "cook-password-1")
    items = (await client.get(f"{WEB}/shopping-lists/{shared['id']}")).json()["items"]
    assert items[0]["recipe"] is None
    assert items[0]["name"].startswith("Mehl")
    mine = (await cook.get(f"{WEB}/shopping-lists/{shared['id']}")).json()["items"]
    assert mine[0]["recipe"]["title"] == "Kuchen"


async def test_each_hidden_source_recipe_is_a_placeholder(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    friend = await make_user("friend")
    flour = await make_ingredient(cook, "Mehl")
    g = await unit_id(cook, "g")
    line = {"ingredient_id": flour["id"], "amount": 100, "unit_id": g}
    open_recipe = await make_recipe(cook, "Brot", [("Backen", [line])])
    hidden = await make_recipe(cook, "Kuchen", [("Backen", [line])])
    shared = (
        await cook.post(
            f"{WEB}/shopping-lists",
            headers=CSRF,
            json={"name": "Markt", "member_ids": [friend["id"]]},
        )
    ).json()
    for recipe in (hidden, open_recipe):
        await cook.post(
            f"{WEB}/shopping-lists/{shared['id']}/recipes",
            headers=CSRF,
            json={"recipe_id": recipe["id"]},
        )
    await _set_visibility(cook, hidden["id"], "private")
    await login(client, "friend@example.com", "cook-password-1")
    item = (await client.get(f"{WEB}/shopping-lists/{shared['id']}")).json()["items"][0]
    assert item["recipe"] is None
    assert [(r["id"], r["title"], r["accessible"]) for r in item["recipes"]] == [
        (None, None, False),
        (open_recipe["id"], "Brot", True),
    ]
    mine = (await cook.get(f"{WEB}/shopping-lists/{shared['id']}")).json()["items"][0]
    assert [r["title"] for r in mine["recipes"]] == ["Kuchen", "Brot"]


async def test_agents_do_not_see_private_recipes(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    from tests.integration.test_mcp import _token
    from tests.integration.test_mcp import call

    recipe = await _recipe(cook, "Geheim", visibility="private")
    token = await _token(admin, ["use:mcp", "write:recipes"])
    found = await call(admin, token, "search_recipes", {"query": "geheim"})
    assert found["structuredContent"]["total"] == 0
    read = await call(admin, token, "get_recipe", {"recipe_id": recipe["id"]})
    assert read["isError"] is True
