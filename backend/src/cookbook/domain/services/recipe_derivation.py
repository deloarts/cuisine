"""
What a recipe adds up to: the ingredient list for a number of servings, the
sub-recipes it needs, the nutrition in total and per serving, the allergens
and the diets it fits. These are derived on every read.

A recipe holds two ingredient lists that overlap: the lines of its steps and
the list the cook declared for the whole recipe. `merged_lines` turns them
into the one list everything else counts, taking the larger of the two per
ingredient, so a step line is never lost and nothing read from the list can
undercount. A recipe without a declared list counts its steps alone.

Nutrition, allergens and diets go through the sub-recipes too
(`sub_recipes.leaves`), scaled by how much of each the recipe needs.
"""

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.services.diet_rules import diets_of
from src.cookbook.domain.services.quantity import to_grams
from src.cookbook.domain.services.sub_recipes import LeafLine
from src.cookbook.domain.services.sub_recipes import LinesOf
from src.cookbook.domain.services.sub_recipes import leaves
from src.cookbook.domain.services.sub_recipes import named_lines
from src.cookbook.domain.services.sub_recipes import sub_recipe_factor
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import NoteText


@dataclass(frozen=True)
class IngredientLine:
    """One line of the derived ingredient list. `amount` None means "to
    taste"; `unit_id` None means a bare number of pieces."""

    ingredient_id: int
    amount: float | None
    unit_id: int | None
    # The cook's note per locale ("weich", "festkochend"), see `merged_notes`.
    notes: Mapping[str, NoteText] = field(default_factory=dict)


@dataclass(frozen=True)
class SubRecipeNeed:
    """A sub-recipe the recipe needs, with the line's amount scaled to the
    wanted servings and the number of batches that makes."""

    recipe_id: int
    amount: float | None
    unit_id: int | None
    batches: float


@dataclass(frozen=True)
class ExtendedTotal:
    """One extended nutrient summed over the recipe, for the wanted
    servings and per serving. `complete` is false when an amount could not
    be weighed or a counted ingredient does not state this nutrient."""

    key: str
    total: float
    per_serving: float
    complete: bool


@dataclass(frozen=True)
class DerivedRecipe:
    lines: list[IngredientLine]
    nutrition_total: Nutrition
    nutrition_per_serving: Nutrition
    # False when an amount could not be weighed or an ingredient has no
    # nutrition, so the totals undercount.
    nutrition_complete: bool
    allergens: list[Allergen]
    servings: int
    factor: float
    # The diets the recipe's ingredients fit, from their diet markers.
    diets: list[Diet] = field(default_factory=list)
    missing_nutrition_ingredient_ids: list[int] = field(default_factory=list)
    needs: list[SubRecipeNeed] = field(default_factory=list)
    extended: list[ExtendedTotal] = field(default_factory=list)


def scale_factor(recipe: Recipe, servings: int | None) -> tuple[int, float]:
    wanted = servings if servings and servings > 0 else recipe.base_servings
    return wanted, wanted / max(recipe.base_servings, 1)


def _gram_unit(units: Mapping[int, Unit]) -> Unit | None:
    return next(
        (u for u in units.values() if u.kind is UnitKind.MASS and u.to_base == 1.0),
        None,
    )


def _combine(
    ingredient_id: int,
    per_unit: Mapping[int | None, float],
    ingredient: Ingredient | None,
    units: Mapping[int, Unit],
    gram: Unit | None,
    factor: float,
) -> list[IngredientLine]:
    """Measured amounts of one ingredient, summed per unit, as list lines:
    one unit stays as it is, several add up in grams when every one of them
    can be weighed and stay separate otherwise."""
    if len(per_unit) > 1 and ingredient is not None and gram is not None:
        weights = [
            to_grams(amount, units.get(unit_id) if unit_id is not None else None, ingredient)
            for unit_id, amount in per_unit.items()
        ]
        if all(w is not None for w in weights):
            total = sum(w for w in weights if w is not None)
            return [IngredientLine(ingredient_id, total * factor, gram.id)]
    return [
        IngredientLine(ingredient_id, amount * factor, unit_id)
        for unit_id, amount in per_unit.items()
    ]


def _per_unit(found: Iterable[tuple[float | None, int | None]]) -> dict[int | None, float]:
    per_unit: dict[int | None, float] = {}
    for amount, unit_id in found:
        if amount is not None:
            per_unit[unit_id] = per_unit.get(unit_id, 0.0) + amount
    return per_unit


