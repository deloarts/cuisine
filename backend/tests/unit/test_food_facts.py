"""The food fact of the day: the rotation through every fact and the
fallback when a fact's ingredient has left the catalogue."""

from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
from math import gcd

import pytest

from src.cookbook.adapters.outbound.reference.static_food_facts import StaticFoodFactSource
from src.cookbook.application.use_cases.cooking.food_facts import ReadFoodFact
from src.cookbook.domain.entities.food_fact import FactSource
from src.cookbook.domain.entities.food_fact import FoodFact
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.services.food_facts import daily_candidates
from src.cookbook.domain.services.food_facts import stride
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.texts import IngredientText

NOW = datetime(2026, 11, 27, tzinfo=UTC)
DAY = date(2026, 11, 27)


@pytest.mark.parametrize("count", [1, 2, 3, 10, 12, 97, 1000, 1240])
def test_the_stride_shares_no_factor_with_the_count(count: int) -> None:
    assert gcd(stride(count), count) == 1


@pytest.mark.parametrize("count", [1, 7, 12, 360, 1240])
def test_consecutive_days_show_every_fact_once_before_any_repeats(count: int) -> None:
    shown = [next(daily_candidates(DAY + timedelta(days=d), count)) for d in range(count)]
    assert sorted(shown) == list(range(count))


def test_the_day_decides_the_fact_and_the_fallbacks_cover_every_fact() -> None:
    assert list(daily_candidates(DAY, 50)) == list(daily_candidates(DAY, 50))
    assert sorted(daily_candidates(DAY, 50)) == list(range(50))
    assert next(daily_candidates(DAY, 50)) != next(daily_candidates(DAY + timedelta(days=1), 50))
    assert list(daily_candidates(DAY, 0)) == []


def _fact(ingredient: str, slug: str) -> FoodFact:
    return FoodFact(
        key=f"{ingredient}.{slug}",
        ingredient_key=ingredient,
        texts={"en-GB": f"{ingredient} {slug}", "de-AT": f"{ingredient} {slug} (de)"},
        source=FactSource(locale="en-GB", title=ingredient.title(), revision=1),
    )


def _ingredient(id_: int, key: str, status: IngredientStatus) -> Ingredient:
    return Ingredient(
        id=id_,
        owner_id=None,
        original_locale="en-GB",
        created=NOW,
        changed=NOW,
        translations={"en-GB": IngredientText(key, key)},
        status=status,
        seed_key=key,
    )


class _Ingredients:
    def __init__(self, *ingredients: Ingredient) -> None:
        self._by_key = {i.seed_key: i for i in ingredients if i.seed_key}

    async def by_seed_keys(self, keys: list[str]) -> dict[str, Ingredient]:
        return {k: self._by_key[k] for k in keys if k in self._by_key}


FACTS = [_fact(k, s) for k in ("apple", "basil", "cumin", "dill") for s in ("one", "two")]


async def test_the_day_shows_its_own_fact_while_its_ingredient_is_active() -> None:
    every = [
        _ingredient(n, k, IngredientStatus.ACTIVE)
        for n, k in enumerate(("apple", "basil", "cumin", "dill"))
    ]
    source = StaticFoodFactSource(lambda: FACTS)
    use_case = ReadFoodFact(source=source, ingredient_repo=_Ingredients(*every))  # type: ignore[arg-type]
    daily = await use_case.for_day(DAY)
    assert daily is not None
    ordered = source.facts()
    assert daily.fact == ordered[next(daily_candidates(DAY, len(ordered)))]
    assert daily.ingredient.seed_key == daily.fact.ingredient_key


async def test_a_fact_whose_ingredient_is_gone_or_not_active_gives_way() -> None:
    source = StaticFoodFactSource(lambda: FACTS)
    ordered = source.facts()
    first = ordered[next(daily_candidates(DAY, len(ordered)))]
    others = [k for k in ("apple", "basil", "cumin", "dill") if k != first.ingredient_key]
    # The day's ingredient is archived, one other was deleted, the rest are drafts but one.
    kept = [
        _ingredient(1, first.ingredient_key, IngredientStatus.ARCHIVED),
        _ingredient(2, others[0], IngredientStatus.DRAFT),
        _ingredient(3, others[1], IngredientStatus.ACTIVE),
    ]
    use_case = ReadFoodFact(source=source, ingredient_repo=_Ingredients(*kept))  # type: ignore[arg-type]
    daily = await use_case.for_day(DAY)
    assert daily is not None
    assert daily.fact.ingredient_key == others[1]


async def test_no_fact_when_no_fact_has_its_ingredient() -> None:
    use_case = ReadFoodFact(
        source=StaticFoodFactSource(lambda: FACTS),
        ingredient_repo=_Ingredients(),  # type: ignore[arg-type]
    )
    assert await use_case.for_day(DAY) is None
    empty = ReadFoodFact(source=StaticFoodFactSource(tuple), ingredient_repo=_Ingredients())  # type: ignore[arg-type]
    assert await empty.for_day(DAY) is None
