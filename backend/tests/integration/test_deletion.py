"""Deleting accounts, recipes, ingredients and resources.

A deleted account leaves no trace in any read path but one anonymous
security event; deleting an ingredient never reveals that food restrictions
name it."""

from datetime import date
from io import BytesIO
from typing import Any

import httpx
import pytest
from PIL import Image

from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import grant_health_data
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id

# Written for user choice, the privacy mode in which owners pick each
# recipe's visibility; a fresh instance runs in instance mode.
pytestmark = pytest.mark.usefixtures("user_choice_privacy")

TODAY = date.today().isoformat()


async def _recipe(client: httpx.AsyncClient, title: str, **extra: Any) -> dict[str, Any]:
    flour = await make_ingredient(client, f"Mehl {title}")
    return await make_recipe(
        client,
        title,
        [
            (
                "Backen",
                [
                    {
                        "ingredient_id": flour["id"],
                        "amount": 100,
                        "unit_id": await unit_id(client, "g"),
                    }
                ],
            )
        ],
        **extra,
    )


def _png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (32, 32), (10, 120, 30)).save(out, format="PNG")
    return out.getvalue()


async def _victim(
    make_user: MakeUser,
    client: httpx.AsyncClient,
    cook: httpx.AsyncClient,
    login_system: LoginSystem,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """A user with a published recipe, a draft, a rating, a note, a
    favourite, a cook event and a food restriction; returns the user, their
    recipe and the cook's recipe they rated."""
    victim = await make_user("victim", permissions=["write:recipes", "write:ingredients"])
    rated = await _recipe(cook, "Fremdes Rezept")
    await login(client, "victim@example.com", "cook-password-1")
    own = await _recipe(client, "Opferrezept")
    await _recipe(client, "Entwurf", publish=False)
    await client.put(f"{WEB}/recipes/{rated['id']}/rating", headers=CSRF, json={"stars": 1})
    await client.put(f"{WEB}/recipes/{rated['id']}/note", headers=CSRF, json={"text": "geheim"})
    await client.put(
        f"{WEB}/recipes/{rated['id']}/favourite", headers=CSRF, json={"favourite": True}
    )
    await client.post(
        f"{WEB}/cook-events",
        headers=CSRF,
        json={"recipe_id": rated["id"], "cooked_on": TODAY, "servings": 2},
    )
    await grant_health_data(client)
    await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "allergy", "allergen": "nuts"},
    )
    await login_system(client)
    return victim, own, rated