def aggregate(
    entries: Iterable[tuple[int, float | None, int | None]],
    ingredients: Mapping[int, Ingredient],
    units: Mapping[int, Unit],
    factor: float = 1.0,
) -> list[IngredientLine]:
    """Ingredient lines summed per ingredient. Lines of one unit add up;
    lines of several units add up in grams when every one of them can be
    weighed, and stay separate otherwise. "To taste" lines appear once, and
    only when the ingredient has no measured line."""
    by_ingredient: dict[int, list[tuple[float | None, int | None]]] = {}
    for ingredient_id, amount, unit_id in entries:
        by_ingredient.setdefault(ingredient_id, []).append((amount, unit_id))

    gram = _gram_unit(units)
    lines: list[IngredientLine] = []
    for ingredient_id, found in by_ingredient.items():
        per_unit = _per_unit(found)
        if not per_unit:
            lines.append(IngredientLine(ingredient_id, None, found[0][1]))
            continue
        lines.extend(
            _combine(ingredient_id, per_unit, ingredients.get(ingredient_id), units, gram, factor)
        )
    return lines


@dataclass(frozen=True)
class MergedLine:
    """One line of the merged list of a recipe, for one batch: a catalogue
    ingredient or a sub-recipe, exactly one."""

    ingredient_id: int | None
    sub_recipe_id: int | None
    amount: float | None
    unit_id: int | None
    notes: Mapping[str, NoteText] = field(default_factory=dict)


def merged_notes(declared: list[StepIngredient], used: list[StepIngredient]) -> dict[str, NoteText]:
    """The notes of one merged line per locale: those of the declared lines
    when the cook wrote any there, since the declared list speaks for the
    whole recipe, distinct notes joined with a comma. Without them, a step
    note counts only when every step line of the ingredient has that same
    note ("gehackt"): a note such as "zum Wälzen" or "der Rest" describes
    the line in its own step, never the whole amount."""
    declared_notes: dict[str, list[str]] = {}
    for line in declared:
        for locale, text in line.translations.items():
            note = text.note.strip()
            if note and note not in declared_notes.setdefault(locale, []):
                declared_notes[locale].append(note)
    found = {loc: NoteText(note=", ".join(n)) for loc, n in declared_notes.items() if n}
    if found or not used:
        return found
    shared: dict[str, NoteText] = {}
    for locale in used[0].translations:
        notes = {
            line.translations[locale].note.strip() if locale in line.translations else ""
            for line in used
        }
        if len(notes) == 1 and (note := notes.pop()):
            shared[locale] = NoteText(note=note)
    return shared


def _unit_class(unit_id: int | None, units: Mapping[int, Unit]) -> tuple[object, ...]:
    """Units whose amounts compare: those of one kind with a factor to the
    kind's base unit, otherwise only the unit itself."""
    unit = units.get(unit_id) if unit_id is not None else None
    if unit is not None and unit.to_base is not None:
        return ("kind", unit.kind)
    return ("unit", unit_id)


def _in_base(per_unit: Mapping[int | None, float], units: Mapping[int, Unit]) -> float:
    total = 0.0
    for unit_id, amount in per_unit.items():
        unit = units.get(unit_id) if unit_id is not None else None
        total += amount * (unit.to_base if unit is not None and unit.to_base else 1.0)
    return total


