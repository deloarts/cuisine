"""Seed updates: the per-field three-way merge on start-up, the overridden
updates an edit holds back and accepting one."""

from dataclasses import replace

import httpx
import pytest

from src.bootstrap import cookbook_seed
from src.bootstrap import reference_router
from src.bootstrap.cookbook_seed import ensure_reference_data
from src.bootstrap.reference_data import ReferenceData
from src.bootstrap.reference_data import load_reference_data
from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB


def _use(monkeypatch: pytest.MonkeyPatch, data: ReferenceData) -> None:
    monkeypatch.setattr(cookbook_seed, "load_reference_data", lambda: data)
    monkeypatch.setattr(reference_router, "load_reference_data", lambda: data)


def _small() -> ReferenceData:
    """The real units, categories and tags with two ingredients and no
    families or equipment, to keep the test fast."""
    data = load_reference_data()
    potato = data.ingredient("potato")
    celeriac = data.ingredient("celeriac")
    return replace(
        data,
        families=[],
        equipment=[],
        ingredients=[replace(potato, family=None), replace(celeriac, family=None)],
    )


async def _tag(admin: httpx.AsyncClient, english: str) -> dict[str, object]:
    tags = (await admin.get(f"{WEB}/tags", params={"locale": "en-GB"})).json()
    return dict(next(t for t in tags if t["name"] == english))


async def test_untouched_fields_follow_the_seed_and_edits_stay(
    admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _small()
    _use(monkeypatch, data)
    await ensure_reference_data()
    breakfast = await _tag(admin, "Breakfast")
    edited = await admin.put(
        f"{WEB}/tags/{breakfast['id']}",
        headers=CSRF,
        json={
            "kind": "meal",
            "color": breakfast["color"],
            "translations": {"en-GB": {"name": "Breakfast"}, "de-AT": {"name": "Morgenessen"}},
        },
    )
    assert edited.status_code == 200, edited.text
    lunch = await _tag(admin, "Lunch")
    dinner = await _tag(admin, "Dinner")
    assert (await admin.delete(f"{WEB}/tags/{dinner['id']}", headers=CSRF)).status_code == 204

    tags = []
    for tag in data.tags:
        if tag.key == "breakfast":
            tag = replace(tag, names={**tag.names, "de-AT": "Zmorgen"}, color="#112233")
        elif tag.key == "lunch":
            tag = replace(tag, names={**tag.names, "en-GB": "Luncheon"})
        elif tag.key == "dinner":
            tag = replace(tag, names={**tag.names, "en-GB": "Supper"})
        tags.append(tag)
    potato = data.ingredient("potato")
    changed = replace(
        data,
        tags=tags,
        ingredients=[
            replace(potato, allergens=["celery"], season_months=[9, 10]),
            data.ingredient("celeriac"),
        ],
    )
    _use(monkeypatch, changed)
    assert await ensure_reference_data() is True

    after = {
        t["id"]: t for t in (await admin.get(f"{WEB}/tags", params={"locale": "de-AT"})).json()
    }
    assert after[breakfast["id"]]["name"] == "Morgenessen"
    assert after[breakfast["id"]]["color"] == "#112233"
    lunch_now = (await admin.get(f"{WEB}/tags", params={"locale": "en-GB"})).json()
    assert next(t for t in lunch_now if t["id"] == lunch["id"])["name"] == "Luncheon"
    # A deleted row stays deleted.
    assert dinner["id"] not in after
    potato_row = (await admin.get(f"{WEB}/ingredients", params={"search": "Erdapfel"})).json()
    assert potato_row["items"][0]["allergens"] == ["celery"]
    assert potato_row["items"][0]["season_months"] == [9, 10]

    # A second start changes nothing more.
    assert await ensure_reference_data() is False

    updates = (await admin.get(f"{WEB}/admin/reference-updates")).json()
    assert [(u["kind"], u["key"], u["field"]) for u in updates] == [
        ("tag", "breakfast", "names.de-AT")
    ]
    assert updates[0]["current"] == "Morgenessen"
    assert updates[0]["seed"] == "Zmorgen"

    accepted = await admin.post(
        f"{WEB}/admin/reference-updates/accept",
        headers=CSRF,
        json={"kind": "tag", "key": "breakfast", "field": "names.de-AT"},
    )
    assert accepted.status_code == 204
    final = (await admin.get(f"{WEB}/tags", params={"locale": "de-AT"})).json()
    assert next(t for t in final if t["id"] == breakfast["id"])["name"] == "Zmorgen"
    assert (await admin.get(f"{WEB}/admin/reference-updates")).json() == []
    again = await admin.post(
        f"{WEB}/admin/reference-updates/accept",
        headers=CSRF,
        json={"kind": "tag", "key": "breakfast", "field": "names.de-AT"},
    )
    assert again.status_code == 404


async def test_allergen_overrides_come_first(
    admin: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _small()
    _use(monkeypatch, data)
    await ensure_reference_data()
    found = (await admin.get(f"{WEB}/ingredients", params={"search": "Erdapfel"})).json()
    potato = found["items"][0]
    detail = (await admin.get(f"{WEB}/ingredients/{potato['id']}")).json()
    edited = await admin.put(
        f"{WEB}/ingredients/{potato['id']}",
        headers=CSRF,
        json={
            "original_locale": detail["original_locale"],
            "translations": detail["translations"],
            "allergens": ["mustard"],
            "season_months": [1],
            "nutrition": detail["nutrition"],
        },
    )
    assert edited.status_code == 200, edited.text
    seed_potato = data.ingredient("potato")
    _use(
        monkeypatch,
        replace(
            data,
            ingredients=[
                replace(seed_potato, allergens=["celery"], season_months=[2]),
                data.ingredient("celeriac"),
            ],
        ),
    )
    await ensure_reference_data()
    updates = (await admin.get(f"{WEB}/admin/reference-updates")).json()
    assert [u["field"] for u in updates] == ["allergens", "season_months"]
    assert updates[0]["current"] == ["mustard"]
    assert updates[0]["seed"] == ["celery"]


async def test_reading_updates_needs_read_settings(cook: httpx.AsyncClient) -> None:
    assert (await cook.get(f"{WEB}/admin/reference-updates")).status_code == 403
