"""
What a recipe needs to be cooked with: the "You'll need" list and what the
cook's kitchen lacks. The list is the union over the steps, each item with
the highest count any single step needs (two bowls in one step and one in
another need two bowls, not three), and includes the equipment of the
sub-recipes, listed apart for the sub-recipe whose steps need it.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.sub_recipes import MAX_DEPTH


@dataclass(frozen=True)
class NeededEquipment:
    equipment_id: int
    # The highest count a single step names; None when no step names one.
    count: int | None
    # The sub-recipe whose steps need it; None for the recipe's own steps.
    sub_recipe_id: int | None = None


def _merge(
    found: dict[tuple[int, int | None], int | None], key: tuple[int, int | None], count: int | None
) -> None:
    if key not in found:
        found[key] = count
    elif count is not None:
        previous = found[key]
        found[key] = count if previous is None else max(previous, count)


def needed_equipment(recipe: Recipe, recipes: Mapping[int, Recipe]) -> list[NeededEquipment]:
    """The recipe's own equipment first, in step order, then each
    sub-recipe's (depth first). A sub-recipe the tree reaches twice is
    listed once."""
    found: dict[tuple[int, int | None], int | None] = {}
    for step in recipe.steps:
        for item in step.equipment:
            _merge(found, (item.equipment_id, None), item.count)
    seen: set[int] = {recipe.id}

    def walk(parent: Recipe, depth: int) -> None:
        if depth > MAX_DEPTH:
            return
        for sub_id in parent.sub_recipe_ids:
            sub = recipes.get(sub_id)
            if sub is None or sub.id in seen:
                continue
            seen.add(sub.id)
            for step in sub.steps:
                for item in step.equipment:
                    _merge(found, (item.equipment_id, sub.id), item.count)
            walk(sub, depth + 1)

    walk(recipe, 1)
    return [NeededEquipment(eid, count, sub_id) for (eid, sub_id), count in found.items()]


def all_equipment_ids(recipe: Recipe, recipes: Mapping[int, Recipe]) -> set[int]:
    """Every equipment item the recipe and its sub-recipes need."""
    return {n.equipment_id for n in needed_equipment(recipe, recipes)}


def missing_equipment(recipe: Recipe, recipes: Mapping[int, Recipe], owned: set[int]) -> list[int]:
    """The equipment of the tree the kitchen lacks, without repeats, in the
    order of the "You'll need" list."""
    return list(
        dict.fromkeys(
            n.equipment_id for n in needed_equipment(recipe, recipes) if n.equipment_id not in owned
        )
    )