def _merge_ingredient(
    ingredient_id: int,
    declared: list[StepIngredient],
    used: list[StepIngredient],
    ingredient: Ingredient | None,
    units: Mapping[int, Unit],
    gram: Unit | None,
) -> list[IngredientLine]:
    """The larger of the declared amount and the steps' summed amount of one
    ingredient, compared within units that compare (see `merged_lines`)."""
    have = _per_unit((line.amount, line.unit_id) for line in declared)
    need = _per_unit((line.amount, line.unit_id) for line in used)
    if not have and not need:
        first = (declared or used)[0]
        return [IngredientLine(ingredient_id, None, first.unit_id)]
    if not have or not need:
        return _combine(ingredient_id, have or need, ingredient, units, gram, 1.0)
    every = {**have, **need}
    if len(every) == 1:
        unit_id = next(iter(every))
        return [IngredientLine(ingredient_id, max(have[unit_id], need[unit_id]), unit_id)]
    if ingredient is not None and gram is not None:
        weights = {
            unit_id: to_grams(1.0, units.get(unit_id) if unit_id is not None else None, ingredient)
            for unit_id in every
        }
        if all(w is not None for w in weights.values()):
            have_g = sum(a * (weights[u] or 0.0) for u, a in have.items())
            need_g = sum(a * (weights[u] or 0.0) for u, a in need.items())
            return [IngredientLine(ingredient_id, max(have_g, need_g), gram.id)]
    lines: list[IngredientLine] = []
    classes = dict.fromkeys(_unit_class(u, units) for u in [*have, *need])
    for unit_class in classes:
        have_part = {u: a for u, a in have.items() if _unit_class(u, units) == unit_class}
        need_part = {u: a for u, a in need.items() if _unit_class(u, units) == unit_class}
        winner = need_part
        if not need_part or (have_part and _in_base(have_part, units) > _in_base(need_part, units)):
            winner = have_part
        lines.extend(IngredientLine(ingredient_id, a, u) for u, a in winner.items())
    return lines


def merged_lines(
    recipe: Recipe,
    ingredients: Mapping[int, Ingredient],
    units: Mapping[int, Unit],
    recipes: Mapping[int, Recipe],
) -> list[MergedLine]:
    """The recipe's own ingredient list for one batch: the declared list
    merged with what the steps use, declared lines first in their order,
    then the ingredients only the steps name.

    Per ingredient the steps' lines and the declared lines are each summed
    per unit, and the larger side counts: in that unit when both use one and
    the same, in grams when every unit can be weighed, and otherwise per
    group of comparable units (one kind with a factor to its base unit, or
    a single unit), where the side with more keeps its lines. A "to taste"
    line remains only when neither side measures the ingredient. Per
    sub-recipe the side needing more batches keeps its lines. Without a
    declared list this is exactly the steps' list."""
    gram = _gram_unit(units)
    declared: dict[tuple[str, int], list[StepIngredient]] = {}
    used: dict[tuple[str, int], list[StepIngredient]] = {}
    order: dict[tuple[str, int], None] = {}
    sources = (
        (declared, recipe.ingredients),
        (used, [si for step in recipe.steps for si in step.ingredients]),
    )
    for target, lines in sources:
        for line in lines:
            if line.ingredient_id is not None:
                key = ("ingredient", line.ingredient_id)
            elif line.sub_recipe_id is not None:
                key = ("recipe", line.sub_recipe_id)
            else:
                continue
            target.setdefault(key, []).append(line)
            order.setdefault(key)
    result: list[MergedLine] = []
    for kind, ref in order:
        have = declared.get((kind, ref), [])
        need = used.get((kind, ref), [])
        if kind == "recipe":
            winner = need or have
            sub = recipes.get(ref)
            if have and need and sub is not None:
                have_batches = sum(sub_recipe_factor(line, sub) for line in have)
                need_batches = sum(sub_recipe_factor(line, sub) for line in need)
                winner = have if have_batches > need_batches else need
            notes = merged_notes(have, need)
            result.extend(
                MergedLine(None, ref, line.amount, line.unit_id, notes if i == 0 else {})
                for i, line in enumerate(winner)
            )
            continue
        # An ingredient split over units of different kinds carries its
        # notes on its first line only, so the reader sees them once.
        notes = merged_notes(have, need)
        result.extend(
            MergedLine(line.ingredient_id, None, line.amount, line.unit_id, notes if i == 0 else {})
            for i, line in enumerate(
                _merge_ingredient(ref, have, need, ingredients.get(ref), units, gram)
            )
        )
    return result


def merged_lines_of(
    ingredients: Mapping[int, Ingredient],
    units: Mapping[int, Unit],
    recipes: Mapping[int, Recipe],
) -> LinesOf:
    """`merged_lines` for every recipe of a tree walk (`sub_recipes.leaves`)."""
    return lambda recipe: merged_lines(recipe, ingredients, units, recipes)


