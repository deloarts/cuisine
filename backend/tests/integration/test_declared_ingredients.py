"""The recipe's declared ingredient list through the API: saving and reading
it in the editor with its ids, the detail's merged list, translating its
notes, the ingredient filter, revisions and restoring, the `.cui` round trip
and an agent's draft."""

from typing import Any

import httpx

from tests.integration.conftest import COOK_PERMISSIONS
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import unit_id
from tests.integration.test_mcp import _cook_token
from tests.integration.test_mcp import call

CUI = "application/vnd.cuisine.recipe+zip"


async def _create(cook: httpx.AsyncClient, **extra: Any) -> dict[str, Any]:
    flour = await make_ingredient(cook, "Mehl", kcal=350)
    milk = await make_ingredient(cook, "Milch")
    g = await unit_id(cook, "g")
    ml = await unit_id(cook, "ml")
    payload = recipe_payload(
        "Palatschinken",
        [("Teig rühren.", [{"ingredient_id": flour["id"], "amount": 100, "unit_id": g}])],
        ingredients=[
            {
                "ingredient_id": flour["id"],
                "amount": 250,
                "unit_id": g,
                "notes": {"de-AT": {"note": "glatt"}},
            },
            {"ingredient_id": milk["id"], "amount": 500, "unit_id": ml},
        ],
        **extra,
    )
    created = await cook.post(f"{WEB}/recipes", headers=CSRF, json=payload)
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    body["_flour"], body["_milk"], body["_g"], body["_ml"] = flour, milk, g, ml
    return body


def _amounts(detail: dict[str, Any]) -> dict[str, tuple[float | None, str | None]]:
    return {
        line["ingredient_id"]: (line["amount"], line["unit"]["code"] if line["unit"] else None)
        for line in detail["ingredients"]
    }


async def test_the_editor_saves_and_returns_the_declared_list_with_its_ids(
    cook: httpx.AsyncClient,
) -> None:
    recipe = await _create(cook)
    flour, milk, g = recipe["_flour"], recipe["_milk"], recipe["_g"]
    declared = recipe["ingredients"]
    assert [(line["ingredient_id"], line["amount"]) for line in declared] == [
        (flour["id"], 250),
        (milk["id"], 500),
    ]
    assert declared[0]["ingredient_name"] == "Mehl"
    assert declared[0]["notes"] == {"de-AT": {"note": "glatt"}}

    # A save that names the loaded ids keeps them; a new line gets a fresh one.
    sugar = await make_ingredient(cook, "Zucker")
    kept = {k: declared[0][k] for k in ("id", "ingredient_id", "amount", "unit_id")}
    payload = recipe_payload(
        "Palatschinken",
        [("Teig rühren.", [{"ingredient_id": flour["id"], "amount": 100, "unit_id": g}])],
        ingredients=[kept, {"ingredient_id": sugar["id"], "amount": 1, "unit_id": g}],
    )
    saved = await cook.put(f"{WEB}/recipes/{recipe['id']}", headers=CSRF, json=payload)
    assert saved.status_code == 200, saved.text
    lines = saved.json()["ingredients"]
    assert lines[0]["id"] == declared[0]["id"]
    assert lines[1]["id"] not in {d["id"] for d in declared}
    edit = (await cook.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    assert [line["ingredient_id"] for line in edit["ingredients"]] == [flour["id"], sugar["id"]]

    unknown = await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json={
            **payload,
            "ingredients": [{"ingredient_id": "00000000-0000-4000-8000-000000000000"}],
        },
    )
    assert unknown.status_code == 404


async def test_the_detail_lists_the_larger_of_declared_and_used(cook: httpx.AsyncClient) -> None:
    recipe = await _create(cook)
    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    assert _amounts(detail) == {
        recipe["_flour"]["id"]: (250, "g"),
        recipe["_milk"]["id"]: (500, "ml"),
    }
    # 250 g flour at 350 kcal per 100 g, for two servings.
    assert detail["nutrition"]["total"]["kcal"] == 875
    doubled = (await cook.get(f"{WEB}/recipes/{recipe['id']}", params={"servings": 4})).json()
    assert _amounts(doubled)[recipe["_milk"]["id"]] == (1000, "ml")

    # The ingredient filter finds a recipe through its declared list too.
    found = await cook.get(
        f"{WEB}/recipes", params={"ingredient_id": recipe["_milk"]["id"], "status": "drafts"}
    )
    assert found.status_code == 200, found.text
    assert [r["id"] for r in found.json()["items"]] == [recipe["id"]]