async def test_a_deleted_account_leaves_no_trace(
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    victim, own, rated = await _victim(make_user, client, cook, login_system)
    impact = (await client.get(f"{WEB}/users/{victim['id']}/deletion-impact")).json()
    assert impact["recipes"]["instance"] == 1 and impact["drafts"] == 1
    assert impact["backup_keep_days"] == 14
    assert impact["backups_clear_by"] > TODAY

    deleted = await client.delete(
        f"{WEB}/users/{victim['id']}", headers=CSRF, params={"ownerless_visibility": "instance"}
    )
    assert deleted.status_code == 204, deleted.text

    users = (await client.get(f"{WEB}/users")).json()
    assert victim["id"] not in str(users)
    assert "victim" not in str((await client.get(f"{WEB}/users/directory")).json())
    kept = (await cook.get(f"{WEB}/recipes/{own['id']}")).json()
    assert kept["owner"] is None and kept["visibility"] == "instance"
    detail = (await cook.get(f"{WEB}/recipes/{rated['id']}")).json()
    assert detail["rating_count"] == 0
    window = {"date_from": TODAY, "date_to": TODAY}
    assert (await cook.get(f"{WEB}/cook-events", params=window)).json() == []
    assert (await client.get(f"{WEB}/recipes", params={"status": "drafts"})).json()["total"] == 0

    events = (await client.get(f"{WEB}/security-events", params={"limit": 200})).json()["items"]
    text = str(events)
    assert "victim" not in text and victim["id"] not in text
    deletions = [e for e in events if e["event_type"] == "user_deleted"]
    assert len(deletions) == 1
    assert deletions[0]["actor_name"] == "Test Admin"
    assert deletions[0]["target_user_id"] is None and deletions[0]["detail"] == {}


async def test_ownerless_private_recipes_cannot_keep_their_visibility(
    make_user: MakeUser,
    client: httpx.AsyncClient,
    resources: None,
    login_system: LoginSystem,
) -> None:
    victim = await make_user("victim", permissions=["write:recipes", "write:ingredients"])
    await login(client, "victim@example.com", "cook-password-1")
    await _recipe(client, "Privat", visibility="private")
    await login_system(client)
    refused = await client.delete(
        f"{WEB}/users/{victim['id']}", headers=CSRF, params={"ownerless_visibility": "keep"}
    )
    assert refused.status_code == 422
    assert refused.json()["code"] == "AccountDeletionChoiceError"
    assert (await client.get(f"{WEB}/users/{victim['id']}")).status_code == 200


async def test_a_new_owner_takes_over_and_lists_pass_on(
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
    login_system: LoginSystem,
) -> None:
    heir = await make_user("heir")
    victim = await make_user("victim", permissions=["write:recipes", "write:ingredients"])
    await login(client, "victim@example.com", "cook-password-1")
    own = await _recipe(client, "Erbstück", visibility="private")
    shared = (
        await client.post(
            f"{WEB}/shopping-lists",
            headers=CSRF,
            json={"name": "Markt", "member_ids": [heir["id"]]},
        )
    ).json()
    alone = (await client.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Solo"})).json()
    await login_system(client)
    assert (
        await client.delete(
            f"{WEB}/users/{victim['id']}", headers=CSRF, params={"new_owner_id": heir["id"]}
        )
    ).status_code == 204
    await login(client, "heir@example.com", "cook-password-1")
    taken = (await client.get(f"{WEB}/recipes/{own['id']}")).json()
    assert taken["owner"]["display_name"] == "Heir"
    assert taken["visibility"] == "private"
    lists = {entry["id"]: entry for entry in (await client.get(f"{WEB}/shopping-lists")).json()}
    assert lists[shared["id"]]["is_owner"] is True
    assert alone["id"] not in lists


async def test_deleting_a_recipe_frees_plans_and_images(cook: httpx.AsyncClient) -> None:
    image = (
        await cook.post(
            f"{WEB}/files", headers=CSRF, files={"file": ("cover.png", _png(), "image/png")}
        )
    ).json()
    recipe = await _recipe(cook, "Kurzlebig", cover_image_id=image["id"])
    await cook.post(
        f"{WEB}/meal-plan",
        headers=CSRF,
        json={"plan_date": TODAY, "slot": "dinner", "recipe_id": recipe["id"]},
    )
    impact = (await cook.get(f"{WEB}/recipes/{recipe['id']}/deletion-impact")).json()
    assert impact == {"blocked": False, "used_by": [], "used_by_hidden_count": 0}
    assert (await cook.delete(f"{WEB}/recipes/{recipe['id']}", headers=CSRF)).status_code == 204
    entries = (
        await cook.get(f"{WEB}/meal-plan", params={"date_from": TODAY, "date_to": TODAY})
    ).json()
    assert entries[0]["recipe"] is None and entries[0]["title"] == "Kurzlebig"
    assert (await cook.get(f"{WEB}/files/{image['id']}")).status_code == 404


async def test_a_used_sub_recipe_lists_its_parents(cook: httpx.AsyncClient) -> None:
    sub = await _recipe(cook, "Teig")
    parent = await make_recipe(
        cook, "Kuchen", [("Backen", [{"sub_recipe_id": sub["id"], "amount": 1}])]
    )
    impact = (await cook.get(f"{WEB}/recipes/{sub['id']}/deletion-impact")).json()
    assert impact["blocked"] is True
    assert [r["id"] for r in impact["used_by"]] == [parent["id"]]
    assert (await cook.delete(f"{WEB}/recipes/{sub['id']}", headers=CSRF)).status_code == 409


async def test_seeded_ingredients_and_units_stay(admin: httpx.AsyncClient) -> None:
    from src.bootstrap.cookbook_seed import ensure_reference_data

    await ensure_reference_data()
    flour = (await admin.get(f"{WEB}/ingredients", params={"search": "wholemeal"})).json()["items"][
        0
    ]
    impact = (await admin.get(f"{WEB}/ingredients/{flour['id']}/deletion-impact")).json()
    assert impact["seeded"] is True and impact["can_merge"] is False
    assert (await admin.delete(f"{WEB}/ingredients/{flour['id']}", headers=CSRF)).status_code == 409
    gram = await unit_id(admin, "g")
    assert (await admin.get(f"{WEB}/units/{gram}/deletion-impact")).json()["seeded"] is True
    assert (await admin.delete(f"{WEB}/units/{gram}", headers=CSRF)).status_code == 409
    # A deleted seeded tag never comes back.
    tags = (await admin.get(f"{WEB}/tags", params={"locale": "en-GB"})).json()
    party = next(t for t in tags if t["name"] == "Party")
    assert (await admin.delete(f"{WEB}/tags/{party['id']}", headers=CSRF)).status_code == 204
    assert await ensure_reference_data() is False
    names = {t["name"] for t in (await admin.get(f"{WEB}/tags", params={"locale": "en-GB"})).json()}
    assert "Party" not in names


async def test_an_ingredient_in_use_is_merged_instead(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    duplicate = await make_ingredient(cook, "Topfen")
    original = await make_ingredient(cook, "Quark")
    g = await unit_id(cook, "g")
    recipe = await make_recipe(
        cook,
        "Topfenstrudel",
        [("Füllen", [{"ingredient_id": duplicate["id"], "amount": 250, "unit_id": g}])],
    )
    impact = (await cook.get(f"{WEB}/ingredients/{duplicate['id']}/deletion-impact")).json()
    assert impact["recipe_count"] == 1 and impact["recipes"][0]["id"] == recipe["id"]
    assert impact["can_merge"] is False
    assert (
        await cook.delete(f"{WEB}/ingredients/{duplicate['id']}", headers=CSRF)
    ).status_code == 409
    assert (
        await cook.post(
            f"{WEB}/ingredients/{duplicate['id']}/merge",
            headers=CSRF,
            json={"into_id": original["id"]},
        )
    ).status_code == 403
    merged = await admin.post(
        f"{WEB}/ingredients/{duplicate['id']}/merge", headers=CSRF, json={"into_id": original["id"]}
    )
    assert merged.status_code == 200
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    # A weight takes the plural, which the test helper writes as name + "n".
    assert detail["ingredients"][0]["name"] == "Quarkn"
    assert (await cook.get(f"{WEB}/ingredients/{duplicate['id']}")).status_code == 404


async def test_deleting_an_ingredient_never_reveals_restrictions(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    named = await make_ingredient(cook, "Kiwi")
    plain = await make_ingredient(cook, "Mango")
    await make_user("allergic")
    await login(client, "allergic@example.com", "cook-password-1")
    await grant_health_data(client)
    await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "allergy", "ingredient_id": named["id"]},
    )
    shopping = (
        await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Obst"})
    ).json()
    await cook.post(
        f"{WEB}/shopping-lists/{shopping['id']}/items",
        headers=CSRF,
        json={"ingredient_id": named["id"]},
    )

    impacts = [
        (await cook.get(f"{WEB}/ingredients/{i['id']}/deletion-impact")).json()
        for i in (named, plain)
    ]
    assert impacts[0] == impacts[1]
    answers = [
        await cook.delete(f"{WEB}/ingredients/{i['id']}", headers=CSRF) for i in (named, plain)
    ]
    assert [a.status_code for a in answers] == [204, 204]
    assert answers[0].content == answers[1].content
    for ingredient in (named, plain):
        assert (await cook.get(f"{WEB}/ingredients/{ingredient['id']}")).status_code == 404
    assert (await cook.get(f"{WEB}/ingredients", params={"search": "kiwi"})).json()["total"] == 0
    item = (await cook.get(f"{WEB}/shopping-lists/{shopping['id']}")).json()["items"][0]
    assert item["ingredient_id"] is None and item["name"] == "Kiwi"
    # The restriction stays for its user, who keeps seeing what it names.
    own = (await client.get(f"{WEB}/users/me/food-restrictions")).json()
    assert own[0]["ingredient_name"] == "Kiwi"


async def test_custom_units_merge_and_categories_take_a_replacement(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    fistful = (
        await admin.post(
            f"{WEB}/units",
            headers=CSRF,
            json={
                "code": "fistful",
                "kind": "count",
                "translations": {"de-AT": {"name": "Faustvoll"}},
            },
        )
    ).json()
    nuts = await make_ingredient(cook, "Nüsse")
    recipe = await make_recipe(
        cook,
        "Müsli",
        [("Mischen", [{"ingredient_id": nuts["id"], "amount": 1, "unit_id": fistful["id"]}])],
    )
    assert (await admin.delete(f"{WEB}/units/{fistful['id']}", headers=CSRF)).status_code == 409
    piece = await unit_id(admin, "piece")
    assert (
        await admin.post(
            f"{WEB}/units/{fistful['id']}/merge", headers=CSRF, json={"into_id": piece}
        )
    ).status_code == 200
    line = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()["ingredients"][0]
    assert line["unit"]["code"] == "piece"

    categories = (
        await admin.get(f"{WEB}/ingredient-categories", params={"locale": "en-GB"})
    ).json()
    fruit = next(c for c in categories if c["name"] == "Fruit")
    vegetables = next(c for c in categories if c["name"] == "Vegetables")
    apple = (
        await cook.post(
            f"{WEB}/ingredients",
            headers=CSRF,
            json={
                "original_locale": "de-AT",
                "translations": {"de-AT": {"name": "Apfel"}},
                "category_id": fruit["id"],
            },
        )
    ).json()
    assert (
        await admin.delete(
            f"{WEB}/ingredient-categories/{fruit['id']}",
            headers=CSRF,
            params={"replacement_id": vegetables["id"]},
        )
    ).status_code == 204
    moved = (await cook.get(f"{WEB}/ingredients/{apple['id']}", params={"locale": "en-GB"})).json()
    assert moved["category"]["name"] == "Vegetables"
