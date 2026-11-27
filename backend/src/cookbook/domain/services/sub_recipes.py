"""
Sub-recipes: a step ingredient may name another recipe, such as homemade
lasagna sheets in a lasagna. This module walks those links: how much of a
sub-recipe a line needs, the catalogue ingredients the whole tree uses with
their scaled amounts, and the rules against cycles and deep nesting.

Everything derived (nutrition, allergens, diets, warnings, the dinner guest
check, shopping) goes through the whole tree, whatever the viewer may see of
the sub-recipes; only links and titles are hidden.
"""

from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import SubRecipeCycleError
from src.cookbook.domain.exceptions import SubRecipeTooDeepError

# A recipe, its sub-recipes, theirs and theirs: three levels below the top.
MAX_DEPTH = 3


class Line(Protocol):
    """An ingredient or sub-recipe line with its amount: a stored line or
    one of the merged lines the derivation computes."""

    @property
    def ingredient_id(self) -> int | None: ...

    @property
    def sub_recipe_id(self) -> int | None: ...

    @property
    def amount(self) -> float | None: ...

    @property
    def unit_id(self) -> int | None: ...


# The lines a walk counts for one recipe of the tree. Amounts need the
# merged lines (`recipe_derivation.merged_lines`), since the steps and the
# declared list overlap; `named_lines` is enough when only ids matter.
LinesOf = Callable[[Recipe], Iterable[Line]]


def named_lines(recipe: Recipe) -> Iterable[Line]:
    """Every stored line of the recipe, for walks that only collect ids."""
    return recipe.all_lines


def sub_recipe_factor(line: Line, sub: Recipe) -> float:
    """How many batches of `sub` the line needs. In the sub-recipe's yield
    unit it is amount / yield; otherwise the amount counts servings of the
    sub-recipe; without an amount the line needs one batch."""
    if line.amount is None:
        return 1.0
    if sub.yield_amount and sub.yield_unit_id is not None and line.unit_id == sub.yield_unit_id:
        return line.amount / sub.yield_amount
    return line.amount / max(sub.base_servings, 1)


@dataclass(frozen=True)
class LeafLine:
    """A catalogue ingredient the tree needs, scaled to one batch of the top
    recipe, with the sub-recipes it came through (outermost first)."""

    ingredient_id: int
    amount: float | None
    unit_id: int | None
    path: tuple[int, ...]


def leaves(
    recipe: Recipe,
    recipes: Mapping[int, Recipe],
    lines_of: LinesOf,
    factor: float = 1.0,
    path: tuple[int, ...] = (),
    skip: frozenset[int] = frozenset(),
) -> Iterator[LeafLine]:
    """Every catalogue ingredient line of `recipe` and its sub-recipes, as
    `lines_of` gives them, scaled by `factor`. Sub-recipes in `skip` are not
    expanded (bought as a whole); missing ones are ignored."""
    if len(path) > MAX_DEPTH:
        return
    for line in lines_of(recipe):
        if line.ingredient_id is not None:
            yield LeafLine(
                line.ingredient_id,
                line.amount * factor if line.amount is not None else None,
                line.unit_id,
                path,
            )
        elif line.sub_recipe_id is not None and line.sub_recipe_id not in skip:
            sub = recipes.get(line.sub_recipe_id)
            if sub is None or sub.id in path or sub.id == recipe.id:
                continue
            yield from leaves(
                sub,
                recipes,
                lines_of,
                factor * sub_recipe_factor(line, sub),
                (*path, sub.id),
                skip,
            )


def batches(
    recipe: Recipe,
    recipes: Mapping[int, Recipe],
    lines_of: LinesOf,
    factor: float = 1.0,
    path: tuple[int, ...] = (),
    skip: frozenset[int] = frozenset(),
) -> Iterator[tuple[Recipe, float, tuple[int, ...]]]:
    """`recipe` and every sub-recipe below it, each with how many of its
    batches one batch of the top recipe times `factor` needs and the path
    to it (outermost first). Walks the tree like `leaves`, so a sub-recipe
    used twice appears twice."""
    if len(path) > MAX_DEPTH:
        return
    yield recipe, factor, path
    for line in lines_of(recipe):
        if line.sub_recipe_id is None or line.sub_recipe_id in skip:
            continue
        sub = recipes.get(line.sub_recipe_id)
        if sub is None or sub.id in path or sub.id == recipe.id:
            continue
        yield from batches(
            sub,
            recipes,
            lines_of,
            factor * sub_recipe_factor(line, sub),
            (*path, sub.id),
            skip,
        )


def all_ingredient_ids(recipe: Recipe, recipes: Mapping[int, Recipe]) -> list[int]:
    return sorted({leaf.ingredient_id for leaf in leaves(recipe, recipes, named_lines)})


def depth_below(recipe_id: int, recipes: Mapping[int, Recipe], seen: tuple[int, ...] = ()) -> int:
    """How many levels of sub-recipes hang below the recipe."""
    recipe = recipes.get(recipe_id)
    if recipe is None:
        return 0
    if recipe_id in seen:
        raise SubRecipeCycleError("A recipe cannot contain itself through its sub-recipes.")
    subs = recipe.sub_recipe_ids
    if not subs:
        return 0
    return 1 + max(depth_below(s, recipes, (*seen, recipe_id)) for s in subs)


def assert_sub_recipes_allowed(
    recipe: Recipe, recipes: Mapping[int, Recipe], depth_above: int, ancestors: set[int]
) -> None:
    """No cycle through the recipe and at most MAX_DEPTH levels in every
    tree it belongs to. `depth_above` is the longest chain of recipes using
    it; `ancestors` every recipe that uses it, directly or not."""
    for sub_id in recipe.sub_recipe_ids:
        if sub_id == recipe.id or sub_id in ancestors:
            raise SubRecipeCycleError("A recipe cannot contain itself through its sub-recipes.")
    tree = {**recipes, recipe.id: recipe} if recipe.id else dict(recipes)
    below = 0
    for sub_id in recipe.sub_recipe_ids:
        if sub_id == recipe.id:
            continue
        below = max(below, 1 + depth_below(sub_id, tree, (recipe.id,) if recipe.id else ()))
    if depth_above + below > MAX_DEPTH:
        raise SubRecipeTooDeepError(f"Sub-recipes may nest at most {MAX_DEPTH} levels deep.")
