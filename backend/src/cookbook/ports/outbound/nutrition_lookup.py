"""Looking up nutrition in a public food database (USDA FoodData Central)."""

from dataclasses import dataclass
from dataclasses import field
from typing import Protocol

from src.cookbook.domain.value_objects.nutrition import Nutrition


@dataclass(frozen=True)
class FoodMatch:
    fdc_id: int
    description: str
    data_type: str
    brand: str | None
    nutrition: Nutrition
    # Extended nutrients per 100 g by catalogue key, as far as known.
    extended_nutrition: dict[str, float] = field(default_factory=dict)


class INutritionLookup(Protocol):
    async def search(self, query: str, *, api_key: str, limit: int) -> list[FoodMatch]: ...
    async def get(self, fdc_id: int, *, api_key: str) -> FoodMatch | None: ...
