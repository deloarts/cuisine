"""The `cuisine-recipes` format through the admin archive: the golden v1
file imports on every run, an export validates against the checked-in JSON
Schema and carries the instance id, step and line ids and the variations the
exporter may see, imported variations become the importer's own, and
readers ignore unknown fields but refuse a newer version."""

import io
import json
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import jsonschema

from tests.integration.conftest import COOK_PERMISSIONS
from tests.integration.conftest import CSRF
from tests.integration.conftest import LoginSystem
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import tag_id
from tests.integration.cookbook_helpers import unit_id

BACKEND = Path(__file__).resolve().parents[2]
GOLDEN_V1 = BACKEND / "tests" / "fixtures" / "formats" / "cuisine-recipes.v1.cui"
SCHEMA_V1 = BACKEND / "formats" / "cuisine-recipes.v1.schema.json"


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


async def _import(admin: httpx.AsyncClient, data: bytes, status: int = 200) -> dict[str, Any]:
    response = await admin.post(
        f"{WEB}/recipes/import",
        headers=CSRF,
        files={"file": ("recipes.cui", data, "application/zip")},
    )
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_the_golden_v1_file_imports(admin: httpx.AsyncClient, resources: None) -> None:
    """Written once by the exporter of the first release; it must import
    on every build, whatever the format layer becomes."""
    report = await _import(admin, GOLDEN_V1.read_bytes())
    assert [(r["source_id"], r["title"]) for r in report["recipes"]] == [
        ("358e3858-73a9-4b19-b1cf-0bf38ccd5e99", "Mürbteig"),
        ("2e82e346-1e8d-4834-be32-b8f82c438ca2", "Drachenfruchttarte"),
    ]
    assert report["created_ingredients"] == ["Weizenmehl", "Drachenfrucht"]
    assert report["created_equipment"] == ["Dough bowl"]
    assert (report["matched_ingredients"], report["matched_equipment"]) == (0, 0)
    assert report["conflicts"] == []

    pastry_id, tart_id = (r["id"] for r in report["recipes"])
    tart = (await admin.get(f"{WEB}/recipes/{tart_id}/edit")).json()
    assert tart["status"] == "draft"
    assert tart["translations"]["en-GB"]["title"] == "Dragon fruit tart"
    assert (tart["base_servings"], tart["rest_minutes"], tart["difficulty"]) == (6, 10, "medium")
    assert tart["source_name"] == "Oma"
    assert tart["tag_ids"] == [await tag_id(admin, "Dessert")]
    assert tart["cover_image_id"] not in (None, "78e91ab3-5ce4-434a-ba15-3b82fa510a7b")

    rolling, topping = tart["steps"]
    assert rolling["ingredients"][0]["sub_recipe_id"] == pastry_id
    assert rolling["ingredients"][0]["unit_id"] == await unit_id(admin, "g")
    bowl = rolling["equipment"][0]
    assert (bowl["count"], bowl["notes"]["de-AT"]["note"]) == (1, "groß")
    text = rolling["translations"]["de-AT"]["text"]
    assert f"recipe:{pastry_id}" in text and f"equipment:{bowl['equipment_id']}" in text
    assert rolling["image_id"] not in (None, "fd6bc862-ed4b-45ba-86e0-5b916539f9a9")
    assert rolling["duration_minutes"] == 15
    # Source step and line ids are never taken over.
    assert rolling["id"] != "2f28eae6-649b-4eec-b369-85d9922a78f1"

    fruit_line = topping["ingredients"][0]
    assert fruit_line["unit_id"] == await unit_id(admin, "piece")
    assert fruit_line["notes"]["de-AT"]["note"] == "in Scheiben"
    assert f"ingredient:{fruit_line['ingredient_id']}" in topping["translations"]["de-AT"]["text"]
    fruit = (await admin.get(f"{WEB}/ingredients/{fruit_line['ingredient_id']}")).json()
    assert fruit["status"] == "draft" and fruit["nutrition"]["kcal"] == 60
    assert [(c["unit_code"], c["grams"]) for c in fruit["conversions"]] == [("piece", 350)]


async def test_readers_ignore_unknown_fields(admin: httpx.AsyncClient, resources: None) -> None:
    def future(manifest: dict[str, Any]) -> None:
        manifest["signature"] = {"alg": "none"}
        entry = manifest["recipes"][1]
        entry["rating"] = 5
        entry["snapshot"]["servings_label"] = {"de-AT": "Stück"}
        entry["snapshot"]["steps"][0]["timer"] = {"seconds": 60}
        manifest["catalogue"]["units"]["c15309de-a50b-58ec-af68-f3be27ea6786"]["system"] = "si"

    report = await _import(admin, _rewrite(GOLDEN_V1.read_bytes(), future))
    assert [r["title"] for r in report["recipes"]] == ["Mürbteig", "Drachenfruchttarte"]
    assert report["conflicts"] == []


async def test_a_newer_or_foreign_document_is_refused(admin: httpx.AsyncClient) -> None:
    def newer(manifest: dict[str, Any]) -> None:
        manifest["version"] = 2

    def broken(manifest: dict[str, Any]) -> None:
        manifest["recipes"][0]["snapshot"]["base_servings"] = "four"

    refused = await _import(admin, _rewrite(GOLDEN_V1.read_bytes(), newer), status=422)
    assert "newer Cuisine" in json.dumps(refused)
    refused = await _import(admin, _rewrite(GOLDEN_V1.read_bytes(), broken), status=422)
    assert "base_servings" in json.dumps(refused)


