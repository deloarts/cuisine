"""Search text containing `%` or `_` matches those characters literally in
recipe, ingredient and equipment searches, instead of acting as a LIKE
wildcard."""

import httpx
import pytest

from src.cookbook.adapters.outbound.persistence.repositories._like import contains_pattern
from tests.integration.conftest import CSRF
from tests.integration.cookbook_helpers import WEB
from tests.integration.cookbook_helpers import make_ingredient
from tests.integration.cookbook_helpers import make_recipe


def test_pattern_escapes_backslash_percent_and_underscore() -> None:
    assert contains_pattern("  A%b_c\\d ") == "%a\\%b\\_c\\\\d%"


@pytest.mark.parametrize(("wildcard", "literal"), [("%", "50% Roggen"), ("_", "Roggen_Mehl")])
async def test_ingredient_search_matches_wildcards_literally(
    cook: httpx.AsyncClient, wildcard: str, literal: str
) -> None:
    await make_ingredient(cook, literal)
    await make_ingredient(cook, "Weizenmehl")
    found = (await cook.get(f"{WEB}/ingredients", params={"search": wildcard})).json()
    assert [i["name"] for i in found["items"]] == [literal]


@pytest.mark.parametrize(("wildcard", "literal"), [("%", "Sieb 50%"), ("_", "Sieb_fein")])
async def test_equipment_search_matches_wildcards_literally(
    admin: httpx.AsyncClient, cook: httpx.AsyncClient, wildcard: str, literal: str
) -> None:
    for name in (literal, "Schneebesen"):
        created = await admin.post(
            f"{WEB}/equipment",
            headers=CSRF,
            json={"kind": "utensil", "translations": {"de-AT": {"name": name}}},
        )
        assert created.status_code == 201, created.text
    found = (await cook.get(f"{WEB}/equipment", params={"search": wildcard})).json()
    assert [e["name"] for e in found] == [literal]


@pytest.mark.parametrize(("wildcard", "literal"), [("%", "Brot 100%"), ("_", "Brot_Roggen")])
async def test_recipe_search_matches_wildcards_literally(
    cook: httpx.AsyncClient, wildcard: str, literal: str
) -> None:
    await make_recipe(cook, literal, [("Backen", [])])
    await make_recipe(cook, "Kuchen", [("Backen", [])])
    found = (await cook.get(f"{WEB}/recipes", params={"search": wildcard})).json()
    assert found["total"] == 1
    assert found["items"][0]["title"] == literal
