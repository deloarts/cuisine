"""Recipes as `.cui` files between cooks: exporting a recipe follows its
visibility exactly like reading it, importing needs write:recipes and lands
as drafts with their origin, a second import of the same recipe offers the
earlier import for an update (a normal revision keeping visibility, status,
step and variation ids) or becomes a new copy, and changes of a variation
that no longer fit are reported."""

import io
import json
import uuid
import zipfile
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from sqlalchemy import select

from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.platform.adapters.outbound.persistence.session import SessionLocal
from tests.integration.conftest import COOK_PERMISSIONS
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import unit_id

pytestmark = pytest.mark.usefixtures("user_choice_privacy")

CUI = "application/vnd.cuisine.recipe+zip"


def _manifest(data: bytes) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads(zipfile.ZipFile(io.BytesIO(data)).read("recipes.json"))
    return manifest


def _rewrite(data: bytes, change: Callable[[dict[str, Any]], None]) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as target:
        for info in source.infolist():
            content = source.read(info)
            if info.filename == "recipes.json":
                manifest = json.loads(content)
                change(manifest)
                content = json.dumps(manifest).encode()
            target.writestr(info.filename, content)
    return out.getvalue()


async def _save(client: httpx.AsyncClient, recipe_id: str, **changes: Any) -> dict[str, Any]:
    """Saves the recipe as its editor shows it, with the given fields
    replaced, keeping step and line ids."""
    edit = (await client.get(f"{WEB}/recipes/{recipe_id}/edit")).json()
    body: dict[str, Any] = {
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
                        "sub_recipe_id": i["sub_recipe_id"],
                        "amount": i["amount"],
                        "unit_id": i["unit_id"],
                    }
                    for i in s["ingredients"]
                ],
            }
            for s in edit["steps"]
        ],
        **changes,
    }
    saved = await client.put(f"{WEB}/recipes/{recipe_id}", headers=CSRF, json=body)
    assert saved.status_code == 200, saved.text
    result: dict[str, Any] = saved.json()
    return result


async def _export(client: httpx.AsyncClient, recipe_id: str, status: int = 200) -> bytes:
    response = await client.get(f"{WEB}/recipes/{recipe_id}/export")
    assert response.status_code == status, response.text
    return response.content


async def _preview(client: httpx.AsyncClient, data: bytes) -> list[dict[str, Any]]:
    response = await client.post(
        f"{WEB}/recipes/import/preview",
        headers=CSRF,
        files={"file": ("recipe.cui", data, CUI)},
    )
    assert response.status_code == 200, response.text
    recipes: list[dict[str, Any]] = response.json()["recipes"]
    return recipes


async def _import(
    client: httpx.AsyncClient, data: bytes, update: list[str] | None = None, status: int = 200
) -> dict[str, Any]:
    response = await client.post(
        f"{WEB}/recipes/import",
        headers=CSRF,
        files={"file": ("recipe.cui", data, CUI)},
        data={"update": update or []},
    )
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    return body


async def _origin(recipe_id: str) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    async with SessionLocal() as db:
        row = await db.scalar(
            select(RecipeModel).where(RecipeModel.public_id == uuid.UUID(recipe_id))
        )
        assert row is not None
        return row.origin_instance_id, row.origin_public_id


