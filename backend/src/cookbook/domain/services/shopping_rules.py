"""Adding up shopping items: a new amount of an ingredient joins an open
item of the same ingredient, unit and sub-recipe path instead of becoming a
second line, so flour for homemade pasta stays apart from flour for bread."""

from collections.abc import Iterable

from src.cookbook.domain.entities.cooking import ShoppingItem


def find_mergeable(
    items: Iterable[ShoppingItem],
    ingredient_id: int | None,
    unit_id: int | None,
    sub_recipe_path: list[int] | None = None,
) -> ShoppingItem | None:
    if ingredient_id is None:
        return None
    for item in items:
        if (
            not item.checked
            and item.ingredient_id == ingredient_id
            and item.unit_id == unit_id
            and item.sub_recipe_path == (sub_recipe_path or [])
            and item.amount is not None
        ):
            return item
    return None
