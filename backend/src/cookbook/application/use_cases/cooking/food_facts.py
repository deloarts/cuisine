"""
The food fact of the day for the start page (domain/services/food_facts.py).
A fact is shown only while its ingredient is an active catalogue entry, so a
fact about an ingredient that is archived or missing on this instance gives
way to the next one in the order.
"""

from dataclasses import dataclass
from datetime import date
from itertools import islice

from src.cookbook.domain.entities.food_fact import FoodFact
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.services.food_facts import daily_candidates
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.ports.outbound.food_fact_source import IFoodFactSource
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository

# Candidates looked up per query; the day's own fact is nearly always usable.
BATCH = 8


@dataclass(frozen=True)
class DailyFoodFact:
    fact: FoodFact
    ingredient: Ingredient


class ReadFoodFact:
    def __init__(self, *, source: IFoodFactSource, ingredient_repo: IIngredientRepository) -> None:
        self._source = source
        self._ingredients = ingredient_repo

    async def for_day(self, day: date) -> DailyFoodFact | None:
        """The fact `day` shows, or None when no fact's ingredient is left."""
        facts = self._source.facts()
        candidates = daily_candidates(day, len(facts))
        while batch := [facts[i] for i in islice(candidates, BATCH)]:
            found = await self._ingredients.by_seed_keys(sorted({f.ingredient_key for f in batch}))
            for fact in batch:
                ingredient = found.get(fact.ingredient_key)
                if ingredient is not None and ingredient.status is IngredientStatus.ACTIVE:
                    return DailyFoodFact(fact=fact, ingredient=ingredient)
        return None
