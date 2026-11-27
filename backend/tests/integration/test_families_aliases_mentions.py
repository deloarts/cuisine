"""Ingredient families, aliases, the shared name namespace, near duplicates
and ingredient mentions in step text."""

from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.conftest import MakeUser
from tests.integration.conftest import login
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import grant_health_data
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import unit_id


async def _family(admin: httpx.AsyncClient, de: str, en: str) -> dict[str, Any]:
    created = await admin.post(
        f"{WEB}/ingredient-families",
        headers=CSRF,
        json={"translations": {"de-AT": {"name": de}, "en-GB": {"name": en}}},
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


async def _ingredient(client: httpx.AsyncClient, name: str, **extra: Any) -> httpx.Response:
    return await client.post(
        f"{WEB}/ingredients",
        headers=CSRF,
        json={"original_locale": "de-AT", "translations": {"de-AT": {"name": name}}, **extra},
    )


async def test_aliases_are_found_and_unique(cook: httpx.AsyncClient) -> None:
    created = await _ingredient(cook, "Paradeiser", aliases={"de-AT": ["Tomate", "Tomaten"]})
    assert created.status_code == 201, created.text
    assert created.json()["aliases"] == {"de-AT": ["Tomate", "Tomaten"]}
    found = (await cook.get(f"{WEB}/ingredients", params={"search": "tomate"})).json()
    assert [i["name"] for i in found["items"]] == ["Paradeiser"]
    taken = await _ingredient(cook, "Tomäte")
    assert taken.status_code == 409
    assert taken.json()["existing_name"] == "Paradeiser"
    assert taken.json()["existing_id"] == created.json()["id"]
    alias_taken = await _ingredient(cook, "Gurke", aliases={"de-AT": ["  paradeiser "]})
    assert alias_taken.status_code == 409


async def test_near_duplicates_suggest_existing_ingredients(cook: httpx.AsyncClient) -> None:
    await _ingredient(cook, "Erdapfel", aliases={"de-AT": ["Kartoffel"]})
    # Diacritics never count, so "Erdäpfel" is the same name; a plural
    # ending makes a near duplicate.
    same = (await cook.get(f"{WEB}/ingredients/duplicates", params={"name": "Erdäpfel"})).json()
    assert [(c["name"], c["exact"]) for c in same] == [("Erdapfel", True)]
    near = (await cook.get(f"{WEB}/ingredients/duplicates", params={"name": "Erdäpfeln"})).json()
    assert [(c["name"], c["exact"]) for c in near] == [("Erdapfel", False)]
    typo = (await cook.get(f"{WEB}/ingredients/duplicates", params={"name": "Kartofel"})).json()
    assert typo[0]["matched"] == "Kartoffel"
    exact = (await cook.get(f"{WEB}/ingredients/duplicates", params={"name": "KARTOFFEL"})).json()
    assert exact[0]["exact"] is True
    none = (await cook.get(f"{WEB}/ingredients/duplicates", params={"name": "Zucchini"})).json()
    assert none == []


async def test_families_group_and_restrict(
    cook: httpx.AsyncClient,
    admin: httpx.AsyncClient,
    make_user: MakeUser,
    client: httpx.AsyncClient,
) -> None:
    tomatoes = await _family(admin, "Paradeiser", "Tomatoes")
    fresh = (await _ingredient(cook, "Paradeiser", family_id=tomatoes["id"])).json()
    canned = (await _ingredient(cook, "Dosentomaten", family_id=tomatoes["id"])).json()
    await _ingredient(cook, "Gurke")
    listed = (await cook.get(f"{WEB}/ingredients", params={"family_id": tomatoes["id"]})).json()
    assert {i["name"] for i in listed["items"]} == {"Paradeiser", "Dosentomaten"}
    assert fresh["family"]["name"] == "Tomatoes"
    # A family name may not take an unrelated ingredient's name.
    clash = await admin.post(
        f"{WEB}/ingredient-families",
        headers=CSRF,
        json={"translations": {"de-AT": {"name": "Gurke"}}},
    )
    assert clash.status_code == 409

    g = await unit_id(cook, "g")
    created = await cook.post(
        f"{WEB}/recipes",
        headers=CSRF,
        json=recipe_payload(
            "Sugo", [("Kochen", [{"ingredient_id": canned["id"], "amount": 400, "unit_id": g}])]
        ),
    )
    await cook.post(f"{WEB}/recipes/{created.json()['id']}/publish", headers=CSRF)
    await make_user("sensitive")
    await login(client, "sensitive@example.com", "cook-password-1")
    await grant_health_data(client)
    restriction = await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "intolerance", "family_id": tomatoes["id"]},
    )
    assert restriction.status_code == 201
    assert restriction.json()["family_name"] == "Tomatoes"
    detail = (await client.get(f"{WEB}/recipes/{created.json()['id']}")).json()
    assert detail["has_warning"] is True
    assert detail["warnings"][0]["family_id"] == tomatoes["id"]


