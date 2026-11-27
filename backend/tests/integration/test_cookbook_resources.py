"""Units, tags and ingredient categories."""

import httpx

from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import unit_id


async def test_seeded_resources_read_in_the_viewers_language(
    cook: httpx.AsyncClient,
) -> None:
    units = (await cook.get(f"{WEB}/units", params={"locale": "de-AT"})).json()
    tbsp = next(u for u in units if u["code"] == "tbsp")
    assert tbsp["abbreviation"] == "EL"
    assert tbsp["translations"]["en-GB"]["abbreviation"] == "tbsp"
    tags = (await cook.get(f"{WEB}/tags", params={"locale": "en-GB"})).json()
    assert "Dinner" in {t["name"] for t in tags}
    categories = (await cook.get(f"{WEB}/ingredient-categories")).json()
    assert len(categories) >= 10


async def test_seed_is_idempotent(cook: httpx.AsyncClient) -> None:
    from src.bootstrap.cookbook_seed import ensure_reference_data

    before = len((await cook.get(f"{WEB}/tags")).json())
    assert await ensure_reference_data(ingredients=False) is False
    assert len((await cook.get(f"{WEB}/tags")).json()) == before


async def test_changing_resources_needs_write_resources(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    body = {"kind": "meal", "translations": {"de-AT": {"name": "Test tag"}}}
    assert (await cook.post(f"{WEB}/tags", headers=CSRF, json=body)).status_code == 403
    created = await admin.post(f"{WEB}/tags", headers=CSRF, json=body)
    assert created.status_code == 201
    assert created.json()["name"] == "Test tag"
    deleted = await admin.delete(f"{WEB}/tags/{created.json()['id']}", headers=CSRF)
    assert deleted.status_code == 204


async def test_unit_codes_are_unique_and_used_units_stay(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient
) -> None:
    duplicate = await admin.post(
        f"{WEB}/units",
        headers=CSRF,
        json={"code": "g", "kind": "mass", "to_base": 1, "translations": {"de-AT": {"name": "x"}}},
    )
    assert duplicate.status_code == 409
    piece = await unit_id(cook, "piece")
    await make_ingredient(cook, "Ei", conversions=[{"unit_id": piece, "grams": 55}])
    in_use = await admin.delete(f"{WEB}/units/{piece}", headers=CSRF)
    assert in_use.status_code == 409


async def test_mass_units_need_a_factor(admin: httpx.AsyncClient, resources: None) -> None:
    refused = await admin.post(
        f"{WEB}/units",
        headers=CSRF,
        json={"code": "stone", "kind": "mass", "translations": {"en-GB": {"name": "stone"}}},
    )
    assert refused.status_code == 422