async def _tart(cook: httpx.AsyncClient, **extra: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """A tart using a pastry as its sub-recipe, both published."""
    g = await unit_id(cook, "g")
    flour = await make_ingredient(cook, "Mehl")
    fruit = await make_ingredient(cook, "Marille")
    pastry = await make_recipe(
        cook,
        "Mürbteig",
        [("Kneten.", [{"ingredient_id": flour["id"], "amount": 250, "unit_id": g}])],
    )
    tart = await make_recipe(
        cook,
        "Marillentarte",
        [
            ("Teig ausrollen.", [{"sub_recipe_id": pastry["id"], "amount": 250, "unit_id": g}]),
            (
                f"Mit @[Marille](ingredient:{fruit['id']}) belegen.",
                [{"ingredient_id": fruit["id"], "amount": 6}],
            ),
        ],
        **extra,
    )
    return pastry, tart


async def test_export_follows_the_visibility_of_the_recipe(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    visitor: httpx.AsyncClient,
    make_user: MakeUser,
) -> None:
    pastry, tart = await _tart(cook)
    friend = await make_user("friend")
    stranger = await make_user("stranger")

    # Anonymous visitors have no export route at all.
    assert (await visitor.get(f"{WEB}/recipes/{tart['id']}/export")).status_code == 401

    response = await cook.get(f"{WEB}/recipes/{tart['id']}/export")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == CUI
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="marillentarte.cui"'
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    manifest = _manifest(response.content)
    assert [r["id"] for r in manifest["recipes"]] == [pastry["id"], tart["id"]]

    # Instance: every signed-in user, without any permission.
    await login(visitor, "friend@example.com", "cook-password-1")
    assert await _export(visitor, tart["id"])
    # Private: the owner only, administrators included in the refusal.
    await _save(cook, tart["id"], visibility="private")
    await _export(visitor, tart["id"], status=404)
    await _export(admin, tart["id"], status=404)
    assert await _export(cook, tart["id"])
    # Shared with the friend: the friend yes, a stranger no.
    await _save(cook, tart["id"], visibility="shared", shared_user_ids=[friend["id"]])
    assert await _export(visitor, tart["id"])
    await login(visitor, "stranger@example.com", "cook-password-1")
    await _export(visitor, tart["id"], status=404)
    assert stranger["id"]

    # A draft: its owner only. An unknown id answers the same 404.
    draft = await make_recipe(cook, "Entwurf", [("Rühren.", [])], publish=False)
    await _export(visitor, draft["id"], status=404)
    assert await _export(cook, draft["id"])
    await _export(cook, str(uuid.uuid4()), status=404)

    # A private sub-recipe stays out of the file of whoever may not see it.
    await _save(cook, tart["id"], visibility="instance")
    await _save(cook, pastry["id"], visibility="private")
    manifest = _manifest(await _export(visitor, tart["id"]))
    assert [r["id"] for r in manifest["recipes"]] == [tart["id"]]


async def test_household_members_export_household_recipes(
    cook: httpx.AsyncClient, make_user: MakeUser, visitor: httpx.AsyncClient
) -> None:
    _, tart = await _tart(cook)
    await _save(cook, tart["id"], visibility="household")
    partner = await make_user("partner")
    await make_user("outsider")
    await cook.post(f"{WEB}/households", headers=CSRF, json={"name": "Zuhause"})
    invitation = (
        await cook.post(
            f"{WEB}/households/mine/invitations", headers=CSRF, json={"user_id": partner["id"]}
        )
    ).json()
    await login(visitor, "outsider@example.com", "cook-password-1")
    await _export(visitor, tart["id"], status=404)
    await login(visitor, "partner@example.com", "cook-password-1")
    await _export(visitor, tart["id"], status=404)
    joined = await visitor.post(
        f"{WEB}/households/invitations/{invitation['id']}/accept", headers=CSRF
    )
    assert joined.status_code == 200, joined.text
    assert await _export(visitor, tart["id"])


async def test_import_needs_write_recipes_and_the_admin_route_is_gone(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    visitor: httpx.AsyncClient,
) -> None:
    _, tart = await _tart(cook)
    data = await _export(cook, tart["id"])
    await make_user("reader")
    await login(visitor, "reader@example.com", "cook-password-1")
    for path in ("/recipes/import", "/recipes/import/preview"):
        refused = await visitor.post(
            f"{WEB}{path}", headers=CSRF, files={"file": ("recipe.cui", data, CUI)}
        )
        assert refused.status_code == 403
    gone = await admin.post(
        f"{WEB}/admin/recipes/import", headers=CSRF, files={"file": ("recipe.cui", data, CUI)}
    )
    assert gone.status_code in (404, 405)
    broken = await _import(cook, b"not a zip", status=422)
    assert broken


async def test_import_records_the_origin_and_updates_the_earlier_import(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    visitor: httpx.AsyncClient,
) -> None:
    _, tart = await _tart(cook)
    vegan = await cook.post(
        f"{WEB}/recipes/{tart['id']}/variations",
        headers=CSRF,
        json={
            "name": "Mit Honig",
            "locale": "de-AT",
            "changes": [{"kind": "step_text", "step": 2, "text": "Mit Honig beträufeln."}],
        },
    )
    assert vegan.status_code == 201, vegan.text
    instance_id = (await admin.get(f"{WEB}/admin/host")).json()["instance_id"]
    first = await _export(cook, tart["id"])

    await make_user("friend", permissions=COOK_PERMISSIONS)
    friend = visitor
    await login(friend, "friend@example.com", "cook-password-1")
    assert [r["earlier"] for r in await _preview(friend, first)] == [None, None]
    report = await _import(friend, first)
    assert [(r["title"], r["updated"]) for r in report["recipes"]] == [
        ("Mürbteig", False),
        ("Marillentarte", False),
    ]
    imported = report["recipes"][1]["id"]
    assert await _origin(imported) == (uuid.UUID(instance_id), uuid.UUID(tart["id"]))
    edit = (await friend.get(f"{WEB}/recipes/{imported}/edit")).json()
    assert edit["status"] == "draft"
    (variation,) = (await friend.get(f"{WEB}/recipes/{imported}/variations")).json()

    # The friend makes it their own: published, private.
    published = await friend.post(f"{WEB}/recipes/{imported}/publish", headers=CSRF)
    assert published.status_code == 200, published.text
    await _save(friend, imported, visibility="private")
    first_step_id = edit["steps"][0]["id"]
    second_line_id = edit["steps"][1]["ingredients"][0]["id"]

    # The source changes the second step and adds a third.
    source = (await cook.get(f"{WEB}/recipes/{tart['id']}/edit")).json()
    steps = [
        {
            "id": s["id"],
            "translations": s["translations"],
            "ingredients": [
                {k: i[k] for k in ("id", "ingredient_id", "sub_recipe_id", "amount", "unit_id")}
                for i in s["ingredients"]
            ],
        }
        for s in source["steps"]
    ]
    steps[1]["translations"] = {"de-AT": {"text": "Mit Marillen belegen und backen."}}
    steps.append({"translations": {"de-AT": {"text": "Abkühlen lassen."}}, "ingredients": []})
    await _save(cook, tart["id"], steps=steps)
    second = await _export(cook, tart["id"])

    preview = await _preview(friend, second)
    assert preview[1]["earlier"] == {
        "id": imported,
        "title": "Marillentarte",
        "status": "published",
    }
    report = await _import(friend, second, update=[tart["id"]])
    updated = report["recipes"][1]
    assert (updated["id"], updated["updated"]) == (imported, True)
    # The pastry was not chosen, so it became a new copy without an origin.
    pastry_copy = report["recipes"][0]
    assert pastry_copy["updated"] is False
    assert await _origin(pastry_copy["id"]) == (None, None)

    after = (await friend.get(f"{WEB}/recipes/{imported}/edit")).json()
    assert (after["status"], after["visibility"]) == ("published", "private")
    assert [s["translations"]["de-AT"]["text"] for s in after["steps"]] == [
        "Teig ausrollen.",
        "Mit Marillen belegen und backen.",
        "Abkühlen lassen.",
    ]
    assert after["steps"][0]["id"] == first_step_id
    assert after["steps"][1]["ingredients"][0]["id"] == second_line_id
    assert after["steps"][0]["ingredients"][0]["sub_recipe_id"] == pastry_copy["id"]
    revisions = (await friend.get(f"{WEB}/recipes/{imported}/revisions")).json()["items"]
    assert (revisions[0]["kind"], revisions[0]["note"]) == ("updated", "Updated from import")
    # The variation the first import brought is replaced, not added twice.
    variations = (await friend.get(f"{WEB}/recipes/{imported}/variations")).json()
    assert [v["id"] for v in variations] == [variation["id"]]

    # Importing it once more as a new copy keeps the earlier import as the
    # one that carries the origin.
    report = await _import(friend, second)
    copy_id = report["recipes"][1]["id"]
    assert copy_id != imported and report["recipes"][1]["updated"] is False
    assert await _origin(copy_id) == (None, None)
    assert await _origin(imported) == (uuid.UUID(instance_id), uuid.UUID(tart["id"]))

    # Another cook holds an import of their own with the same origin.
    report = await _import(admin, second)
    assert await _origin(report["recipes"][1]["id"]) == (
        uuid.UUID(instance_id),
        uuid.UUID(tart["id"]),
    )


async def test_an_update_without_steps_does_not_stay_published(
    cook: httpx.AsyncClient, make_user: MakeUser, visitor: httpx.AsyncClient
) -> None:
    _, tart = await _tart(cook)
    data = await _export(cook, tart["id"])
    await make_user("friend", permissions=COOK_PERMISSIONS)
    await login(visitor, "friend@example.com", "cook-password-1")
    imported = (await _import(visitor, data))["recipes"][1]["id"]
    assert (await visitor.post(f"{WEB}/recipes/{imported}/publish", headers=CSRF)).is_success

    def no_steps(manifest: dict[str, Any]) -> None:
        manifest["recipes"][1]["snapshot"]["steps"] = []
        manifest["recipes"][1]["variations"] = []

    report = await _import(visitor, _rewrite(data, no_steps), update=[tart["id"]])
    assert ("status", "Marillentarte") in {(c["kind"], c["name"]) for c in report["conflicts"]}
    after = (await visitor.get(f"{WEB}/recipes/{imported}/edit")).json()
    assert (after["status"], after["steps"]) == ("draft", [])


async def test_variation_changes_that_do_not_fit_are_reported(cook: httpx.AsyncClient) -> None:
    _, tart = await _tart(cook)
    created = await cook.post(
        f"{WEB}/recipes/{tart['id']}/variations",
        headers=CSRF,
        json={
            "name": "Mit Honig",
            "locale": "de-AT",
            "changes": [{"kind": "step_text", "step": 2, "text": "Mit Honig beträufeln."}],
        },
    )
    assert created.status_code == 201, created.text

    def shorter(manifest: dict[str, Any]) -> None:
        entry = manifest["recipes"][1]
        entry["snapshot"]["steps"] = entry["snapshot"]["steps"][:1]
        changes = entry["variations"][0]["changes"]
        changes.append({**changes[0], "id": "x", "kind": "sprinkle"})

    report = await _import(cook, _rewrite(await _export(cook, tart["id"]), shorter))
    variation = [c for c in report["conflicts"] if c["kind"] == "variation"]
    assert [(c["name"], c["recipe"]) for c in variation] == [
        ("Mit Honig", "Marillentarte"),
        ("Mit Honig", "Marillentarte"),
    ]
    assert "sprinkle" in variation[0]["detail"] and "step_text" in variation[1]["detail"]
