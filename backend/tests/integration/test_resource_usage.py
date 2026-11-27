"""How often resources and ingredients are used: `/resources/usage` for the
resources page and `usage_count` on the ingredient list, counting only the
recipes the viewer may see, each recipe once, and filtering and sorting the
ingredient list by it."""

from typing import Any

import httpx

from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe
from tests.integration.cookbook_helpers import recipe_payload
from tests.integration.cookbook_helpers import tag_id
from tests.integration.cookbook_helpers import unit_id


def _counts(usage: dict[str, Any], kind: str) -> dict[str, int]:
    return {entry["id"]: entry["usage_count"] for entry in usage[kind]}


async def _usage(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.get(f"{WEB}/resources/usage")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _equipment(admin: httpx.AsyncClient, name: str) -> dict[str, Any]:
    created = await admin.post(
        f"{WEB}/equipment",
        headers=CSRF,
        json={"kind": "utensil", "translations": {"de-AT": {"name": name}}},
    )
    assert created.status_code == 201, created.text
    body: dict[str, Any] = created.json()
    return body


async def test_resources_count_each_visible_recipe_once(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient, user_choice_privacy: None
) -> None:
    flour = await make_ingredient(cook, "Mehl")
    sugar = await make_ingredient(cook, "Zucker")
    g = await unit_id(cook, "g")
    dessert = await tag_id(cook, "Dessert")
    whisk = await _equipment(admin, "Schneebesen")
    # Grams twice in the steps and once in the declared list, the whisk in
    # two steps: one recipe each.
    await make_recipe(
        cook,
        "Kuchen",
        [
            ("Mischen.", [{"ingredient_id": flour["id"], "amount": 100, "unit_id": g}]),
            ("Süßen.", [{"ingredient_id": sugar["id"], "amount": 50, "unit_id": g}]),
        ],
        tag_ids=[dessert],
        ingredients=[{"ingredient_id": flour["id"], "amount": 200, "unit_id": g}],
    )
    payload = recipe_payload("Schnee", [])
    payload["steps"] = [
        {"translations": {"de-AT": {"text": text}}, "equipment": [{"equipment_id": whisk["id"]}]}
        for text in ("Schlagen.", "Nochmals schlagen.")
    ]
    created = await cook.post(f"{WEB}/recipes", headers=CSRF, json=payload)
    assert created.status_code == 201, created.text
    published = await cook.post(f"{WEB}/recipes/{created.json()['id']}/publish", headers=CSRF)
    assert published.status_code == 200, published.text
    # The administrator's private recipe is theirs alone to count.
    await make_recipe(
        admin,
        "Geheim",
        [("Wiegen.", [{"ingredient_id": flour["id"], "amount": 10, "unit_id": g}])],
        tag_ids=[dessert],
        visibility="private",
    )

    seen_by_cook = await _usage(cook)
    assert _counts(seen_by_cook, "units")[g] == 1
    assert _counts(seen_by_cook, "tags")[dessert] == 1
    assert _counts(seen_by_cook, "equipment")[whisk["id"]] == 1
    assert _counts(seen_by_cook, "units")[await unit_id(cook, "ml")] == 0

    seen_by_admin = await _usage(admin)
    assert _counts(seen_by_admin, "units")[g] == 2
    assert _counts(seen_by_admin, "tags")[dessert] == 2


async def test_a_unit_counts_the_recipes_whose_yield_uses_it(
    cook: httpx.AsyncClient, user_choice_privacy: None
) -> None:
    flour = await make_ingredient(cook, "Mehl")
    g = await unit_id(cook, "g")
    litre = await unit_id(cook, "l")
    await make_recipe(cook, "Suppe", [("Kochen.", [])], yield_amount=2, yield_unit_id=litre)
    # Yield and step line in the same unit: still one recipe.
    await make_recipe(
        cook,
        "Teig",
        [("Kneten.", [{"ingredient_id": flour["id"], "amount": 500, "unit_id": g}])],
        yield_amount=800,
        yield_unit_id=g,
    )

    usage = await _usage(cook)
    assert _counts(usage, "units")[litre] == 1
    assert _counts(usage, "units")[g] == 1


async def test_categories_and_families_count_their_ingredients(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient
) -> None:
    categories = (await cook.get(f"{WEB}/ingredient-categories")).json()
    category = categories[0]["id"]
    family = await admin.post(
        f"{WEB}/ingredient-families",
        headers=CSRF,
        json={"translations": {"de-AT": {"name": "Zitrusfrüchte"}}},
    )
    assert family.status_code == 201, family.text
    family_id = family.json()["id"]
    for name in ("Zitrone", "Limette"):
        created = await cook.post(
            f"{WEB}/ingredients",
            headers=CSRF,
            json={
                "original_locale": "de-AT",
                "translations": {"de-AT": {"name": name}},
                "category_id": category,
                "family_id": family_id,
            },
        )
        assert created.status_code == 201, created.text

    usage = await _usage(cook)
    assert _counts(usage, "categories")[category] == 2
    assert _counts(usage, "families")[family_id] == 2
    assert all(n == 0 for i, n in _counts(usage, "categories").items() if i != category)


async def test_the_ingredient_list_counts_filters_and_sorts_by_usage(
    cook: httpx.AsyncClient, admin: httpx.AsyncClient, user_choice_privacy: None
) -> None:
    apple = await make_ingredient(cook, "Apfel")
    butter = await make_ingredient(cook, "Butter")
    cream = await make_ingredient(cook, "Rahm")
    g = await unit_id(cook, "g")

    def line(ingredient: dict[str, Any]) -> dict[str, Any]:
        return {"ingredient_id": ingredient["id"], "amount": 10, "unit_id": g}

    # Butter in two recipes, once only in a declared list; the apple twice in
    # one recipe; the cream only in the administrator's private recipe.
    await make_recipe(
        cook, "Strudel", [("Füllen.", [line(apple), line(butter)]), ("Mehr.", [line(apple)])]
    )
    await make_recipe(cook, "Brösel", [("Rösten.", [])], ingredients=[line(butter)])
    await make_recipe(admin, "Geheim", [("Schlagen.", [line(cream)])], visibility="private")

    def counts(page: dict[str, Any]) -> list[tuple[str, int]]:
        return [(item["name"], item["usage_count"]) for item in page["items"]]

    listed = (await cook.get(f"{WEB}/ingredients")).json()
    assert counts(listed) == [("Apfel", 1), ("Butter", 2), ("Rahm", 0)]
    assert dict(counts((await admin.get(f"{WEB}/ingredients")).json()))["Rahm"] == 1

    by_usage = (
        await cook.get(f"{WEB}/ingredients", params={"sort": "usage", "order": "desc"})
    ).json()
    assert counts(by_usage) == [("Butter", 2), ("Apfel", 1), ("Rahm", 0)]
    ascending = (await cook.get(f"{WEB}/ingredients", params={"sort": "usage"})).json()
    assert counts(ascending) == [("Rahm", 0), ("Apfel", 1), ("Butter", 2)]
    by_name = (
        await cook.get(f"{WEB}/ingredients", params={"sort": "name", "order": "desc"})
    ).json()
    assert [name for name, _ in counts(by_name)] == ["Rahm", "Butter", "Apfel"]

    used = (await cook.get(f"{WEB}/ingredients", params={"min_usage": 1})).json()
    assert counts(used) == [("Apfel", 1), ("Butter", 2)]
    assert used["total"] == 2
    unused = (await cook.get(f"{WEB}/ingredients", params={"max_usage": 0})).json()
    assert counts(unused) == [("Rahm", 0)]
    paged = (
        await cook.get(
            f"{WEB}/ingredients",
            params={"sort": "usage", "order": "desc", "limit": 1, "offset": 1},
        )
    ).json()
    assert counts(paged) == [("Apfel", 1)] and paged["total"] == 3
