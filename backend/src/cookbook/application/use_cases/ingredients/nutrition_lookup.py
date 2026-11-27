"""Searching USDA FoodData Central for nutrition to prefill an ingredient.
Switched on and keyed in the integration settings."""

from src.cookbook.domain.exceptions import NutritionLookupUnavailableError
from src.cookbook.ports.outbound.nutrition_lookup import FoodMatch
from src.cookbook.ports.outbound.nutrition_lookup import INutritionLookup
from src.platform.domain.exceptions import InvalidInputError
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository

MAX_RESULTS = 25


class LookupNutrition:
    def __init__(self, *, settings_repo: ISettingsRepository, lookup: INutritionLookup) -> None:
        self._settings = settings_repo
        self._lookup = lookup

    async def _key(self) -> str:
        settings = await self._settings.get_integrations()
        if not settings.usda_enabled or not settings.usda_api_key:
            raise NutritionLookupUnavailableError("The USDA lookup is switched off.")
        return settings.usda_api_key

    async def search(self, query: str, *, limit: int = 10) -> list[FoodMatch]:
        cleaned = query.strip()
        if len(cleaned) < 2:
            raise InvalidInputError("Search for at least two characters.")
        return await self._lookup.search(
            cleaned, api_key=await self._key(), limit=min(max(limit, 1), MAX_RESULTS)
        )

    async def get(self, fdc_id: int) -> FoodMatch | None:
        return await self._lookup.get(fdc_id, api_key=await self._key())
