"""The rules behind public ids without a database: which ids a recipe save
keeps, the seed id formula, and that a line's id is no content change."""

from uuid import UUID
from uuid import uuid4
from uuid import uuid5

from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepEquipment
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.services.seed_ids import SEED_NAMESPACE
from src.cookbook.domain.services.seed_ids import seeded_public_id
from src.cookbook.domain.services.step_ids import IdKeeper
from src.cookbook.domain.services.step_ids import StepIdKeepers
from src.cookbook.domain.services.variations import stale_steps


def test_a_keeper_keeps_a_known_id_once_and_replaces_anything_else() -> None:
    known = uuid4()
    keeper = IdKeeper(known={known})
    assert keeper.take(str(known)) == known
    assert keeper.take(str(known)) != known
    stranger = uuid4()
    assert keeper.take(str(stranger)) != stranger
    assert isinstance(keeper.take(None), UUID)
    assert isinstance(keeper.take("not-a-uuid"), UUID)


def test_keepers_know_the_current_steps_and_a_restored_snapshot() -> None:
    line = StepIngredient(ingredient_id=1)
    item = StepEquipment(equipment_id=1)
    step = RecipeStep(ingredients=[line], equipment=[item])
    old_step, old_line = uuid4(), uuid4()
    keepers = StepIdKeepers()
    keepers.know_steps([step])
    keepers.know_snapshot(
        {"steps": [{"id": str(old_step), "ingredients": [{"id": str(old_line)}, {}]}]}
    )
    assert keepers.steps.take(str(step.public_id)) == step.public_id
    assert keepers.steps.take(str(old_step)) == old_step
    assert keepers.lines.take(str(line.public_id)) == line.public_id
    assert keepers.lines.take(str(old_line)) == old_line
    assert keepers.equipment.take(str(item.public_id)) == item.public_id
    # Ids of one kind are not accepted for another.
    assert keepers.lines.take(str(step.public_id)) != step.public_id


def test_the_seed_id_is_uuid5_of_the_fixed_namespace_kind_and_key() -> None:
    assert str(SEED_NAMESPACE) == "2538fe05-07f1-4b04-a2ba-fea846a8eb65"
    assert seeded_public_id("unit", "g") == uuid5(SEED_NAMESPACE, "unit:g")
    assert seeded_public_id("unit", "g") == seeded_public_id("unit", "g")
    assert seeded_public_id("unit", "g") != seeded_public_id("ingredient", "g")


def test_a_line_id_is_no_content_change_for_staleness() -> None:
    line = {"ingredient_id": "a", "amount": 1, "unit_id": None, "notes": {}}
    old = {"steps": [{"translations": {"en-GB": {"text": "Mix."}}, "ingredients": [line]}]}
    new = {
        "steps": [
            {
                "id": str(uuid4()),
                "translations": {"en-GB": {"text": "Mix."}},
                "ingredients": [{**line, "id": str(uuid4())}],
            }
        ]
    }
    assert stale_steps(old, new, [1], "en-GB") == []


def test_an_import_derives_step_and_line_ids_from_the_recipe_and_the_source_id() -> None:
    recipe, other_recipe, source = uuid4(), uuid4(), uuid4()
    keepers = StepIdKeepers()
    keepers.derive_from_source(recipe)
    derived = keepers.steps.take(str(source))
    assert derived == uuid5(recipe, f"step:{source}")
    # A source id named twice in one save gets a fresh id the second time.
    assert keepers.steps.take(str(source)) != derived
    assert keepers.lines.take(str(source)) == uuid5(recipe, f"line:{source}")
    assert keepers.equipment.take(str(source)) == uuid5(recipe, f"equipment:{source}")
    # The same source step in another recipe, a new copy say, gets another id.
    again = StepIdKeepers()
    again.derive_from_source(other_recipe)
    assert again.steps.take(str(source)) != derived
    assert isinstance(again.steps.take(None), UUID)