async def test_merge_keeps_the_source_names_as_aliases(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    target = (await _ingredient(cook, "Topfen")).json()
    source = (await _ingredient(cook, "Quark")).json()
    merged = await admin.post(
        f"{WEB}/ingredients/{source['id']}/merge", headers=CSRF, json={"into_id": target["id"]}
    )
    assert merged.status_code == 200, merged.text
    assert "Quark" in merged.json()["aliases"]["de-AT"]
    found = (await cook.get(f"{WEB}/ingredients", params={"search": "quark"})).json()
    assert [i["name"] for i in found["items"]] == ["Topfen"]


async def test_restriction_by_alias_and_private_origin(
    cook: httpx.AsyncClient, make_user: MakeUser, client: httpx.AsyncClient
) -> None:
    sahne = (await _ingredient(cook, "Schlagobers", aliases={"de-AT": ["Sahne"]})).json()
    await make_user("reader")
    await login(client, "reader@example.com", "cook-password-1")
    await grant_health_data(client)
    by_alias = await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "intolerance", "ingredient_name": "sahne"},
    )
    assert by_alias.json()["ingredient_id"] == sahne["id"]
    typed = await client.post(
        f"{WEB}/users/me/food-restrictions",
        headers=CSRF,
        json={"kind": "intolerance", "ingredient_name": "Kiwano"},
    )
    draft = (await cook.get(f"{WEB}/ingredients/{typed.json()['ingredient_id']}")).json()
    other = (await _ingredient(cook, "Physalis")).json()
    # The draft looks like any ownerless draft: no owner, no origin field.
    assert draft["owner"] is None and draft["status"] == "draft"
    assert set(draft) == set((await cook.get(f"{WEB}/ingredients/{other['id']}")).json())
    assert "created_via" not in draft and "restriction" not in str(draft).lower()


async def test_mentions_must_point_at_the_steps_lines(cook: httpx.AsyncClient) -> None:
    g = await unit_id(cook, "g")
    flour = (await _ingredient(cook, "Mehl")).json()
    salt = (await _ingredient(cook, "Salz")).json()
    good = recipe_payload(
        "Teig",
        [
            (
                f"@[Mehl](ingredient:{flour['id']}) **gut** sieben",
                [{"ingredient_id": flour["id"], "amount": 200, "unit_id": g}],
            )
        ],
        translations={
            "de-AT": {
                "title": "Teig",
                "description": f"Mit @[Mehl](ingredient:{flour['id']}) und *Liebe*.",
            }
        },
    )
    created = await cook.post(f"{WEB}/recipes", headers=CSRF, json=good)
    assert created.status_code == 201, created.text
    summary = (await cook.get(f"{WEB}/recipes", params={"status": "drafts"})).json()["items"][0]
    assert summary["description_text"] == "Mit Mehl und Liebe."
    bad = recipe_payload(
        "Brot",
        [
            (
                f"@[Salz](ingredient:{salt['id']}) dazu",
                [{"ingredient_id": flour["id"], "amount": 200, "unit_id": g}],
            )
        ],
    )
    refused = await cook.post(f"{WEB}/recipes", headers=CSRF, json=bad)
    assert refused.status_code == 422
    assert "Salz" in refused.json()["detail"]
