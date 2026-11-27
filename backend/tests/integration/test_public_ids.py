"""Public ids: steps and lines keep theirs across saves and restores, seeded
rows get the deterministic seed id, the instance id stays, and the resolver
answers what an id opens under the read rule of its kind."""

from typing import Any
from uuid import UUID
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from src.bootstrap.cookbook_seed import ensure_reference_data
from src.bootstrap.seed import ensure_instance_id
from src.cookbook.adapters.outbound.persistence.models.equipment_models import KitchenModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeNoteModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import TagModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import UnitModel
from src.cookbook.adapters.outbound.persistence.models.revision_models import RecipeRevisionModel
from src.cookbook.domain.services.seed_ids import seeded_public_id
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id
from tests.integration.test_admin_area import FakeRedis


async def _edit(client: httpx.AsyncClient, recipe_id: str) -> dict[str, Any]:
    response = await client.get(f"{WEB}/recipes/{recipe_id}/edit")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _request_from(edit: dict[str, Any]) -> dict[str, Any]:
    """The editor's save body, built from its response with every id."""
    return {
        "original_locale": edit["original_locale"],
        "translations": edit["translations"],
        "base_servings": edit["base_servings"],
        "steps": [
            {
                "id": s["id"],
                "translations": s["translations"],
                "ingredients": [
                    {
                        "id": i["id"],
                        "ingredient_id": i["ingredient_id"],
                        "amount": i["amount"],
                        "unit_id": i["unit_id"],
                    }
                    for i in s["ingredients"]
                ],
                "equipment": [
                    {"id": e["id"], "equipment_id": e["equipment_id"], "count": e["count"]}
                    for e in s["equipment"]
                ],
            }
            for s in edit["steps"]
        ],
    }


async def _three_step_recipe(client: httpx.AsyncClient, admin: httpx.AsyncClient) -> dict[str, Any]:
    flour = await make_ingredient(client, "Mehl")
    sugar = await make_ingredient(client, "Zucker")
    g = await unit_id(client, "g")
    bowl = await admin.post(
        f"{WEB}/equipment",
        headers=CSRF,
        json={"kind": "utensil", "translations": {"de-AT": {"name": "Schüssel"}}},
    )
    assert bowl.status_code == 201, bowl.text
    recipe = await make_recipe(
        client,
        "Kuchen",
        [
            ("Mischen.", [{"ingredient_id": flour["id"], "amount": 200, "unit_id": g}]),
            ("Süßen.", [{"ingredient_id": sugar["id"], "amount": 50, "unit_id": g}]),
            ("Backen.", []),
        ],
    )
    edit = await _edit(client, recipe["id"])
    body = _request_from(edit)
    body["steps"][0]["equipment"] = [{"equipment_id": bowl.json()["id"], "count": 1}]
    saved = await client.put(f"{WEB}/recipes/{recipe['id']}", headers=CSRF, json=body)
    assert saved.status_code == 200, saved.text
    result: dict[str, Any] = saved.json()
    return result


# ── Steps and lines keep their ids ───────────────────────────────────


