"""Shared shopping lists: access, merging items, recipes and live updates."""

import httpx

from src.cookbook.adapters.outbound.external.live_updates import InMemoryLivePublisher
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id


async def test_lists_are_private_until_shared(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    friend = await make_user("friend")
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    await login(client, "friend@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/shopping-lists/{created['id']}")).status_code == 404

    shared = await cook.put(
        f"{WEB}/shopping-lists/{created['id']}", headers=CSRF, json={"member_ids": [friend["id"]]}
    )
    assert [m["display_name"] for m in shared.json()["members"]] == ["Friend"]
    mine = (await client.get(f"{WEB}/shopping-lists")).json()
    assert mine[0]["is_owner"] is False
    refused = await client.put(
        f"{WEB}/shopping-lists/{created['id']}", headers=CSRF, json={"member_ids": []}
    )
    assert refused.status_code == 403
    assert (
        await client.delete(f"{WEB}/shopping-lists/{created['id']}", headers=CSRF)
    ).status_code == 403
    assert (
        await client.post(f"{WEB}/shopping-lists/{created['id']}/leave", headers=CSRF)
    ).status_code == 204
    assert (await client.get(f"{WEB}/shopping-lists")).json() == []


async def test_items_merge_check_and_publish(
    cook: httpx.AsyncClient, live: InMemoryLivePublisher
) -> None:
    flour = await make_ingredient(cook, "Mehl")
    g = await unit_id(cook, "g")
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    url = f"{WEB}/shopping-lists/{created['id']}"
    await cook.post(
        f"{url}/items",
        headers=CSRF,
        json={"ingredient_id": flour["id"], "amount": 200, "unit_id": g},
    )
    merged = await cook.post(
        f"{url}/items",
        headers=CSRF,
        json={"ingredient_id": flour["id"], "amount": 300, "unit_id": g},
    )
    items = merged.json()["items"]
    assert len(items) == 1 and items[0]["amount"] == 500
    assert items[0]["name"] == "Mehl"
    free = (await cook.post(f"{url}/items", headers=CSRF, json={"text": "Servietten"})).json()
    assert {i["name"] for i in free["items"]} == {"Mehl", "Servietten"}

    checked = await cook.patch(
        f"{url}/items/{items[0]['id']}", headers=CSRF, json={"checked": True}
    )
    flour_item = next(i for i in checked.json()["items"] if i["name"] == "Mehl")
    assert flour_item["checked"] is True
    assert flour_item["checked_by"]["display_name"] == "Cook"
    assert (await cook.post(f"{url}/clear-checked", headers=CSRF)).json() == {"removed": 1}

    channels = {channel for channel, _ in live.published}
    assert channels == {f"cuisine:shopping-list:{created['id']}"}
    assert {event["type"] for _, event in live.published} == {"items_changed"}


async def test_deleting_an_item_answers_the_list_and_strangers_get_404(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    url = f"{WEB}/shopping-lists/{created['id']}"
    await cook.post(f"{url}/items", headers=CSRF, json={"text": "Servietten"})
    added = (await cook.post(f"{url}/items", headers=CSRF, json={"text": "Kerzen"})).json()
    candles = next(i for i in added["items"] if i["name"] == "Kerzen")

    await make_user("stranger")
    await login(client, "stranger@example.com", "cook-password-1")
    foreign = await client.delete(f"{url}/items/{candles['id']}", headers=CSRF)
    assert foreign.status_code == 404

    deleted = await cook.delete(f"{url}/items/{candles['id']}", headers=CSRF)
    assert deleted.status_code == 200, deleted.text
    assert [i["name"] for i in deleted.json()["items"]] == ["Servietten"]
    again = await cook.delete(f"{url}/items/{candles['id']}", headers=CSRF)
    assert again.status_code == 404


async def test_free_text_needs_a_text(cook: httpx.AsyncClient) -> None:
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    refused = await cook.post(f"{WEB}/shopping-lists/{created['id']}/items", headers=CSRF, json={})
    assert refused.status_code == 422


async def test_adding_a_recipe_scales_and_merges(cook: httpx.AsyncClient) -> None:
    flour = await make_ingredient(cook, "Mehl")
    g = await unit_id(cook, "g")
    recipe = await make_recipe(
        cook, "Brot", [("Kneten", [{"ingredient_id": flour["id"], "amount": 250, "unit_id": g}])]
    )
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    url = f"{WEB}/shopping-lists/{created['id']}"
    await cook.post(f"{url}/recipes", headers=CSRF, json={"recipe_id": recipe["id"], "servings": 4})
    await cook.post(f"{url}/recipes", headers=CSRF, json={"recipe_id": recipe["id"]})
    items = (await cook.get(url)).json()["items"]
    assert len(items) == 1
    assert items[0]["amount"] == 750
    assert items[0]["recipe"]["title"] == "Brot"


async def test_an_item_lists_every_recipe_it_is_for(cook: httpx.AsyncClient) -> None:
    flour = await make_ingredient(cook, "Mehl")
    g = await unit_id(cook, "g")
    line = {"ingredient_id": flour["id"], "amount": 250, "unit_id": g}
    bread = await make_recipe(cook, "Brot", [("Kneten", [line])])
    pizza = await make_recipe(cook, "Pizza", [("Kneten", [line])])
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    url = f"{WEB}/shopping-lists/{created['id']}"
    for recipe in (bread, pizza, bread):
        await cook.post(f"{url}/recipes", headers=CSRF, json={"recipe_id": recipe["id"]})
    items = (await cook.get(url)).json()["items"]
    assert len(items) == 1 and items[0]["amount"] == 750
    assert items[0]["recipe"]["title"] == "Brot"
    assert [(r["title"], r["accessible"]) for r in items[0]["recipes"]] == [
        ("Brot", True),
        ("Pizza", True),
    ]

    assert (await cook.delete(f"{WEB}/recipes/{bread['id']}", headers=CSRF)).status_code == 204
    left = (await cook.get(url)).json()["items"][0]
    assert left["recipe"] is None
    assert [r["title"] for r in left["recipes"]] == ["Pizza"]


async def test_a_free_item_learns_the_recipe_that_joins_it(cook: httpx.AsyncClient) -> None:
    flour = await make_ingredient(cook, "Mehl")
    g = await unit_id(cook, "g")
    bread = await make_recipe(
        cook, "Brot", [("Kneten", [{"ingredient_id": flour["id"], "amount": 250, "unit_id": g}])]
    )
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    url = f"{WEB}/shopping-lists/{created['id']}"
    await cook.post(
        f"{url}/items",
        headers=CSRF,
        json={"ingredient_id": flour["id"], "amount": 100, "unit_id": g},
    )
    await cook.post(f"{url}/recipes", headers=CSRF, json={"recipe_id": bread["id"]})
    items = (await cook.get(url)).json()["items"]
    assert len(items) == 1 and items[0]["amount"] == 350
    assert [r["title"] for r in items[0]["recipes"]] == ["Brot"]


async def test_events_stream_needs_access(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    created = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Markt"})
    ).json()
    await make_user("stranger")
    await login(client, "stranger@example.com", "cook-password-1")
    refused = await client.get(f"{WEB}/shopping-lists/{created['id']}/events")
    assert refused.status_code == 404
