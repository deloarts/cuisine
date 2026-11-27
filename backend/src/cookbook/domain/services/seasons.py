"""
Seasonality: an ingredient may list the months (1 to 12) in which it is in
season in Austria; an empty list means it is not seasonal. A recipe is in
season in a month when it uses at least one seasonal ingredient, through its
sub-recipes too, and every seasonal ingredient it uses is in season then.
"""

from collections.abc import Iterable
from collections.abc import Mapping

from src.cookbook.domain.entities.ingredient import Ingredient

MONTHS = range(1, 13)


def clean_months(months: Iterable[int]) -> list[int]:
    """Sorted months without repeats; anything outside 1 to 12 raises
    ValueError."""
    cleaned = sorted(set(months))
    if any(m not in MONTHS for m in cleaned):
        raise ValueError("Season months run from 1 to 12.")
    return cleaned


def recipe_season(
    ingredient_ids: Iterable[int], ingredients: Mapping[int, Ingredient]
) -> list[int]:
    """The months in which every seasonal ingredient among `ingredient_ids`
    is in season; empty when none of them is seasonal (or their seasons do
    not overlap)."""
    months: set[int] | None = None
    for ingredient_id in set(ingredient_ids):
        ingredient = ingredients.get(ingredient_id)
        if ingredient is None or not ingredient.season_months:
            continue
        own = set(ingredient.season_months)
        months = own if months is None else months & own
    return sorted(months or ())