async def _vary(client: httpx.AsyncClient, recipe_id: str, body: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(f"{WEB}/recipes/{recipe_id}/variations", headers=CSRF, json=body)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def test_an_export_validates_and_carries_variations(
    admin: httpx.AsyncClient,
    cook: httpx.AsyncClient,
    make_user: MakeUser,
    login_system: LoginSystem,
) -> None:
    g = await unit_id(cook, "g")
    milk = await make_ingredient(cook, "Vollmilch")
    oat = await make_ingredient(cook, "Haferdrink")
    flour = await make_ingredient(cook, "Dinkelmehl")
    recipe = await make_recipe(
        cook,
        "Dinkelpalatschinken",
        [
            (
                f"@[Vollmilch](ingredient:{milk['id']}) und Mehl verrühren.",
                [
                    {"ingredient_id": milk["id"], "amount": 250, "unit_id": g},
                    {"ingredient_id": flour["id"], "amount": 100, "unit_id": g},
                ],
            )
        ],
    )
    vegan = {
        "name": "Vegan",
        "locale": "de-AT",
        "note": "Ohne Milch.",
        "changes": [{"kind": "swap", "ingredient_id": milk["id"], "to_ingredient_id": oat["id"]}],
    }
    await _vary(cook, recipe["id"], vegan)
    await _vary(cook, recipe["id"], {**vegan, "name": "Geheim", "private": True})
    await _vary(
        admin,
        recipe["id"],
        {
            "name": "Meine",
            "locale": "de-AT",
            "private": True,
            "changes": [{"kind": "step_text", "step": 1, "text": "Alles verrühren."}],
        },
    )
    # A third author who hides the name from other instances, in the admin's
    # browser for a moment.
    await make_user("anna", permissions=COOK_PERMISSIONS)
    await login(admin, "anna@example.com", "cook-password-1")
    hidden = await admin.patch(
        f"{WEB}/users/me", headers=CSRF, json={"show_name_on_paired_instances": False}
    )
    assert hidden.status_code == 200, hidden.text
    await _vary(admin, recipe["id"], {**vegan, "name": "Annas"})
    await login_system(admin)

    exported = await cook.get(f"{WEB}/admin/recipes/export")
    assert exported.status_code == 403
    exporter = admin
    response = await exporter.get(f"{WEB}/admin/recipes/export", params={"recipe_id": recipe["id"]})
    assert response.status_code == 200, response.text
    manifest = _manifest(response.content)
    jsonschema.validate(manifest, json.loads(SCHEMA_V1.read_text(encoding="utf-8")))

    host = (await exporter.get(f"{WEB}/admin/host")).json()
    assert manifest["instance_id"] == host["instance_id"]
    (entry,) = manifest["recipes"]
    assert entry["id"] == recipe["id"]
    edit = (await cook.get(f"{WEB}/recipes/{recipe['id']}/edit")).json()
    step = entry["snapshot"]["steps"][0]
    assert step["id"] == edit["steps"][0]["id"]
    assert [line["id"] for line in step["ingredients"]] == [
        line["id"] for line in edit["steps"][0]["ingredients"]
    ]
    authors = {v["name"]: (v["author_name"], v["private"]) for v in entry["variations"]}
    me = (await exporter.get(f"{WEB}/users/me")).json()
    admin_name = me["full_name"]
    # The cook's private variation stays home; the exporter's own goes along.
    assert authors == {
        "Vegan": ("Cook", False),
        "Annas": (None, False),
        "Meine": (admin_name, True),
    }
    # The swap target is used by a variation only, and still in the catalogue.
    assert oat["id"] in manifest["catalogue"]["ingredients"]

    report = await _import(exporter, response.content)
    new_id = report["recipes"][0]["id"]
    assert [c["kind"] for c in report["conflicts"]] == ["title"]
    variations = (await exporter.get(f"{WEB}/recipes/{new_id}/variations")).json()
    by_name = {v["name"]: v for v in variations}
    assert set(by_name) == {"Vegan", "Annas", "Meine"}
    assert {v["author"]["display_name"] for v in variations} == {admin_name}
    assert by_name["Vegan"]["note"] == "Ohne Milch.\n\nOriginally by Cook."
    assert by_name["Annas"]["note"] == "Ohne Milch.\n\nOriginally by another cook."
    assert by_name["Meine"]["note"] == f"Originally by {admin_name}."
    assert by_name["Meine"]["private"] is True
    swap = by_name["Vegan"]["changes"][0]
    assert swap["to_ingredient_id"] == oat["id"] and swap["available"] is True
    assert by_name["Vegan"]["based_on_revision"] == 1

    def without_oat(manifest: dict[str, Any]) -> None:
        del manifest["catalogue"]["ingredients"][oat["id"]]

    report = await _import(exporter, _rewrite(response.content, without_oat))
    dropped = [c for c in report["conflicts"] if c["kind"] == "ingredient"]
    assert len(dropped) == 2
    assert all(c["recipe"] == "Dinkelpalatschinken" for c in dropped)
    new_id = report["recipes"][0]["id"]
    variations = (await exporter.get(f"{WEB}/recipes/{new_id}/variations")).json()
    assert {v["name"]: len(v["changes"]) for v in variations} == {
        "Vegan": 0,
        "Annas": 0,
        "Meine": 1,
    }