def shopping_lines(
    recipe: Recipe,
    ingredients: Mapping[int, Ingredient],
    units: Mapping[int, Unit],
    recipes: Mapping[int, Recipe],
    factor: float,
    bought: frozenset[int] = frozenset(),
) -> list[tuple[IngredientLine, tuple[int, ...]]]:
    """What to buy for `factor` batches: every catalogue ingredient of the
    tree, summed per ingredient and sub-recipe path. Sub-recipes in `bought`
    are not expanded; the caller adds them as one item each."""
    by_path: dict[tuple[int, ...], list[LeafLine]] = {}
    lines_of = merged_lines_of(ingredients, units, recipes)
    for leaf in leaves(recipe, recipes, lines_of, factor, skip=bought):
        by_path.setdefault(leaf.path, []).append(leaf)
    result: list[tuple[IngredientLine, tuple[int, ...]]] = []
    for path, found in by_path.items():
        lines = aggregate(
            ((f.ingredient_id, f.amount, f.unit_id) for f in found), ingredients, units
        )
        result.extend((line, path) for line in lines)
    return result


def derive(
    recipe: Recipe,
    ingredients: Mapping[int, Ingredient],
    units: Mapping[int, Unit],
    servings: int | None = None,
    recipes: Mapping[int, Recipe] | None = None,
) -> DerivedRecipe:
    """`recipes` holds the sub-recipes of the tree; without it sub-recipe
    lines count for nothing."""
    tree = recipes or {}
    wanted, factor = scale_factor(recipe, servings)
    total = Nutrition()
    complete = True
    missing: set[int] = set()
    allergens: set[Allergen] = set()
    used: list[Ingredient] = []
    extended: dict[str, float] = {}
    # Keys some measured ingredient does not state, and whether any measured
    # amount could not be weighed at all.
    extended_gaps: set[str] = set()
    unweighable = False
    lines_of = merged_lines_of(ingredients, units, tree)
    for leaf in leaves(recipe, tree, lines_of):
        ingredient = ingredients.get(leaf.ingredient_id)
        if ingredient is None:
            complete = False
            unweighable = True
            continue
        allergens.update(ingredient.allergens)
        used.append(ingredient)
        if leaf.amount is None:
            # "To taste" adds too little to count.
            continue
        grams = to_grams(
            leaf.amount, units.get(leaf.unit_id) if leaf.unit_id is not None else None, ingredient
        )
        if grams is not None:
            for key in EXTENDED_KEYS:
                value = ingredient.extended_nutrition.get(key)
                if value is None:
                    extended_gaps.add(key)
                else:
                    extended[key] = extended.get(key, 0.0) + value * grams / 100.0
        else:
            unweighable = True
        if grams is None or ingredient.nutrition.is_empty:
            complete = False
            if ingredient.nutrition.is_empty:
                missing.add(ingredient.id)
            continue
        total = total.plus(ingredient.nutrition.scaled(grams / 100.0))
    own = merged_lines(recipe, ingredients, units, tree)
    needs = []
    for line in own:
        sub = tree.get(line.sub_recipe_id) if line.sub_recipe_id is not None else None
        if sub is None:
            continue
        needs.append(
            SubRecipeNeed(
                recipe_id=sub.id,
                amount=line.amount * factor if line.amount is not None else None,
                unit_id=line.unit_id,
                batches=sub_recipe_factor(line, sub) * factor,
            )
        )
    servings_base = max(recipe.base_servings, 1)
    return DerivedRecipe(
        lines=[
            IngredientLine(
                line.ingredient_id,
                line.amount * factor if line.amount is not None else None,
                line.unit_id,
                line.notes,
            )
            for line in own
            if line.ingredient_id is not None
        ],
        nutrition_total=total.scaled(factor).rounded(),
        nutrition_per_serving=total.scaled(1.0 / servings_base).rounded(),
        nutrition_complete=complete,
        allergens=sorted(allergens, key=lambda a: a.value),
        servings=wanted,
        factor=factor,
        diets=diets_of(used),
        missing_nutrition_ingredient_ids=sorted(missing),
        needs=needs,
        extended=[
            ExtendedTotal(
                key=key,
                total=round(extended[key] * factor, 3),
                per_serving=round(extended[key] / servings_base, 3),
                complete=not unweighable and key not in extended_gaps,
            )
            for key in EXTENDED_KEYS
            if key in extended
        ],
    )


def recipe_diets(
    recipe: Recipe, ingredients: Mapping[int, Ingredient], recipes: Mapping[int, Recipe]
) -> list[Diet]:
    """The diets a recipe and its sub-recipes fit, without deriving the rest."""
    return diets_of(
        ingredients[leaf.ingredient_id]
        for leaf in leaves(recipe, recipes, named_lines)
        if leaf.ingredient_id in ingredients
    )