async def test_a_save_keeps_the_ids_it_names_and_gives_new_rows_fresh_ones(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    recipe = await _three_step_recipe(cook, admin)
    before = await _edit(cook, recipe["id"])
    step_ids = [s["id"] for s in before["steps"]]
    line_id = before["steps"][0]["ingredients"][0]["id"]
    equipment_id = before["steps"][0]["equipment"][0]["id"]
    assert len(set(step_ids)) == 3

    body = _request_from(before)
    # Drop the second step, add a new one, add a new line to the first step
    # and send an id this recipe never had on the third.
    del body["steps"][1]
    body["steps"][0]["ingredients"].append(
        {"ingredient_id": before["steps"][1]["ingredients"][0]["ingredient_id"], "amount": 5}
    )
    body["steps"][1]["id"] = str(uuid4())
    body["steps"].append({"translations": {"de-AT": {"text": "Servieren."}}})
    saved = await cook.put(f"{WEB}/recipes/{recipe['id']}", headers=CSRF, json=body)
    assert saved.status_code == 200, saved.text

    after = await _edit(cook, recipe["id"])
    assert after["steps"][0]["id"] == step_ids[0]
    assert after["steps"][0]["ingredients"][0]["id"] == line_id
    assert after["steps"][0]["equipment"][0]["id"] == equipment_id
    new_line = after["steps"][0]["ingredients"][1]["id"]
    assert new_line not in {line_id, before["steps"][1]["ingredients"][0]["id"]}
    assert after["steps"][1]["id"] not in {*step_ids, body["steps"][1]["id"]}
    assert after["steps"][2]["id"] not in step_ids

    detail = (await cook.get(f"{WEB}/recipes/{recipe['id']}")).json()
    assert [s["id"] for s in detail["steps"]] == [s["id"] for s in after["steps"]]
    assert detail["steps"][0]["ingredients"][0]["line_id"] == line_id
    assert detail["steps"][0]["equipment"][0]["id"] == equipment_id
    assert all(i["line_id"] is None for i in detail["ingredients"])


async def test_saving_the_same_id_twice_keeps_it_once(cook: httpx.AsyncClient) -> None:
    recipe = await make_recipe(cook, "Brot", [("Kneten.", []), ("Backen.", [])])
    edit = await _edit(cook, recipe["id"])
    body = _request_from(edit)
    body["steps"][1]["id"] = body["steps"][0]["id"]
    saved = await cook.put(f"{WEB}/recipes/{recipe['id']}", headers=CSRF, json=body)
    assert saved.status_code == 200, saved.text
    after = await _edit(cook, recipe["id"])
    assert after["steps"][0]["id"] == edit["steps"][0]["id"]
    assert after["steps"][1]["id"] not in {s["id"] for s in edit["steps"]}


async def test_a_new_recipe_and_a_copy_never_take_over_ids(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    original = await _three_step_recipe(cook, admin)
    edit = await _edit(cook, original["id"])
    taken = {s["id"] for s in edit["steps"]}

    body = _request_from(edit)
    body["translations"] = {"de-AT": {"title": "Zweiter Kuchen"}}
    created = await cook.post(f"{WEB}/recipes", headers=CSRF, json=body)
    assert created.status_code == 201, created.text
    second = await _edit(cook, created.json()["id"])
    assert taken.isdisjoint(s["id"] for s in second["steps"])

    copied = await admin.post(f"{WEB}/recipes/{original['id']}/copy", headers=CSRF)
    assert copied.status_code == 201, copied.text
    copy = await _edit(admin, copied.json()["id"])
    assert taken.isdisjoint(s["id"] for s in copy["steps"])
    assert {i["id"] for s in edit["steps"] for i in s["ingredients"]}.isdisjoint(
        i["id"] for s in copy["steps"] for i in s["ingredients"]
    )


async def test_a_restore_brings_back_the_ids_the_revision_recorded(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    recipe = await _three_step_recipe(cook, admin)
    before = await _edit(cook, recipe["id"])
    revisions = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions")).json()
    number = revisions["items"][0]["number"]
    snapshot = (await cook.get(f"{WEB}/recipes/{recipe['id']}/revisions/{number}")).json()[
        "snapshot"
    ]
    first, recorded = before["steps"][0], snapshot["steps"][0]
    assert [s["id"] for s in snapshot["steps"]] == [s["id"] for s in before["steps"]]
    assert recorded["ingredients"][0]["id"] == first["ingredients"][0]["id"]
    assert recorded["equipment"][0]["id"] == first["equipment"][0]["id"]

    body = _request_from(before)
    del body["steps"][1]
    assert (
        await cook.put(f"{WEB}/recipes/{recipe['id']}", headers=CSRF, json=body)
    ).status_code == 200
    restored = await cook.post(
        f"{WEB}/recipes/{recipe['id']}/revisions/{number}/restore", headers=CSRF
    )
    assert restored.status_code == 200, restored.text

    after = await _edit(cook, recipe["id"])
    assert [s["id"] for s in after["steps"]] == [s["id"] for s in before["steps"]]
    assert [i["id"] for s in after["steps"] for i in s["ingredients"]] == [
        i["id"] for s in before["steps"] for i in s["ingredients"]
    ]


# ── Seeded ids and the instance id ───────────────────────────────────


async def test_seeded_rows_get_the_deterministic_seed_id(resources: None) -> None:
    async with SessionLocal() as db:
        units = (await db.execute(select(UnitModel.seed_key, UnitModel.public_id))).all()
        tags = (await db.execute(select(TagModel.seed_key, TagModel.public_id))).all()
    assert units and tags
    for key, public_id in units:
        assert public_id == seeded_public_id("unit", key)
    for key, public_id in tags:
        assert public_id == seeded_public_id("tag", key)


async def test_seeded_ingredients_get_the_deterministic_seed_id() -> None:
    await ensure_reference_data()
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(IngredientModel.seed_key, IngredientModel.public_id).where(
                    IngredientModel.seed_key.is_not(None)
                )
            )
        ).all()
    assert len(rows) > 100
    assert all(public_id == seeded_public_id("ingredient", key) for key, public_id in rows)


async def test_the_instance_id_is_created_once_and_never_changes(
    admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await ensure_instance_id()
    assert await ensure_instance_id() == first
    async with SessionLocal() as db:
        assert await SqlAlchemySettingsRepository(db).instance_id() == first
    monkeypatch.setattr(deps, "get_redis", lambda: FakeRedis())
    host = (await admin.get(f"{WEB}/admin/host")).json()
    assert UUID(host["instance_id"]) == first


async def test_the_host_reading_creates_a_missing_instance_id_and_keeps_it(
    admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(deps, "get_redis", lambda: FakeRedis())
    first = (await admin.get(f"{WEB}/admin/host")).json()["instance_id"]
    second = (await admin.get(f"{WEB}/admin/host")).json()["instance_id"]
    assert first == second
    assert UUID(first) == await ensure_instance_id()


# ── The resolver ─────────────────────────────────────────────────────


async def _resolve(client: httpx.AsyncClient, public_id: object) -> httpx.Response:
    return await client.get(f"{WEB}/resolve/{public_id}")


async def _revision_id(recipe_id: str) -> UUID:
    async with SessionLocal() as db:
        found = await db.scalar(
            select(RecipeRevisionModel.public_id)
            .join(RecipeModel, RecipeModel.id == RecipeRevisionModel.recipe_id)
            .where(RecipeModel.public_id == UUID(recipe_id))
        )
    assert found is not None
    return found


async def test_a_recipe_and_its_child_rows_resolve_to_the_recipe_page(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    recipe = await _three_step_recipe(cook, admin)
    edit = await _edit(cook, recipe["id"])
    children = [
        recipe["id"],
        edit["steps"][0]["id"],
        edit["steps"][0]["ingredients"][0]["id"],
        edit["steps"][0]["equipment"][0]["id"],
        await _revision_id(recipe["id"]),
    ]
    for public_id in children:
        response = await _resolve(admin, public_id)
        assert response.status_code == 200, (public_id, response.text)
        assert response.json() == {
            "kind": "recipe",
            "id": recipe["id"],
            "route": f"/recipes/{recipe['id']}",
        }


async def test_resolving_needs_a_session(client: httpx.AsyncClient) -> None:
    assert (await _resolve(client, uuid4())).status_code == 401


async def test_unknown_malformed_and_unregistered_ids_answer_404(cook: httpx.AsyncClient) -> None:
    g = await unit_id(cook, "g")
    for public_id in (uuid4(), "not-a-uuid", g):
        response = await _resolve(cook, public_id)
        assert response.status_code == 404, public_id
        assert response.json()["code"] == "PublicIdNotFoundError"


@pytest.mark.usefixtures("user_choice_privacy")
async def test_a_recipe_the_user_may_not_see_answers_like_an_unknown_id(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    private = await make_recipe(cook, "Geheim", [("Rühren.", [])], visibility="private")
    draft = await make_recipe(cook, "Entwurf", [("Rühren.", [])], publish=False)
    for recipe in (private, draft):
        step_id = (await _edit(cook, recipe["id"]))["steps"][0]["id"]
        for public_id in (recipe["id"], step_id):
            own = await _resolve(cook, public_id)
            assert own.status_code == 200, own.text
            assert own.json()["id"] == recipe["id"]
            hidden = await _resolve(admin, public_id)
            assert hidden.status_code == 404
            assert hidden.json() == (await _resolve(admin, uuid4())).json()


async def test_a_personal_note_resolves_for_its_owner_only(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    recipe = await make_recipe(cook, "Suppe", [("Kochen.", [])])
    noted = await cook.put(
        f"{WEB}/recipes/{recipe['id']}/note", headers=CSRF, json={"text": "mehr Salz"}
    )
    assert noted.status_code == 200, noted.text
    async with SessionLocal() as db:
        note_id = await db.scalar(select(RecipeNoteModel.public_id))
    own = await _resolve(cook, note_id)
    assert own.status_code == 200, own.text
    assert own.json()["route"] == f"/recipes/{recipe['id']}"
    # The admin sees the recipe, but the note is the cook's alone.
    assert (await _resolve(admin, recipe["id"])).status_code == 200
    assert (await _resolve(admin, note_id)).status_code == 404


async def test_ingredients_variations_and_shopping_lists_resolve_to_their_pages(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    flour = await make_ingredient(cook, "Mehl")
    resolved = (await _resolve(admin, flour["id"])).json()
    assert resolved == {
        "kind": "ingredient",
        "id": flour["id"],
        "route": f"/ingredients/{flour['id']}",
    }

    recipe = await make_recipe(cook, "Nockerl", [("Rühren.", [])])
    variation = await cook.post(
        f"{WEB}/recipes/{recipe['id']}/variations",
        headers=CSRF,
        json={"name": "Scharf", "locale": "de-AT", "private": True},
    )
    assert variation.status_code == 201, variation.text
    vid = variation.json()["id"]
    own = (await _resolve(cook, vid)).json()
    assert own == {
        "kind": "variation",
        "id": vid,
        "route": f"/recipes/{recipe['id']}?variation={vid}",
    }
    # A private variation is its author's alone.
    assert (await _resolve(admin, vid)).status_code == 404

    created = await cook.post(f"{WEB}/shopping-lists", headers=CSRF, json={"name": "Einkauf"})
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]
    item = await cook.post(
        f"{WEB}/shopping-lists/{list_id}/items", headers=CSRF, json={"text": "Milch"}
    )
    assert item.status_code == 200, item.text
    item_id = item.json()["items"][0]["id"]
    for public_id in (list_id, item_id):
        answer = (await _resolve(cook, public_id)).json()
        assert answer == {"kind": "shopping_list", "id": list_id, "route": f"/shopping/{list_id}"}
        assert (await _resolve(admin, public_id)).status_code == 404


async def test_a_household_and_its_kitchen_resolve_for_members_only(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    founded = await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "Daheim"})
    assert founded.status_code == 201, founded.text
    household_id = founded.json()["id"]
    own = (await _resolve(cook, household_id)).json()
    assert own == {"kind": "household", "id": household_id, "route": "/household"}
    assert (await _resolve(admin, household_id)).status_code == 404

    set_up = await cook.post(f"{WEB}/kitchen/setup", headers=CSRF, json={"equipment_ids": []})
    assert set_up.status_code == 200, set_up.text
    async with SessionLocal() as db:
        kitchen_id = await db.scalar(select(KitchenModel.public_id))
    kitchen = (await _resolve(cook, kitchen_id)).json()
    assert kitchen == {"kind": "kitchen", "id": str(kitchen_id), "route": "/kitchen"}
    assert (await _resolve(admin, kitchen_id)).status_code == 404
