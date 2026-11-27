"""The recipe's declared ingredient list merged with what its steps use: the
derived list, nutrition, allergens, sub-recipe needs, shopping and a
variation's swap in every step take the larger of the two per ingredient,
and a recipe without a declared list derives exactly what its steps add up
to."""

from datetime import UTC
from datetime import datetime

import pytest

from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.ingredient import UnitConversion
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.exceptions import InvalidRecipeError
from src.cookbook.domain.services.recipe_derivation import IngredientLine
from src.cookbook.domain.services.recipe_derivation import aggregate
from src.cookbook.domain.services.recipe_derivation import derive
from src.cookbook.domain.services.recipe_derivation import shopping_lines
from src.cookbook.domain.services.recipe_rules import validate_recipe
from src.cookbook.domain.services.revisions import SnapshotRefs
from src.cookbook.domain.services.revisions import build_snapshot
from src.cookbook.domain.services.step_ids import StepIdKeepers
from src.cookbook.domain.services.variations import Change
from src.cookbook.domain.services.variations import apply_variation
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.enums import VariationChangeKind
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText

NOW = datetime(2026, 1, 1, tzinfo=UTC)

G = Unit(id=1, code="g", kind=UnitKind.MASS, to_base=1.0, created=NOW)
KG = Unit(id=2, code="kg", kind=UnitKind.MASS, to_base=1000.0, created=NOW)
ML = Unit(id=3, code="ml", kind=UnitKind.VOLUME, to_base=1.0, created=NOW)
TBSP = Unit(id=4, code="tbsp", kind=UnitKind.VOLUME, to_base=15.0, created=NOW)
PIECE = Unit(id=5, code="piece", kind=UnitKind.COUNT, to_base=None, created=NOW)
UNITS = {u.id: u for u in (G, KG, ML, TBSP, PIECE)}


def _ingredient(id_: int, name: str, **kwargs: object) -> Ingredient:
    return Ingredient(
        id=id_,
        owner_id=1,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        translations={"de-AT": IngredientText(name, name)},
        **kwargs,  # type: ignore[arg-type]
    )


FLOUR = _ingredient(
    10, "Mehl", nutrition=Nutrition(kcal=350, protein=10), allergens=[Allergen.GLUTEN]
)
EGG = _ingredient(
    12,
    "Ei",
    nutrition=Nutrition(kcal=143),
    conversions=[UnitConversion(PIECE.id, 50.0)],
    allergens=[Allergen.EGGS],
)
SALT = _ingredient(13, "Salz")
MILK = _ingredient(14, "Milch", allergens=[Allergen.MILK])
BUTTER = _ingredient(15, "Butter")
INGREDIENTS = {i.id: i for i in (FLOUR, EGG, SALT, MILK, BUTTER)}


def _line(ingredient: Ingredient, amount: float | None, unit: Unit | None) -> StepIngredient:
    return StepIngredient(
        ingredient_id=ingredient.id, amount=amount, unit_id=unit.id if unit else None
    )


def _recipe(
    *steps: list[StepIngredient],
    declared: list[StepIngredient] | None = None,
    id_: int = 1,
    servings: int = 2,
) -> Recipe:
    return Recipe(
        id=id_,
        owner_id=1,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        base_servings=servings,
        translations={"de-AT": RecipeText("Test")},
        steps=[RecipeStep(translations={"de-AT": StepText("x")}, ingredients=s) for s in steps],
        ingredients=declared or [],
    )


def _lines(recipe: Recipe, servings: int | None = None) -> list[tuple[int, float | None, int]]:
    return [
        (line.ingredient_id, line.amount, line.unit_id or 0)
        for line in derive(recipe, INGREDIENTS, UNITS, servings=servings).lines
    ]


