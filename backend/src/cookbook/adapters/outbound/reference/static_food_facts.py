"""The food facts that ship with the release, held in memory. The
composition root hands over a loader, so the facts are read once, on first
use, from wherever the reference data lives."""

from collections.abc import Callable
from collections.abc import Sequence

from src.cookbook.domain.entities.food_fact import FoodFact


class StaticFoodFactSource:
    def __init__(self, load: Callable[[], Sequence[FoodFact]]) -> None:
        self._load = load
        self._facts: tuple[FoodFact, ...] | None = None

    def facts(self) -> Sequence[FoodFact]:
        if self._facts is None:
            self._facts = tuple(sorted(self._load(), key=lambda f: f.key))
        return self._facts
