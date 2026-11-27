"""
USDA FoodData Central, the public domain (CC0) nutrient database of the US
Department of Agriculture. Its generic foods (Foundation and SR Legacy) give
nutrition per 100 g, which maps straight onto an ingredient. Sodium is
reported in milligrams and turned into salt (sodium × 2.5). The extended
nutrients map onto the catalogue in `nutrients.py`; FDC states them in the
catalogue's units except vitamin D in international units (40 IU = 1 µg),
and folate counts as dietary folate equivalents.

API: https://fdc.nal.usda.gov/api-guide. The source line the UI shows is
"Source: USDA FoodData Central".
"""

from typing import Any

import httpx

from src.cookbook.domain.exceptions import NutritionLookupUnavailableError
from src.cookbook.domain.value_objects.nutrients import EXTENDED_NUTRIENTS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.ports.outbound.nutrition_lookup import FoodMatch
from src.platform.infrastructure.logging.logger import log

BASE_URL = "https://api.nal.usda.gov/fdc/v1"
TIMEOUT_SECONDS = 10.0
# Generic foods only by default; branded products describe one product's
# label, not an ingredient.
DATA_TYPES = "Foundation,SR Legacy"

# FoodData Central nutrient ids.
ENERGY_KCAL = (1008, 2047, 2048)
PROTEIN = (1003,)
FAT = (1004,)
SATURATED_FAT = (1258,)
CARBOHYDRATES = (1005,)
SUGAR = (2000, 1063)
FIBRE = (1079,)
SODIUM_MG = (1093,)
VITAMIN_D_IU = 1110
FOLATE_DFE, FOLATE_FOOD, FOLATE_TOTAL, FOLIC_ACID = 1190, 1187, 1177, 1186


def _values(nutrients: list[dict[str, Any]]) -> dict[int, float]:
    """Nutrient id to amount, from either the search or the detail shape."""
    found: dict[int, float] = {}
    for entry in nutrients:
        nutrient = entry.get("nutrient") or {}
        nutrient_id = entry.get("nutrientId", nutrient.get("id"))
        amount = entry.get("value", entry.get("amount"))
        if isinstance(nutrient_id, int) and isinstance(amount, int | float):
            found.setdefault(nutrient_id, float(amount))
    return found


def _first(values: dict[int, float], ids: tuple[int, ...]) -> float | None:
    for nutrient_id in ids:
        if nutrient_id in values:
            return round(values[nutrient_id], 2)
    return None


def parse_nutrition(nutrients: list[dict[str, Any]]) -> Nutrition:
    values = _values(nutrients)
    sodium = _first(values, SODIUM_MG)
    return Nutrition(
        kcal=_first(values, ENERGY_KCAL),
        protein=_first(values, PROTEIN),
        fat=_first(values, FAT),
        saturated_fat=_first(values, SATURATED_FAT),
        carbohydrates=_first(values, CARBOHYDRATES),
        sugar=_first(values, SUGAR),
        fibre=_first(values, FIBRE),
        salt=round(sodium * 2.5 / 1000, 3) if sodium is not None else None,
    )


def _folate_dfe(values: dict[int, float]) -> float | None:
    """FDC's folate DFE, else food folate plus 1.7 times the added folic
    acid, else total folate for a food stated to have no folic acid."""
    if FOLATE_DFE in values:
        return values[FOLATE_DFE]
    folic_acid = values.get(FOLIC_ACID)
    if folic_acid is None:
        return None
    if FOLATE_FOOD in values:
        return values[FOLATE_FOOD] + 1.7 * folic_acid
    if folic_acid == 0 and FOLATE_TOTAL in values:
        return values[FOLATE_TOTAL]
    return None


def parse_extended(nutrients: list[dict[str, Any]]) -> dict[str, float]:
    """The extended nutrients FDC reports for the food; missing ones stay
    absent, never zero."""
    values = _values(nutrients)
    found: dict[str, float] = {}
    for nutrient in EXTENDED_NUTRIENTS:
        if nutrient.key == "folate_ug":
            value = _folate_dfe(values)
        elif nutrient.key == "vitamin_d_ug" and nutrient.usda_nutrient_id not in values:
            iu = values.get(VITAMIN_D_IU)
            value = iu / 40 if iu is not None else None
        else:
            value = values.get(nutrient.usda_nutrient_id)
        if value is not None:
            found[nutrient.key] = round(value, 3)
    return found


def _match(food: dict[str, Any]) -> FoodMatch:
    return FoodMatch(
        fdc_id=int(food["fdcId"]),
        description=str(food.get("description") or ""),
        data_type=str(food.get("dataType") or ""),
        brand=food.get("brandOwner") or food.get("brandName"),
        nutrition=parse_nutrition(list(food.get("foodNutrients") or [])),
        extended_nutrition=parse_extended(list(food.get("foodNutrients") or [])),
    )


class UsdaNutritionLookup:
    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base_url = base_url

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.get(f"{self._base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            log.warning("USDA FoodData Central did not answer: %s", type(exc).__name__)
            raise NutritionLookupUnavailableError(
                "The USDA food database did not answer; try again later."
            ) from exc
        if response.status_code == 404:
            return None
        if response.status_code == 429:
            raise NutritionLookupUnavailableError(
                "The USDA food database refused more requests for now. With DEMO_KEY only a "
                "few lookups per hour are allowed; an administrator can enter a free key."
            )
        if response.status_code >= 400:
            log.warning("USDA FoodData Central answered %s.", response.status_code)
            raise NutritionLookupUnavailableError("The USDA food database refused the lookup.")
        return response.json()

    async def search(self, query: str, *, api_key: str, limit: int) -> list[FoodMatch]:
        data = await self._get(
            "/foods/search",
            {"api_key": api_key, "query": query, "pageSize": limit, "dataType": DATA_TYPES},
        )
        foods = (data or {}).get("foods") or []
        return [_match(f) for f in foods if "fdcId" in f]

    async def get(self, fdc_id: int, *, api_key: str) -> FoodMatch | None:
        data = await self._get(f"/food/{fdc_id}", {"api_key": api_key})
        return _match(data) if data and "fdcId" in data else None