def test_without_a_declared_list_the_steps_alone_count() -> None:
    steps = (
        [_line(FLOUR, 200, G), _line(EGG, 2, PIECE)],
        [_line(FLOUR, 100, G), _line(EGG, 50, G), _line(SALT, None, None)],
        [_line(MILK, 2, TBSP), _line(MILK, 100, G)],
    )
    expected = aggregate(
        (
            (si.ingredient_id or 0, si.amount, si.unit_id)
            for step in steps
            for si in step
            if si.ingredient_id
        ),
        INGREDIENTS,
        UNITS,
    )
    derived = derive(_recipe(*steps), INGREDIENTS, UNITS)
    assert derived.lines == expected
    flour = next(line for line in derived.lines if line.ingredient_id == FLOUR.id)
    assert flour == IngredientLine(FLOUR.id, 300, G.id)
    # Eggs in pieces and grams weigh, milk in spoons and grams does not.
    assert IngredientLine(EGG.id, 150, G.id) in derived.lines
    assert IngredientLine(MILK.id, 2, TBSP.id) in derived.lines
    assert IngredientLine(MILK.id, 100, G.id) in derived.lines


def test_the_larger_side_counts_in_one_unit() -> None:
    more_declared = _recipe(
        [_line(FLOUR, 150, G)], [_line(FLOUR, 50, G)], declared=[_line(FLOUR, 500, G)]
    )
    assert _lines(more_declared) == [(FLOUR.id, 500, G.id)]
    more_used = _recipe(
        [_line(FLOUR, 150, G)], [_line(FLOUR, 400, G)], declared=[_line(FLOUR, 500, G)]
    )
    assert _lines(more_used) == [(FLOUR.id, 550, G.id)]
    # Scaling applies to the merged amount.
    assert _lines(more_declared, servings=4) == [(FLOUR.id, 1000, G.id)]


def test_declared_lines_come_first_and_name_what_no_step_uses() -> None:
    recipe = _recipe(
        [_line(EGG, 2, PIECE), _line(FLOUR, 100, G)],
        declared=[_line(MILK, 250, ML), _line(FLOUR, 100, G)],
    )
    assert [line[0] for line in _lines(recipe)] == [MILK.id, FLOUR.id, EGG.id]
    derived = derive(recipe, INGREDIENTS, UNITS)
    assert Allergen.MILK in derived.allergens
    assert Allergen.EGGS in derived.allergens


def test_units_that_weigh_compare_in_grams() -> None:
    # Three declared eggs weigh 150 g, the steps use 120 g.
    recipe = _recipe([_line(EGG, 120, G)], declared=[_line(EGG, 3, PIECE)])
    assert _lines(recipe) == [(EGG.id, 150, G.id)]
    used_more = _recipe([_line(EGG, 200, G)], declared=[_line(EGG, 3, PIECE)])
    assert _lines(used_more) == [(EGG.id, 200, G.id)]


def test_units_of_one_kind_compare_in_the_base_unit() -> None:
    # Salt has no density, so spoons and millilitres do not weigh, yet both
    # are volumes: the declared tablespoon (15 ml) beats 10 ml.
    recipe = _recipe([_line(SALT, 10, ML)], declared=[_line(SALT, 1, TBSP)])
    assert _lines(recipe) == [(SALT.id, 1, TBSP.id)]
    used_more = _recipe([_line(SALT, 20, ML)], declared=[_line(SALT, 1, TBSP)])
    assert _lines(used_more) == [(SALT.id, 20, ML.id)]


def test_units_that_do_not_compare_stay_side_by_side() -> None:
    # Milk in spoons cannot be weighed and pieces of milk are no volume:
    # both stay, so nothing undercounts.
    recipe = _recipe([_line(MILK, 2, TBSP)], declared=[_line(MILK, 1, PIECE)])
    assert sorted(_lines(recipe)) == sorted([(MILK.id, 1, PIECE.id), (MILK.id, 2, TBSP.id)])


def test_to_taste_lines_give_way_to_measured_ones() -> None:
    declared_to_taste = _recipe([_line(SALT, 5, G)], declared=[_line(SALT, None, None)])
    assert _lines(declared_to_taste) == [(SALT.id, 5, G.id)]
    used_to_taste = _recipe([_line(SALT, None, None)], declared=[_line(SALT, 5, G)])
    assert _lines(used_to_taste) == [(SALT.id, 5, G.id)]
    both = _recipe([_line(SALT, None, None)], declared=[_line(SALT, None, None)])
    assert _lines(both) == [(SALT.id, None, 0)]


