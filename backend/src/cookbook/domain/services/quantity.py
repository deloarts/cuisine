"""Turning an amount of an ingredient into grams, which nutrition and the
shopping list sums need."""

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.value_objects.enums import UnitKind


def to_grams(amount: float | None, unit: Unit | None, ingredient: Ingredient) -> float | None:
    """Grams of `amount` `unit` of `ingredient`, or None when no path exists.

    The ingredient's own conversion wins, so "1 cup flour" can weigh what a
    cup of flour weighs. Otherwise a mass unit converts by its factor and a
    volume unit by its factor and the ingredient's density. An amount
    without a unit counts as pieces of the ingredient's "piece" conversion
    when it has exactly one count conversion.
    """
    if amount is None:
        return None
    if unit is None:
        return None
    per_unit = ingredient.grams_per_unit(unit.id)
    if per_unit is not None:
        return amount * per_unit
    if unit.kind is UnitKind.MASS and unit.to_base is not None:
        return amount * unit.to_base
    if (
        unit.kind is UnitKind.VOLUME
        and unit.to_base is not None
        and ingredient.density_g_per_ml is not None
    ):
        return amount * unit.to_base * ingredient.density_g_per_ml
    return None
