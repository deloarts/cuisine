"""The download name of a `.cui` file."""

from src.cookbook.adapters.inbound.api.v1.recipe_archive_router import cui_file_name


def test_the_file_name_is_a_slug_of_the_title() -> None:
    assert cui_file_name("Marillentarte") == "marillentarte.cui"
    assert cui_file_name("Mürbteig für Kekse!") == "murbteig-fur-kekse.cui"
    assert cui_file_name("  Crème brûlée / 2 ") == "creme-brulee-2.cui"
    assert cui_file_name("寿司") == "recipe.cui"
    assert cui_file_name("a" * 200) == "a" * 80 + ".cui"