def test_nutrition_counts_the_merged_amount() -> None:
    recipe = _recipe([_line(FLOUR, 100, G)], declared=[_line(FLOUR, 200, G)], servings=1)
    derived = derive(recipe, INGREDIENTS, UNITS)
    assert derived.nutrition_total.kcal == pytest.approx(700)
    steps_only = derive(_recipe([_line(FLOUR, 100, G)], servings=1), INGREDIENTS, UNITS)
    assert steps_only.nutrition_total.kcal == pytest.approx(350)


def test_sub_recipes_take_the_side_needing_more_batches() -> None:
    pastry = _recipe([_line(FLOUR, 250, G)], id_=2, servings=4)
    tree = {pastry.id: pastry}
    in_step = StepIngredient(sub_recipe_id=pastry.id, amount=2)
    declared = StepIngredient(sub_recipe_id=pastry.id, amount=4)
    tart = _recipe([in_step], declared=[declared], servings=2)
    derived = derive(tart, INGREDIENTS, UNITS, recipes=tree)
    assert [(n.recipe_id, n.amount, n.batches) for n in derived.needs] == [(pastry.id, 4, 1.0)]
    # One whole batch of the pastry: 250 g flour, 875 kcal.
    assert derived.nutrition_total.kcal == pytest.approx(875)
    declared_only = _recipe([], declared=[declared], servings=2)
    assert derive(declared_only, INGREDIENTS, UNITS, recipes=tree).needs
    assert declared_only.sub_recipe_ids == [pastry.id]


def test_shopping_counts_the_merged_list() -> None:
    recipe = _recipe([_line(FLOUR, 100, G)], declared=[_line(FLOUR, 300, G), _line(MILK, 1, PIECE)])
    found = {
        (line.ingredient_id, line.amount, line.unit_id)
        for line, _ in shopping_lines(recipe, INGREDIENTS, UNITS, {}, 1.0)
    }
    assert found == {(FLOUR.id, 300, G.id), (MILK.id, 1, PIECE.id)}


def test_a_swap_in_every_step_covers_the_declared_list() -> None:
    recipe = _recipe(
        [_line(BUTTER, 100, G)], declared=[_line(BUTTER, 250, G), _line(FLOUR, 200, G)]
    )
    swap = Change(
        id="c1",
        kind=VariationChangeKind.SWAP,
        step=None,
        ingredient_id=BUTTER.id,
        to_ingredient_id=MILK.id,
        keep_amount=True,
    )
    applied = apply_variation(recipe, [swap], "de-AT")
    assert applied.skipped_change_ids == []
    assert [line.ingredient_id for line in applied.recipe.ingredients] == [MILK.id, FLOUR.id]
    assert sorted(_lines(applied.recipe)) == sorted([(MILK.id, 250, G.id), (FLOUR.id, 200, G.id)])
    # The original stays untouched.
    assert recipe.ingredients[0].ingredient_id == BUTTER.id
    declared_only = _recipe([_line(FLOUR, 100, G)], declared=[_line(BUTTER, 250, G)])
    assert apply_variation(declared_only, [swap], "de-AT").skipped_change_ids == []


def test_declared_lines_name_exactly_one_record() -> None:
    recipe = _recipe([], declared=[StepIngredient(amount=1)])
    with pytest.raises(InvalidRecipeError):
        validate_recipe(recipe)
    negative = _recipe([], declared=[_line(FLOUR, -1, G)])
    with pytest.raises(InvalidRecipeError):
        validate_recipe(negative)


def test_declared_ids_are_kept_like_step_line_ids() -> None:
    line = _line(FLOUR, 100, G)
    recipe = _recipe([], declared=[line])
    ids = StepIdKeepers()
    ids.know_declared(recipe.ingredients)
    assert ids.declared.take(str(line.public_id)) == line.public_id
    assert ids.declared.take(str(line.public_id)) != line.public_id
    snapshot = build_snapshot(recipe, SnapshotRefs())
    assert snapshot["ingredients"][0]["id"] == str(line.public_id)
    restoring = StepIdKeepers()
    restoring.know_snapshot(snapshot)
    assert restoring.declared.take(str(line.public_id)) == line.public_id
