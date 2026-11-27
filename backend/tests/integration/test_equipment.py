"""The equipment catalogue, step equipment and "You'll need", equipment
mentions, deletion and merging, the kitchen and the agent's step equipment."""

from typing import Any

import httpx

from src.bootstrap.cookbook_seed import ensure_reference_data
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.test_mcp import call
from tests.integration.test_nutrients_and_seasons import agent_token
from tests.integration.test_visibility_and_households import _household_of_two


async def _item(
    admin: httpx.AsyncClient,
    name: str,
    *,
    english: str | None = None,
    kind: str = "utensil",
    aliases: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    translations = {"de-AT": {"name": name}}
    if english:
        translations["en-GB"] = {"name": english}
    response = await admin.post(
        f"{WEB}/equipment",
        headers=CSRF,
        json={"kind": kind, "translations": translations, "aliases": aliases or {}},
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _uses(item: dict[str, Any], count: int | None = None, note: str = "") -> dict[str, Any]:
    used: dict[str, Any] = {"equipment_id": item["id"], "count": count}
    if note:
        used["notes"] = {"de-AT": {"note": note}}
    return used


async def _recipe_with_equipment(
    client: httpx.AsyncClient,
    title: str,
    steps: list[tuple[str, list[dict[str, Any]]]],
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "original_locale": "de-AT",
        "translations": {"de-AT": {"title": title}},
        "base_servings": 2,
        "steps": [
            {"translations": {"de-AT": {"text": text}}, "equipment": equipment}
            for text, equipment in steps
        ],
        **extra,
    }
    created = await client.post(f"{WEB}/recipes", headers=CSRF, json=payload)
    assert created.status_code == 201, created.text
    published = await client.post(f"{WEB}/recipes/{created.json()['id']}/publish", headers=CSRF)
    assert published.status_code == 200, published.text
    body: dict[str, Any] = published.json()
    return body


async def test_catalogue_crud_and_shared_namespace(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    whisk = await _item(admin, "Schneebesen", english="whisk", aliases={"de-AT": ["Schneerute"]})
    assert whisk["status"] == "active"
    assert whisk["seeded"] is False
    listed = (await cook.get(f"{WEB}/equipment", params={"search": "schneerute"})).json()
    assert [e["id"] for e in listed] == [whisk["id"]]
    refused = await cook.post(
        f"{WEB}/equipment",
        headers=CSRF,
        json={"kind": "utensil", "translations": {"de-AT": {"name": "Sieb"}}},
    )
    assert refused.status_code == 403
    # One namespace with ingredients: neither may take the other's name.
    await make_ingredient(cook, "Mohn")
    taken = await admin.post(
        f"{WEB}/equipment",
        headers=CSRF,
        json={"kind": "utensil", "translations": {"de-AT": {"name": "mohn"}}},
    )
    assert taken.status_code == 409
    assert taken.json()["existing_name"] == "Mohn"
    clash = await cook.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={"original_locale": "de-AT", "translations": {"de-AT": {"name": "Schneerute"}}},
    )
    assert clash.status_code == 409
    near = (await cook.get(f"{WEB}/equipment/duplicates", params={"name": "Schneebesn"})).json()
    assert near[0]["id"] == whisk["id"]
    assert near[0]["exact"] is False
    updated = await admin.put(
        f"{WEB}/equipment/{whisk['id']}",
        headers=CSRF,
        json={
            "kind": "utensil",
            "translations": {"de-AT": {"name": "Schneebesen"}},
            "icon": "mdi-whisk",
            "basic": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["icon"] == "whisk"
    assert updated.json()["basic"] is True


async def test_you_will_need_takes_the_highest_count_and_marks_sub_recipes(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    bowl = await _item(admin, "Schüssel", kind="cookware")
    pan = await _item(admin, "Pfanne", kind="cookware")
    oven = await _item(admin, "Backrohr", kind="appliance")
    sauce = await _recipe_with_equipment(
        cook, "Soße", [("Rühren.", [_uses(bowl, 1)]), ("Köcheln.", [_uses(pan)])]
    )
    recipe = await _recipe_with_equipment(
        cook,
        "Auflauf",
        [
            ("Mischen.", [_uses(bowl, 2)]),
            ("Nochmal mischen.", [_uses(bowl, 1)]),
            ("Backen.", [_uses(oven, note="200 °C Umluft")]),
        ],
    )
    # Link the sauce as a sub-recipe of the bake.
    edit = (await cook.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    steps = [
        {
            "translations": s["translations"],
            "equipment": [
                {"equipment_id": e["equipment_id"], "count": e["count"], "notes": e["notes"]}
                for e in s["equipment"]
            ],
            "ingredients": [],
        }
        for s in edit["steps"]
    ]
    steps[0]["ingredients"] = [{"sub_recipe_id": sauce["id"], "amount": 2}]
    saved = await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": edit["translations"],
            "base_servings": 2,
            "steps": steps,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["steps"][2]["equipment"][0]["notes"]["de-AT"]["note"] == "200 °C Umluft"

    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    need = [(n["equipment"]["name"], n["count"], n["sub_recipe"]) for n in detail["equipment"]]
    assert need[0] == ("Schüssel", 2, None)
    assert need[1] == ("Backrohr", None, None)
    from_sauce = [(n[0], n[1], n[2]["title"]) for n in need[2:]]
    assert from_sauce == [("Schüssel", 1, "Soße"), ("Pfanne", None, "Soße")]
    assert all(n["missing"] is None for n in detail["equipment"])
    assert detail["steps"][2]["equipment"][0]["note"] == "200 °C Umluft"
    assert detail["missing_equipment"] is None
    assert detail["kitchen_ready"] is None


async def test_equipment_mentions_must_point_at_the_steps_items(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    sieve = await _item(admin, "Sieb")
    token = f"@[Sieb](equipment:{sieve['id']})"
    base: dict[str, Any] = {
        "original_locale": "de-AT",
        "translations": {"de-AT": {"title": "Nudeln"}},
    }
    wrong = await cook.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json={
            **base,
            "steps": [
                {"translations": {"de-AT": {"text": "Kochen."}}, "equipment": [_uses(sieve)]},
                {"translations": {"de-AT": {"text": f"Abseihen im {token}."}}},
            ],
        },
    )
    assert wrong.status_code == 422
    body = wrong.json()
    assert body["step"] == 2
    assert body["locale"] == "de-AT"
    assert body["mention_kind"] == "equipment"
    assert body["mention_id"] == sieve["id"]
    right = await cook.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"title": "Nudeln", "description": f"Mit {token}."}},
            "steps": [
                {
                    "translations": {"de-AT": {"text": f"Abseihen im {token}."}},
                    "equipment": [_uses(sieve)],
                }
            ],
        },
    )
    assert right.status_code == 201, right.text
    summary = (await cook.get(f"{WEB}/recipes", params={"status": "drafts"})).json()["items"][0]
    assert summary["description_text"] == "Mit Sieb."


async def test_deletion_is_blocked_in_use_merge_moves_steps_and_seeded_items_stay(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    await ensure_reference_data(ingredients=False, equipment=True)
    seeded = next(
        e for e in (await admin.get(f"{WEB}/equipment")).json() if e["seeded"] and e["basic"]
    )
    assert (await admin.delete(f"{WEB}/equipment/{seeded['id']}", headers=CSRF)).status_code == 409
    rolling = await _item(admin, "Nudelholz zwei")
    recipe = await _recipe_with_equipment(cook, "Strudel", [("Ausrollen.", [_uses(rolling)])])
    impact = (await admin.get(f"{WEB}/equipment/{rolling['id']}/deletion-impact")).json()
    assert impact["recipe_count"] == 1
    assert impact["recipes"][0]["id"] == recipe["id"]
    assert impact["can_merge"] is True
    blocked = await admin.delete(f"{WEB}/equipment/{rolling['id']}", headers=CSRF)
    assert blocked.status_code == 409
    merged = await admin.post(
        f"{WEB}/equipment/{rolling['id']}/merge", headers=CSRF, json={"into_id": seeded["id"]}
    )
    assert merged.status_code == 200, merged.text
    assert "Nudelholz zwei" in merged.json()["aliases"]["de-AT"]
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    assert detail["equipment"][0]["equipment"]["id"] == seeded["id"]
    unused = await _item(admin, "Eierschneider")
    assert (await admin.delete(f"{WEB}/equipment/{unused['id']}", headers=CSRF)).status_code == 204


async def test_kitchen_flags_missing_equipment_only_after_set_up(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
) -> None:
    await ensure_reference_data(ingredients=False, equipment=True)
    await make_user("stranger")
    catalogue = (await cook.get(f"{WEB}/equipment")).json()
    basic = [e for e in catalogue if e["basic"]]
    special = next(e for e in catalogue if not e["basic"])
    everyday = await _recipe_with_equipment(cook, "Eierspeis", [("Braten.", [_uses(basic[0])])])
    fancy = await _recipe_with_equipment(cook, "Soufflé", [("Schlagen.", [_uses(special)])])

    before = (await cook.get(f"{WEB}/kitchen")).json()
    assert before == {"set_up": False, "household": False, "equipment": [], "changed": None}
    listed = (await cook.get(f"{WEB}/recipes", params={"only_kitchen_ready": "true"})).json()
    assert listed["total"] == 2
    assert all(r["missing_equipment"] is None for r in listed["items"])
    not_yet = await cook.put(f"{WEB}/kitchen", headers=CSRF, json={"equipment_ids": []})
    assert not_yet.status_code == 422

    kitchen = (await cook.post(f"{WEB}/kitchen/setup", headers=CSRF, json={})).json()
    assert kitchen["set_up"] is True
    assert {e["id"] for e in kitchen["equipment"]} == {e["id"] for e in basic}
    ready = (await cook.get(f"{WEB}/recipes", params={"only_kitchen_ready": "true"})).json()
    assert [r["id"] for r in ready["items"]] == [everyday["id"]]
    assert ready["items"][0]["kitchen_ready"] is True
    detail = (await cook.get(f"{WEB}/recipes/{fancy['id']}")).json()
    assert detail["kitchen_ready"] is False
    assert [e["id"] for e in detail["missing_equipment"]] == [special["id"]]
    assert detail["equipment"][0]["missing"] is True

    # The household shares one kitchen: a new member sees and edits it.
    _, _partner = await _household_of_two(cook, make_user, client)
    shared = (await client.get(f"{WEB}/kitchen")).json()
    assert shared["set_up"] is False
    joined = (
        await client.post(
            f"{WEB}/kitchen/setup", headers=CSRF, json={"equipment_ids": [special["id"]]}
        )
    ).json()
    assert joined["household"] is True
    seen_by_cook = (await cook.get(f"{WEB}/kitchen")).json()
    assert seen_by_cook["household"] is True
    assert [e["id"] for e in seen_by_cook["equipment"]] == [special["id"]]
    fancy_now = (await cook.get(f"{WEB}/recipes/{fancy['id']}")).json()
    assert fancy_now["kitchen_ready"] is True

    # Another user's kitchen is untouched by all this.
    await login(client, "stranger@example.com", "cook-password-1")
    assert (await client.get(f"{WEB}/kitchen")).json()["set_up"] is False
    stranger_view = (await client.get(f"{WEB}/recipes/{fancy['id']}")).json()
    assert stranger_view["missing_equipment"] is None

    reset = await cook.delete(f"{WEB}/kitchen", headers=CSRF)
    assert reset.status_code == 204
    assert (await cook.get(f"{WEB}/kitchen")).json()["set_up"] is False


async def test_agent_names_step_equipment_and_creates_drafts(
    make_user: MakeUser, client: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    whisk = await _item(admin, "Schneebesen", aliases={"en-GB": ["whisk"]})
    token = await agent_token(make_user, client)
    result = await call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "Palatschinken",
            "steps": [
                {
                    "text": "Teig schlagen.",
                    "equipment": [
                        {"name": "whisk"},
                        {"name": "Palatschinkenpfanne", "count": 2, "note": "20 cm"},
                    ],
                }
            ],
        },
    )
    assert result["isError"] is False, result
    created = result["structuredContent"]
    assert [e["name"] for e in created["created_equipment"]] == ["Palatschinkenpfanne"]
    edit = (await client.get(f"{WEB}/recipes/{created['id']}/edit")).json()
    items = edit["steps"][0]["equipment"]
    assert items[0]["equipment_id"] == whisk["id"]
    assert items[1]["count"] == 2
    assert items[1]["notes"]["de-AT"]["note"] == "20 cm"
    draft = (await client.get(f"{WEB}/equipment", params={"status": "draft"})).json()
    assert [e["name"] for e in draft] == ["Palatschinkenpfanne"]


async def test_make_recipe_without_equipment_still_works(cook: httpx.AsyncClient) -> None:
    salt = await make_ingredient(cook, "Salz")
    recipe = await make_recipe(cook, "Salzwasser", [("Kochen.", [{"ingredient_id": salt["id"]}])])
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    assert detail["equipment"] == []
    assert detail["steps"][0]["equipment"] == []
