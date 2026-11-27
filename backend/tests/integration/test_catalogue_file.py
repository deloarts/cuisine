"""The catalogue file: the export downloads a `cuisine-catalogue` document
that previews as nothing to do on the instance it came from, the preview
names new entries and the differing fields of matched ones (allergens and
diet markers first), the apply creates new entries active and writes only
the accepted fields, keeps references inside the file, reports taken names,
leaves out the kinds the caller may not write, and refuses unreadable files
with 422."""

import json
from typing import Any

import httpx
import jsonschema
import pytest

from src.bootstrap.cookbook_seed import ensure_reference_data
from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import unit_id
from tests.integration.test_recipe_formats import BACKEND

SCHEMA_V1 = BACKEND / "formats" / "cuisine-catalogue.v1.schema.json"
NEW_CATEGORY = "11111111-1111-4111-8111-111111111111"
NEW_UNIT = "22222222-2222-4222-8222-222222222222"
NEW_INGREDIENT = "33333333-3333-4333-8333-333333333333"
NEW_FAMILY = "44444444-4444-4444-8444-444444444444"


async def _export(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get(f"{WEB}/admin/catalogue/export")
    assert response.status_code == 200, response.text
    document: dict[str, Any] = response.json()
    return document


async def _preview(
    client: httpx.AsyncClient, document: dict[str, Any] | bytes, status: int = 200
) -> dict[str, Any]:
    data = document if isinstance(document, bytes) else json.dumps(document).encode()
    response = await client.post(
        f"{WEB}/admin/catalogue/import/preview",
        headers=CSRF,
        files={"file": ("catalogue.json", data, "application/json")},
    )
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    return body


async def _apply(
    client: httpx.AsyncClient, document: dict[str, Any], accept: list[str], status: int = 200
) -> dict[str, Any]:
    response = await client.post(
        f"{WEB}/admin/catalogue/import",
        headers=CSRF,
        files={"file": ("catalogue.json", json.dumps(document).encode(), "application/json")},
        data={"accept": accept},
    )
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    return body


def _source_id(document: dict[str, Any], kind: str, english: str) -> str:
    for source_id, entry in document[kind].items():
        names = entry["names"]
        name = names.get("en-GB") or names.get("de-AT")
        if isinstance(name, dict):
            name = name["name"]
        if name == english:
            return str(source_id)
    raise AssertionError(f"{english} is not in {kind}")


def _kinds(preview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {k["kind"]: k for k in preview["kinds"]}


async def test_an_export_previews_as_nothing_to_do_on_its_own_instance(
    admin: httpx.AsyncClient,
) -> None:
    await ensure_reference_data()
    flour = await make_ingredient(
        admin, "Grünkernschrot", english="Green spelt grits", allergens=["gluten"], kcal=340
    )
    assert flour["status"] == "active"
    response = await admin.get(f"{WEB}/admin/catalogue/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"].startswith("attachment;")
    assert "cuisine-catalogue-" in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    document = response.json()
    jsonschema.validate(document, json.loads(SCHEMA_V1.read_text()))
    assert document["format"] == "cuisine-catalogue"
    assert len(document["ingredients"]) > 400
    assert flour["id"] in document["ingredients"]

    preview = await _preview(admin, document)
    assert preview["entries"] == []
    assert preview["conflicts"] == []
    for summary in preview["kinds"]:
        assert summary["new"] == 0, summary
        assert summary["different"] == 0, summary
        assert summary["skipped"] is False
    assert _kinds(preview)["ingredient"]["matched"] == len(document["ingredients"])

    report = await _apply(admin, document, [])
    assert report == {"created": [], "updated": [], "skipped": [], "conflicts": []}


async def _changed_document(admin: httpx.AsyncClient) -> dict[str, Any]:
    """An export of a small catalogue with a changed ingredient and tag, and
    a new ingredient that names a new category and family and converts a new
    unit, all by their source ids in the file."""
    await make_ingredient(admin, "Erdnuss", english="Peanut", allergens=["peanuts"], kcal=560)
    document = await _export(admin)
    peanut = _source_id(document, "ingredients", "Peanut")
    entry = document["ingredients"][peanut]
    entry["allergens"] = ["nuts", "peanuts"]
    entry["diet_markers"] = ["honey"]
    entry["nutrition"]["kcal"] = 600
    entry["aliases"] = {"de-AT": ["Aschanti"]}
    tag = next(iter(document["tags"]))
    document["tags"][tag]["color"] = "#123456"
    document["categories"][NEW_CATEGORY] = {"names": {"en-GB": "Pantry", "de-AT": "Vorrat"}}
    document["families"][NEW_FAMILY] = {"names": {"en-GB": "Pulses", "de-AT": "Hülsenfrüchte"}}
    document["units"][NEW_UNIT] = {
        "code": "scoop",
        "kind": "count",
        "names": {"en-GB": "scoop"},
        "plural_names": {"en-GB": "scoops"},
    }
    document["ingredients"][NEW_INGREDIENT] = {
        "original_locale": "en-GB",
        "names": {"en-GB": {"name": "Lupin flour"}, "de-AT": {"name": "Lupinenmehl"}},
        "category": {"id": NEW_CATEGORY, "names": {"en-GB": "Pantry"}},
        "family": {"id": NEW_FAMILY, "names": {"en-GB": "Pulses"}},
        "nutrition": {"kcal": 330},
        "conversions": [{"unit_id": NEW_UNIT, "grams": 30}],
        "allergens": ["lupin", "glitter"],
    }
    return document


async def test_the_preview_names_new_entries_and_differing_fields(
    admin: httpx.AsyncClient, resources: None
) -> None:
    document = await _changed_document(admin)
    peanut = _source_id(document, "ingredients", "Peanut")
    preview = await _preview(admin, document)

    kinds = _kinds(preview)
    assert kinds["ingredient"]["new"] == 1
    assert kinds["ingredient"]["different"] == 1
    assert kinds["category"]["new"] == 1
    assert kinds["unit"]["new"] == 1
    assert kinds["tag"]["different"] == 1

    first = preview["entries"][0]
    assert first["source_id"] == peanut
    assert first["local_id"] is not None
    fields = [d["field"] for d in first["differences"]]
    assert fields[:2] == ["allergens", "diet_markers"]
    assert set(fields) == {"allergens", "diet_markers", "nutrition.kcal", "aliases.de-AT"}
    allergens = first["differences"][0]
    assert allergens["current"] == ["peanuts"]
    assert allergens["incoming"] == ["nuts", "peanuts"]

    new = {(e["kind"], e["name"]) for e in preview["entries"] if e["local_id"] is None}
    assert new == {
        ("ingredient", "Lupin flour"),
        ("category", "Pantry"),
        ("family", "Pulses"),
        ("unit", "scoop"),
    }
    assert [c["name"] for c in preview["conflicts"]] == ["Lupin flour"]
    assert "glitter" in preview["conflicts"][0]["detail"]

    # The preview writes nothing.
    again = await _preview(admin, document)
    assert _kinds(again)["ingredient"]["new"] == 1


async def test_the_apply_creates_active_entries_and_writes_only_accepted_fields(
    admin: httpx.AsyncClient, resources: None
) -> None:
    document = await _changed_document(admin)
    peanut = _source_id(document, "ingredients", "Peanut")
    report = await _apply(
        admin,
        document,
        [f"ingredient:{peanut}:allergens", f"ingredient:{peanut}:aliases.de-AT"],
    )
    assert report["skipped"] == []
    assert [(u["kind"], u["fields"]) for u in report["updated"]] == [
        ("ingredient", ["allergens", "aliases.de-AT"])
    ]
    created = {c["kind"]: c for c in report["created"]}
    assert set(created) == {"category", "family", "unit", "ingredient"}

    local_peanut = report["updated"][0]["id"]
    detail = (await admin.get(f"{WEB}/ingredients/{local_peanut}")).json()
    assert detail["allergens"] == ["nuts", "peanuts"]
    assert detail["aliases"] == {"de-AT": ["Aschanti"]}
    assert detail["nutrition"]["kcal"] == 560
    assert detail["diet_markers"] == []

    lupin = (await admin.get(f"{WEB}/ingredients/{created['ingredient']['id']}")).json()
    assert lupin["status"] == "active"
    assert lupin["allergens"] == ["lupin"]
    assert lupin["category"]["id"] == created["category"]["id"]
    assert lupin["family"]["id"] == created["family"]["id"]
    assert [c["unit_id"] for c in lupin["conversions"]] == [created["unit"]["id"]]
    assert await unit_id(admin, "scoop") == created["unit"]["id"]

    # Applying the same file again finds the created entries and leaves the
    # differences that were not accepted.
    preview = await _preview(admin, document)
    kinds = _kinds(preview)
    assert all(k["new"] == 0 for k in kinds.values())
    left = next(e for e in preview["entries"] if e["source_id"] == peanut)
    assert {d["field"] for d in left["differences"]} == {"diet_markers", "nutrition.kcal"}


async def test_a_taken_name_is_reported_and_not_written(
    admin: httpx.AsyncClient, resources: None
) -> None:
    await make_ingredient(admin, "Zucker", english="Sugar")
    await make_ingredient(admin, "Salz", english="Salt", kcal=0)
    document = await _export(admin)
    salt = _source_id(document, "ingredients", "Salt")
    document["ingredients"][salt]["names"]["en-GB"] = {"name": "Sugar", "plural_name": "Sugars"}
    document["ingredients"][salt]["nutrition"]["kcal"] = 1
    # A new family whose name an ingredient holds is not created.
    document["families"][NEW_FAMILY] = {"names": {"de-AT": "Zucker"}}
    report = await _apply(
        admin, document, [f"ingredient:{salt}:names.en-GB", f"ingredient:{salt}:nutrition.kcal"]
    )
    assert report["created"] == []
    assert [(u["name"], u["fields"]) for u in report["updated"]] == [("Salt", ["nutrition.kcal"])]
    conflicts = {(c["kind"], c["name"]) for c in report["conflicts"]}
    assert conflicts == {("ingredient", "Salt"), ("family", "Zucker")}
    detail = (await admin.get(f"{WEB}/ingredients/{report['updated'][0]['id']}")).json()
    assert detail["translations"]["en-GB"]["name"] == "Salt"
    assert detail["nutrition"]["kcal"] == 1


async def test_kinds_the_caller_may_not_write_are_skipped(
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    other_client: httpx.AsyncClient,
    resources: None,
) -> None:
    document = await _changed_document(admin)
    await make_user("keeper", permissions=["write:resources"])
    await login(other_client, "keeper@example.com", "cook-password-1")
    assert (await other_client.get(f"{WEB}/admin/catalogue/export")).status_code == 200
    preview = await _preview(other_client, document)
    kinds = _kinds(preview)
    assert kinds["ingredient"]["skipped"] is True
    assert kinds["ingredient"]["new"] == 1
    assert all(e["kind"] != "ingredient" for e in preview["entries"])
    report = await _apply(other_client, document, [])
    assert report["skipped"] == ["ingredient"]
    assert {c["kind"] for c in report["created"]} == {"category", "family", "unit"}
    found = (await admin.get(f"{WEB}/ingredients", params={"search": "Lupin"})).json()
    assert found["total"] == 0


@pytest.mark.parametrize("permissions", [[], ["write:recipes", "write:ingredients"]])
async def test_the_catalogue_file_needs_catalogue_rights(
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    other_client: httpx.AsyncClient,
    resources: None,
    permissions: list[str],
) -> None:
    document = await _export(admin)
    await make_user("cook", permissions=permissions)
    await login(other_client, "cook@example.com", "cook-password-1")
    assert (await other_client.get(f"{WEB}/admin/catalogue/export")).status_code == 403
    await _preview(other_client, document, status=403)
    await _apply(other_client, document, [], status=403)


async def test_unreadable_files_answer_422(admin: httpx.AsyncClient, resources: None) -> None:
    document = await _export(admin)
    body = await _preview(admin, b"not json", status=422)
    assert body["code"] == "CatalogueFileError"
    await _preview(admin, {**document, "format": "cuisine-recipes"}, status=422)
    newer = await _preview(admin, {**document, "version": 2}, status=422)
    assert "version 2" in newer["detail"]
    await _preview(admin, {**document, "units": {"x": {"names": {}}}}, status=422)
    await _apply(admin, document, ["ingredient-only"], status=422)
    await _apply(admin, document, ["spice:abc:names.de-AT"], status=422)
