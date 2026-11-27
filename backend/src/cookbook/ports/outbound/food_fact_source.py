"""The food facts that ship with the release (domain/entities/food_fact.py)."""

from collections.abc import Sequence
from typing import Protocol

from src.cookbook.domain.entities.food_fact import FoodFact


class IFoodFactSource(Protocol):
    def facts(self) -> Sequence[FoodFact]:
        """Every fact, in a fixed order that only a release changes."""
        ...
