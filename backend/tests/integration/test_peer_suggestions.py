"""Suggestions from a paired instance's catalogue data: the differences
between what the peer sent for a mapped entry and the local entry, listed
with allergens and diet markers first, accepted or dismissed field by field.

The two-instance setup of test_peer_mirrors.py is reused: "A" shares a
recipe, "B" maps its ingredient to a local one and reads the suggestions."""

from typing import Any

import httpx
import pytest
from sqlalchemy import select

from src.cookbook.adapters.outbound.persistence.models.mirror_models import (
    PeerSuggestionDismissalModel,
)
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.entities.user import User
from tests.integration.conftest import CSRF
from tests.integration.test_peer_mirrors import WEB
from tests.integration.test_peer_mirrors import Mirrors
from tests.integration.test_peer_mirrors import mirrors  # noqa: F401

SUGGESTIONS = f"{WEB}/admin/peer-suggestions"


async def _unit_id(client: httpx.AsyncClient, code: str) -> str:
    units = (await client.get(f"{WEB}/units")).json()
    return str(next(u["id"] for u in units if u["code"] == code))


async def _ingredient(client: httpx.AsyncClient, name: str, **fields: Any) -> str:
    created = await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": name, "plural_name": name}},
            **fields,
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


async def _custom_unit(client: httpx.AsyncClient, code: str) -> str:
    created = await client.post(
        f"{WEB}/units",
        headers=CSRF,
        json={
            "code": code,
            "kind": "count",
            "translations": {
                "de-AT": {"name": "Schöpfer", "plural_name": "Schöpfer", "abbreviation": ""},
                "en-GB": {"name": "scoop", "plural_name": "scoops", "abbreviation": ""},
            },
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def _recipe_body(title: str, ingredient: str, unit: str) -> dict[str, Any]:
    return {
        "original_locale": "de-AT",
        "translations": {"de-AT": {"title": title, "description": "Gut."}},
        "base_servings": 2,
        "steps": [
            {
                "translations": {"de-AT": {"text": "Alles mischen."}},
                "ingredients": [{"ingredient_id": ingredient, "amount": 2, "unit_id": unit}],
            }
        ],
    }


async def _share(m: Mirrors, title: str, ingredient: str, unit: str) -> str:
    body = {
        **_recipe_body(title, ingredient, unit),
        "visibility": "shared",
        "shared_peer_ids": [str(m.b_on_a.public_id)],
    }
    created = await m.a.post(f"{WEB}/recipes", headers=CSRF, json=body)
    assert created.status_code == 201, created.text
    recipe_id = str(created.json()["id"])
    published = await m.a.post(f"{WEB}/recipes/{recipe_id}/publish", headers=CSRF)
    assert published.status_code == 200, published.text
    await m.settle()
    return recipe_id


async def _accept_mapped(m: Mirrors, local_id: str) -> str:
    """Accepts the one waiting recipe, mapping its ingredient to `local_id`;
    answers the ingredient's source id."""
    (item,) = await m.incoming()
    (entry,) = [e for e in item["entries"] if e["kind"] == "ingredient"]
    accepted = await m.accept(
        item["id"],
        [
            {
                "kind": "ingredient",
                "source_id": entry["source_id"],
                "action": "map",
                "target_id": local_id,
            }
        ],
    )
    assert accepted.status_code == 200, accepted.text
    return str(entry["source_id"])


async def _suggestions(m: Mirrors, **params: str) -> list[dict[str, Any]]:
    listed = await m.b.get(SUGGESTIONS, params=params)
    assert listed.status_code == 200, listed.text
    result: list[dict[str, Any]] = listed.json()
    return result


def _fields(group: dict[str, Any]) -> list[str]:
    return [s["field"] for s in group["suggestions"]]


def _post(m: Mirrors, action: str, source_id: str, field: str, kind: str = "ingredient") -> Any:
    return m.b.post(
        f"{SUGGESTIONS}/{action}",
        headers=CSRF,
        json={
            "peer_id": str(m.a_on_b.public_id),
            "kind": kind,
            "source_id": source_id,
            "field": field,
        },
    )


async def _kren(m: Mirrors) -> tuple[str, str, str]:
    """Kren on A with allergens, density, nutrition, an alias and two
    conversions (one to a unit B has no mapping for), shared and mapped to
    a sparser local Kren on B. Answers A's id, B's id and the source id."""
    scoop = await _custom_unit(m.a, "scoop")
    tbsp_a = await _unit_id(m.a, "tbsp")
    kren_a = await _ingredient(
        m.a,
        "Kren",
        aliases={"de-AT": ["Meerrettich"]},
        nutrition={"kcal": 100, "protein": 2},
        density_g_per_ml=1.1,
        conversions=[{"unit_id": tbsp_a, "grams": 15}, {"unit_id": scoop, "grams": 40}],
        allergens=["mustard"],
    )
    kren_b = await _ingredient(
        m.b,
        "Kren",
        aliases={"de-AT": ["Krenwurzel"]},
        nutrition={"kcal": 90, "fat": 1},
    )
    await _share(m, "Krenfleisch", kren_a, await _unit_id(m.a, "g"))
    source_id = await _accept_mapped(m, kren_b)
    return kren_a, kren_b, source_id


async def test_differences_are_listed_with_warnings_first_and_gaps_left_out(m: Mirrors) -> None:
    _, kren_b, source_id = await _kren(m)
    (group,) = await _suggestions(m)
    assert group["kind"] == "ingredient"
    assert group["id"] == kren_b
    assert group["name"] == "Kren"
    assert group["warning"] is True
    fields = _fields(group)
    assert fields[0] == "allergens"
    assert set(fields) == {
        "allergens",
        "aliases.de-AT",
        "conversions",
        "density_g_per_ml",
        "nutrition.kcal",
        "nutrition.protein",
    }
    by_field = {s["field"]: s for s in group["suggestions"]}
    assert by_field["allergens"]["current"] == []
    assert by_field["allergens"]["suggested"] == ["mustard"]
    assert by_field["nutrition.kcal"]["current"] == 90
    assert by_field["nutrition.kcal"]["suggested"] == 100
    # Other names are joined with the local ones, never replaced.
    assert by_field["aliases.de-AT"]["suggested"] == ["Krenwurzel", "Meerrettich"]
    # The unit without a mapping or seed key is left out and named.
    assert by_field["conversions"]["suggested"] == {"tbsp": 15}
    assert by_field["conversions"]["unmapped_units"] == ["scoop"]
    assert by_field["allergens"]["peer"]["id"] == str(m.a_on_b.public_id)
    assert by_field["allergens"]["source_id"] == source_id
    # Filters.
    assert await _suggestions(m, kind="unit") == []
    assert len(await _suggestions(m, peer_id=str(m.a_on_b.public_id), kind="ingredient")) == 1


async def test_accepting_writes_only_that_field(m: Mirrors) -> None:
    _, kren_b, source_id = await _kren(m)
    accepted = await _post(m, "accept", source_id, "density_g_per_ml")
    assert accepted.status_code == 204, accepted.text
    accepted = await _post(m, "accept", source_id, "conversions")
    assert accepted.status_code == 204, accepted.text
    detail = (await m.b.get(f"{WEB}/ingredients/{kren_b}")).json()
    assert detail["density_g_per_ml"] == 1.1
    assert [c["grams"] for c in detail["conversions"]] == [15]
    assert detail["nutrition"]["kcal"] == 90
    assert detail["nutrition"]["fat"] == 1
    assert detail["allergens"] == []
    (group,) = await _suggestions(m)
    assert "density_g_per_ml" not in _fields(group)
    assert "conversions" not in _fields(group)
    assert "nutrition.kcal" in _fields(group)

    accepted = await _post(m, "accept", source_id, "aliases.de-AT")
    assert accepted.status_code == 204, accepted.text
    detail = (await m.b.get(f"{WEB}/ingredients/{kren_b}")).json()
    assert sorted(detail["aliases"]["de-AT"]) == ["Krenwurzel", "Meerrettich"]

    # A field that is no suggestion (any more) answers 404.
    again = await _post(m, "accept", source_id, "density_g_per_ml")
    assert again.status_code == 404
    assert again.json()["code"] == "PeerSuggestionNotFoundError"


async def test_a_taken_name_is_reported(m: Mirrors) -> None:
    _, _, source_id = await _kren(m)
    await _ingredient(m.b, "Meerrettich")
    refused = await _post(m, "accept", source_id, "aliases.de-AT")
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "DuplicateNameError"
    (group,) = await _suggestions(m)
    assert "aliases.de-AT" in _fields(group)


async def _b_user(m: Mirrors, name: str, permissions: list[str]) -> User:
    created = await m.b.post(
        f"{WEB}/users",
        headers=CSRF,
        json={
            "full_name": name.title(),
            "email": f"{name}@example.com",
            "password": "cook-password-1",
            "permissions": permissions,
        },
    )
    assert created.status_code == 201, created.text
    async with m.sessions_b() as db:
        found = await SqlAlchemyUserRepository(db).get_by_email(f"{name}@example.com")
    assert found is not None
    return found


async def test_accepting_needs_the_catalogue_rights_of_the_kind(m: Mirrors) -> None:
    _, _, source_id = await _kren(m)
    resources = await _b_user(m, "resi", ["read:settings", "write:resources"])
    # The settings permissions need two-factor authentication.
    resources.totp_enabled = True
    reader = await _b_user(m, "rudi", ["write:recipes"])

    m.as_user_b(reader)
    assert (await m.b.get(SUGGESTIONS)).status_code == 403

    m.as_user_b(resources)
    assert len(await _suggestions(m)) == 1
    refused = await _post(m, "accept", source_id, "density_g_per_ml")
    assert refused.status_code == 403
    assert (await _post(m, "dismiss", source_id, "density_g_per_ml")).status_code == 403

    m.as_user_b(m.admin_b)
    assert (await _post(m, "accept", source_id, "density_g_per_ml")).status_code == 204


async def test_a_dismissal_holds_until_the_peer_offers_another_value(m: Mirrors) -> None:
    kren_a, _, source_id = await _kren(m)
    dismissed = await _post(m, "dismiss", source_id, "nutrition.kcal")
    assert dismissed.status_code == 204, dismissed.text
    (group,) = await _suggestions(m)
    assert "nutrition.kcal" not in _fields(group)
    async with m.sessions_b() as db:
        rows = (await db.scalars(select(PeerSuggestionDismissalModel))).all()
    assert [(r.kind, r.field) for r in rows] == [("ingredient", "nutrition.kcal")]

    # The source changes the ingredient and the recipe goes out again.
    detail = (await m.a.get(f"{WEB}/ingredients/{kren_a}")).json()
    changed = await m.a.put(
        f"{WEB}/ingredients/{kren_a}",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": "Kren", "plural_name": "Kren"}},
            "aliases": detail["aliases"],
            "nutrition": {"kcal": 120, "protein": 2},
            "density_g_per_ml": 1.1,
            "conversions": [
                {"unit_id": c["unit_id"], "grams": c["grams"]} for c in detail["conversions"]
            ],
            "allergens": ["mustard", "celery"],
        },
    )
    assert changed.status_code == 200, changed.text
    (recipe_id,) = [r["id"] for r in (await m.a.get(f"{WEB}/recipes")).json()["items"]]
    body = {
        **_recipe_body("Krenfleisch neu", kren_a, await _unit_id(m.a, "g")),
        "visibility": "shared",
        "shared_peer_ids": [str(m.b_on_a.public_id)],
    }
    await m.save_a(recipe_id, body)
    await m.settle()

    (group,) = await _suggestions(m)
    by_field = {s["field"]: s for s in group["suggestions"]}
    assert by_field["nutrition.kcal"]["suggested"] == 120
    assert by_field["allergens"]["suggested"] == ["celery", "mustard"]


async def test_an_entry_created_from_the_peer_gets_later_changes(m: Mirrors) -> None:
    kren_a = await _ingredient(m.a, "Kren", nutrition={"kcal": 100}, allergens=["mustard"])
    _, mirror_id = await m.share_and_accept("Krenfleisch", [(kren_a, 20)])
    before = await _suggestions(m)
    assert all("nutrition.kcal" not in _fields(g) for g in before)

    changed = await m.a.put(
        f"{WEB}/ingredients/{kren_a}",
        headers=CSRF,
        json={
            "original_locale": "de-AT",
            "translations": {"de-AT": {"name": "Kren", "plural_name": "Kren"}},
            "nutrition": {"kcal": 130},
            "allergens": ["mustard"],
        },
    )
    assert changed.status_code == 200, changed.text
    (recipe,) = (await m.a.get(f"{WEB}/recipes")).json()["items"]
    body = await m.recipe_body(
        "Krenfleisch",
        [(kren_a, 30)],
        visibility="shared",
        shared_peer_ids=[str(m.b_on_a.public_id)],
    )
    await m.save_a(recipe["id"], body)
    await m.settle()
    assert mirror_id
    (group,) = [g for g in await _suggestions(m) if g["kind"] == "ingredient"]
    kcal = next(s for s in group["suggestions"] if s["field"] == "nutrition.kcal")
    assert kcal["suggested"] == 130


async def test_a_unit_only_conversions_name_can_be_mapped_by_hand(m: Mirrors) -> None:
    _, kren_b, source_id = await _kren(m)
    mappings_url = f"{WEB}/admin/peers/{m.a_on_b.public_id}/mappings"
    mappings = (await m.b.get(mappings_url)).json()
    units = {u["name"]: u for u in mappings if u["kind"] == "unit"}
    # The conversion units get mappings although no line uses them: tbsp by
    # its seed key, the custom scoop left for the administrator.
    tbsp = next(u for u in units.values() if u["matched_by"] == "seed_key" and u["used_by"] == 0)
    assert tbsp["action"] == "map"
    scoop = units["scoop"]
    assert scoop["action"] is None
    assert scoop["target_id"] is None

    schoepfer = await _custom_unit(m.b, "schoepfer")
    mapped = await m.b.put(
        f"{mappings_url}/unit/{scoop['source_id']}",
        headers=CSRF,
        json={"action": "map", "target_id": schoepfer},
    )
    assert mapped.status_code == 200, mapped.text
    assert mapped.json()["target_id"] == schoepfer

    (group,) = await _suggestions(m, kind="ingredient")
    conversions = next(s for s in group["suggestions"] if s["field"] == "conversions")
    assert conversions["suggested"] == {"schoepfer": 40, "tbsp": 15}
    assert conversions["unmapped_units"] == []
    accepted = await _post(m, "accept", source_id, "conversions")
    assert accepted.status_code == 204, accepted.text
    detail = (await m.b.get(f"{WEB}/ingredients/{kren_b}")).json()
    assert sorted(c["grams"] for c in detail["conversions"]) == [15, 40]


async def test_the_list_is_gone_while_peering_is_off(m: Mirrors) -> None:
    async with m.sessions_b() as db:
        await SqlAlchemySettingsRepository(db).save_features(FeatureSettings(peering=False))
        await db.commit()
    assert (await m.b.get(SUGGESTIONS)).status_code == 404
    assert (await _post(m, "dismiss", "x", "allergens")).status_code == 404


async def test_an_unknown_peer_or_entry_answers_404(m: Mirrors) -> None:
    unknown = await m.b.get(SUGGESTIONS, params={"peer_id": "00000000-0000-4000-8000-000000000000"})
    assert unknown.status_code == 404
    missing = await _post(m, "accept", "no-such-entry", "allergens")
    assert missing.status_code == 404
    assert missing.json()["code"] == "PeerMappingNotFoundError"


@pytest.fixture
def m(mirrors: Mirrors) -> Mirrors:  # noqa: F811
    return mirrors