async def test_a_translation_adds_the_declared_notes(cook: httpx.AsyncClient) -> None:
    recipe = await _create(cook)
    translated = await cook.put(
        f"{WEB}/recipes/{recipe['id']}/translation",
        headers=CSRF,
        json={
            "locale": "en-GB",
            "text": {"title": "Pancakes"},
            "steps": [{"text": "Stir the batter."}],
            "ingredient_notes": [{"note": "plain"}, {"note": ""}],
        },
    )
    assert translated.status_code == 200, translated.text
    notes = [line["notes"] for line in translated.json()["ingredients"]]
    assert notes == [{"de-AT": {"note": "glatt"}, "en-GB": {"note": "plain"}}, {}]


async def test_revisions_record_and_restore_the_declared_list(cook: httpx.AsyncClient) -> None:
    recipe = await _create(cook)
    flour, g = recipe["_flour"], recipe["_g"]
    original = recipe["ingredients"]
    emptied = await cook.put(
        f"{WEB}/recipes/{recipe['id']}",
        headers=CSRF,
        json=recipe_payload(
            "Palatschinken",
            [("Teig rühren.", [{"ingredient_id": flour["id"], "amount": 100, "unit_id": g}])],
        ),
    )
    assert emptied.status_code == 200
    assert emptied.json()["ingredients"] == []

    first = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions/1")).json()
    snapshot_lines = first["snapshot"]["ingredients"]
    assert [line["id"] for line in snapshot_lines] == [line["id"] for line in original]
    assert snapshot_lines[1]["ingredient_id"] == recipe["_milk"]["id"]
    assert first["snapshot"]["names"]["ingredients"][recipe["_milk"]["id"]] == {"de-AT": "Milch"}

    restored = await cook.post(f"{WEB}/recipes/{recipe['id']}/revisions/1/restore", headers=CSRF)
    assert restored.status_code == 200, restored.text
    lines = restored.json()["ingredients"]
    assert [(line["id"], line["amount"]) for line in lines] == [
        (line["id"], line["amount"]) for line in original
    ]


async def test_a_cui_file_carries_the_declared_list(
    cook: httpx.AsyncClient, make_user: MakeUser, visitor: httpx.AsyncClient
) -> None:
    recipe = await _create(cook)
    exported = await cook.get(f"{WEB}/recipes/{recipe['id']}/export")
    assert exported.status_code == 200, exported.text

    await make_user("friend", permissions=COOK_PERMISSIONS)
    await login(visitor, "friend@example.com", "cook-password-1")
    imported = await visitor.post(
        f"{WEB}/recipes/import",
        headers=CSRF,
        files={"file": ("recipe.cui", exported.content, CUI)},
    )
    assert imported.status_code == 200, imported.text
    (entry,) = imported.json()["recipes"]
    edit = (await visitor.get(f"{WEB}/recipes/{entry['id']}/edit")).json()
    assert [(line["ingredient_name"], line["amount"]) for line in edit["ingredients"]] == [
        ("Mehl", 250),
        ("Milch", 500),
    ]
    assert edit["ingredients"][0]["notes"] == {"de-AT": {"note": "glatt"}}
    # The importer's ids are derived from the source's, never taken over.
    assert {line["id"] for line in edit["ingredients"]}.isdisjoint(
        {line["id"] for line in recipe["ingredients"]}
    )


async def test_an_agent_drafts_a_recipe_with_a_declared_list(
    make_user: MakeUser, client: httpx.AsyncClient, resources: None
) -> None:
    token = await _cook_token(make_user, client)
    result = await call(
        client,
        token,
        "create_recipe_draft",
        {
            "original_locale": "de-AT",
            "title": "Grießnockerlsuppe",
            "steps": [{"text": "Nockerl formen", "ingredients": [{"name": "Grieß", "amount": 50}]}],
            "ingredients": [
                {"name": "Grieß", "amount": 100, "unit": "g"},
                {"name": "Rindsuppe", "amount": 1, "unit": "l", "note": "heiß"},
            ],
        },
    )
    assert result["isError"] is False, result
    created = result["structuredContent"]
    assert len(created["created_ingredients"]) == 2
    edit = (await client.get(f"{WEB}/recipes/{created['id']}/edit")).json()
    assert [(line["ingredient_name"], line["amount"]) for line in edit["ingredients"]] == [
        ("Grieß", 100),
        ("Rindsuppe", 1),
    ]
    assert edit["ingredients"][1]["notes"] == {"de-AT": {"note": "heiß"}}
