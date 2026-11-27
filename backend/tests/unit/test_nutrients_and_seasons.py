"""The extended nutrient catalogue, the USDA mapping of extended nutrients
and a recipe's season."""

from datetime import UTC
from datetime import datetime
from typing import Any

import pytest

from src.cookbook.adapters.outbound.external.usda_nutrition_lookup import parse_extended
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.services.seasons import clean_months
from src.cookbook.domain.services.seasons import recipe_season
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrients import clean_extended


def _ingredient(ingredient_id: int, months: list[int]) -> Ingredient:
    now = datetime.now(UTC)
    return Ingredient(
        id=ingredient_id,
        owner_id=None,
        original_locale="de-AT",
        created=now,
        changed=now,
        season_months=months,
    )


def test_the_catalogue_holds_exactly_the_planned_keys() -> None:
    assert set(EXTENDED_KEYS) == {
        "cholesterol_mg", "caffeine_mg", "vitamin_a_ug", "vitamin_b1_mg", "vitamin_b2_mg",
        "vitamin_b6_mg", "vitamin_b12_ug", "folate_ug", "vitamin_c_mg", "vitamin_d_ug",
        "vitamin_e_mg", "vitamin_k_ug", "calcium_mg", "iron_mg", "magnesium_mg",
        "phosphorus_mg", "potassium_mg", "zinc_mg", "iodine_ug", "monounsaturated_fat_g",
        "polyunsaturated_fat_g", "trans_fat_g",
    }  # fmt: skip


def test_clean_extended_orders_drops_unknown_values_and_refuses_bad_keys() -> None:
    assert list(clean_extended({"zinc_mg": 1, "iron_mg": 2, "calcium_mg": None})) == [
        "iron_mg",
        "zinc_mg",
    ]
    with pytest.raises(ValueError, match="vitamin_x"):
        clean_extended({"vitamin_x": 1})
    with pytest.raises(ValueError):
        clean_extended({"iron_mg": -0.1})


def test_usda_extended_values_map_onto_catalogue_keys() -> None:
    nutrients: list[dict[str, Any]] = [
        {"nutrientId": 1162, "value": 19.7},
        {"nutrient": {"id": 1110}, "amount": 40.0},
        {"nutrientId": 1187, "value": 10.0},
        {"nutrientId": 1186, "value": 5.0},
    ]
    assert parse_extended(nutrients) == {
        "vitamin_c_mg": 19.7,
        "folate_ug": 18.5,
        "vitamin_d_ug": 1.0,
    }


def test_a_recipe_is_in_season_when_every_seasonal_ingredient_is() -> None:
    ingredients = {
        1: _ingredient(1, [5, 6, 7]),
        2: _ingredient(2, [6, 7, 8]),
        3: _ingredient(3, []),
    }
    assert recipe_season([1, 2, 3], ingredients) == [6, 7]
    assert recipe_season([3], ingredients) == []
    assert recipe_season([1, 99], ingredients) == [5, 6, 7]


def test_season_months_are_cleaned() -> None:
    assert clean_months([3, 1, 3]) == [1, 3]
    with pytest.raises(ValueError):
        clean_months([0])
