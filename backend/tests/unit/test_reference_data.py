"""Checks the reference data the startup seed reads (src/bootstrap/data/,
merged by src/bootstrap/reference_data.py), so a bad edit to a YAML file or
a broken nutrition rebuild fails here instead of seeding wrong data into
every instance."""

from typing import Any

import pytest
import yaml

from src.bootstrap.reference_data import DATA
from src.bootstrap.reference_data import LOCALES
from src.bootstrap.reference_data import IngredientData
from src.bootstrap.reference_data import ReferenceData
from src.bootstrap.reference_data import load_reference_data
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrients import BY_KEY
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrients import EXTENDED_NUTRIENTS
from src.cookbook.domain.value_objects.nutrition import NUTRIENTS

# FDC states the energy of these with food-specific factors (cocoa's fibre
# and theobromine, the starch filler of baking powder), so the general
# Atwater estimate overshoots them by far more than the usual tolerance.
SPECIFIC_ENERGY_FACTORS = {"baking_powder", "cocoa", "cloves", "allspice"}


@pytest.fixture(scope="module")
def data() -> ReferenceData:
    return load_reference_data()


@pytest.fixture(scope="module")
def ingredients(data: ReferenceData) -> list[dict[str, Any]]:
    """The merged ingredients in the shape the checks below read."""

    def shape(i: IngredientData) -> dict[str, Any]:
        return {
            "key": i.key,
            "translations": {
                locale: {"name": n[0], "plural_name": n[1]} for locale, n in i.names.items()
            },
            "category": i.category,
            "allergens": i.allergens,
            "diet_markers": i.diet_markers,
            "nutrition": i.nutrition,
            "nutrition_source": i.nutrition_source,
            "usda_fdc_id": i.usda_fdc_id,
            "fdc_dataset": i.fdc_dataset,
            "density_g_per_ml": i.density_g_per_ml,
            "conversions": i.conversions,
        }

    return [shape(i) for i in data.ingredients]


def _is_key(key: str) -> bool:
    return key.isascii() and key.replace("_", "").isalnum() and key.islower()


def test_units_categories_and_tags_are_well_formed(data: ReferenceData) -> None:
    for kind, keys in (
        ("units", [u.key for u in data.units]),
        ("categories", [c.key for c in data.categories]),
        ("tags", [t.key for t in data.tags]),
    ):
        assert len(keys) == len(set(keys)), kind
        assert all(_is_key(k) for k in keys), kind
    for unit in data.units:
        assert UnitKind(unit.kind)
        assert set(unit.names) == set(LOCALES), unit.key
        if unit.kind in ("mass", "volume"):
            assert unit.to_base and unit.to_base > 0, unit.key
    for category in data.categories:
        assert set(category.names) == set(LOCALES), category.key
    for tag in data.tags:
        assert TagKind(tag.kind)
        assert set(tag.names) == set(LOCALES), tag.key


def test_the_credit_names_the_source(data: ReferenceData) -> None:
    assert set(data.credit) == set(LOCALES)
    assert "USDA FoodData Central" in data.credit["en-GB"]


def test_keys_are_unique_and_stable_identifiers(ingredients: list[dict[str, Any]]) -> None:
    keys = [i["key"] for i in ingredients]
    assert len(keys) == len(set(keys))
    assert all(k.isascii() and k.replace("_", "").isalnum() and k.islower() for k in keys)


def test_names_are_unique_per_locale(ingredients: list[dict[str, Any]]) -> None:
    for locale in LOCALES:
        names = [i["translations"][locale]["name"].casefold() for i in ingredients]
        duplicates = {n for n in names if names.count(n) > 1}
        assert not duplicates, f"{locale}: {sorted(duplicates)}"


def test_every_ingredient_has_both_locales(ingredients: list[dict[str, Any]]) -> None:
    for ingredient in ingredients:
        assert set(ingredient["translations"]) == set(LOCALES), ingredient["key"]
        for text in ingredient["translations"].values():
            assert text["name"].strip() and text["plural_name"].strip(), ingredient["key"]


def test_categories_are_known(data: ReferenceData, ingredients: list[dict[str, Any]]) -> None:
    keys = {c.key for c in data.categories}
    assert {i["category"] for i in ingredients} <= keys


def test_allergens_and_diet_markers_are_known(ingredients: list[dict[str, Any]]) -> None:
    allergens = {a.value for a in Allergen}
    markers = {m.value for m in DietMarker}
    for ingredient in ingredients:
        assert set(ingredient["allergens"]) <= allergens, ingredient["key"]
        assert set(ingredient["diet_markers"]) <= markers, ingredient["key"]


def test_conversions_use_seeded_count_units(
    data: ReferenceData, ingredients: list[dict[str, Any]]
) -> None:
    count_units = {u.key for u in data.units if u.kind in ("count", "other")}
    for ingredient in ingredients:
        for unit, grams in ingredient["conversions"].items():
            assert unit in count_units, (ingredient["key"], unit)
            assert 0 < grams <= 5000, (ingredient["key"], unit)


def test_densities_are_plausible(ingredients: list[dict[str, Any]]) -> None:
    for ingredient in ingredients:
        density = ingredient["density_g_per_ml"]
        assert density is None or 0.05 <= density <= 2.0, ingredient["key"]


def test_nutrition_values_are_plausible(ingredients: list[dict[str, Any]]) -> None:
    for ingredient in ingredients:
        n = ingredient["nutrition"]
        key = ingredient["key"]
        assert set(n) == set(NUTRIENTS), key
        assert all(v is None or v >= 0 for v in n.values()), key
        if n["kcal"] is not None:
            # Pure fats sit right at 9 kcal per gram; FDC lists lard at 902.
            assert 0 <= n["kcal"] <= 905, key
        # Sugars are measured and carbohydrates computed by difference, so
        # FDC's sugar can exceed the carbohydrates slightly (buttermilk).
        if n["sugar"] is not None and n["carbohydrates"] is not None:
            assert n["sugar"] <= n["carbohydrates"] * 1.15 + 0.5, key
        if n["saturated_fat"] is not None and n["fat"] is not None:
            assert n["saturated_fat"] <= n["fat"] + 0.5, key
        grams = [n[k] for k in ("protein", "fat", "carbohydrates")]
        if None not in grams:
            assert sum(grams) <= 101, key


def test_energy_agrees_with_the_macronutrients(ingredients: list[dict[str, Any]]) -> None:
    for ingredient in ingredients:
        n = ingredient["nutrition"]
        if ingredient["key"] in SPECIFIC_ENERGY_FACTORS or "alcohol" in ingredient["diet_markers"]:
            continue
        if None in (n["kcal"], n["protein"], n["fat"], n["carbohydrates"]):
            continue
        fibre = n["fibre"] or 0.0
        estimate = (
            4 * n["protein"] + 9 * n["fat"] + 4 * max(n["carbohydrates"] - fibre, 0) + 2 * fibre
        )
        assert abs(estimate - n["kcal"]) <= max(30, 0.2 * n["kcal"]), ingredient["key"]


def test_nutrition_source_matches_the_fdc_reference(ingredients: list[dict[str, Any]]) -> None:
    for ingredient in ingredients:
        if ingredient["nutrition_source"] == "usda":
            assert ingredient["usda_fdc_id"], ingredient["key"]
            assert ingredient["fdc_dataset"] in ("foundation", "sr_legacy"), ingredient["key"]
        else:
            assert ingredient["usda_fdc_id"] is None, ingredient["key"]


def test_diet_markers_agree_with_allergens(ingredients: list[dict[str, Any]]) -> None:
    """Catches the easy slips: milk without dairy, eggs without eggs, fish
    and shellfish without their marker."""
    pairs = {"milk": "dairy", "eggs": "eggs", "fish": "fish", "crustaceans": "seafood"}
    for ingredient in ingredients:
        for allergen, marker in pairs.items():
            if allergen in ingredient["allergens"]:
                assert marker in ingredient["diet_markers"], (ingredient["key"], allergen)


# The fields ingredients.yaml may use. The loader ignores anything else, so a
# misspelt `alergens` would silently seed an ingredient without allergens.
INGREDIENT_FIELDS = {
    "key",
    "names",
    "category",
    "family",
    "aliases",
    "allergens",
    "diet_markers",
    "season",
    "fdc_id",
    "fdc_dataset",
    "fdc_description",
    "density_g_per_ml",
    "conversions",
    "proxy",
    "nutrition",
    "source_note",
}

# What every member of a family must declare, as (allergen, diet marker);
# None leaves that side unchecked.
FAMILY_RULES: dict[str, tuple[str | None, str | None]] = {
    "milk": ("milk", "dairy"),
    "cream": ("milk", "dairy"),
    "butter": ("milk", "dairy"),
    "yoghurt": ("milk", "dairy"),
    "cheese": ("milk", "dairy"),
    "eggs": ("eggs", "eggs"),
    "fish": ("fish", "fish"),
    "seafood": (None, "seafood"),
    "pork": (None, "pork"),
    "beef": (None, "beef"),
    "chicken": (None, "poultry"),
    "turkey": (None, "poultry"),
    "duck": (None, "poultry"),
    "lamb": (None, "meat"),
    "game": (None, "meat"),
    "offal": (None, "meat"),
    "wine": (None, "alcohol"),
    "spirits": (None, "alcohol"),
    "nuts": ("nuts", None),
    "peanuts": ("peanuts", None),
    "soy": ("soybeans", None),
    "mustard": ("mustard", None),
    "flour": ("gluten", None),
    "pasta": ("gluten", None),
    "bread": ("gluten", None),
    "pastry": ("gluten", None),
    "asian_noodles": ("gluten", None),
}

# Members of a gluten family made from a grain or pulse without gluten.
GLUTEN_FREE = {"rice_flour", "chickpea_flour", "rice_noodles", "glass_noodles"}


@pytest.fixture(scope="module")
def raw_ingredients() -> list[dict[str, Any]]:
    """The entries of ingredients.yaml as written, before the merge."""
    loaded = yaml.safe_load((DATA / "ingredients.yaml").read_text(encoding="utf-8"))
    return list(loaded)


def test_ingredient_entries_use_only_known_fields(raw_ingredients: list[dict[str, Any]]) -> None:
    for entry in raw_ingredients:
        assert set(entry) <= INGREDIENT_FIELDS, (entry["key"], set(entry) - INGREDIENT_FIELDS)


def test_stand_ins_and_manual_profiles_say_why(raw_ingredients: list[dict[str, Any]]) -> None:
    """A proxy or a hand-written profile is a judgement call, so it carries a
    note a reviewer can check instead of a silent approximation."""
    for entry in raw_ingredients:
        manual = bool(entry.get("nutrition")) and not entry.get("fdc_id")
        if entry.get("proxy") or manual:
            note = entry.get("source_note")
            assert isinstance(note, str) and len(note.strip()) >= 20, entry["key"]


def test_categories_imply_diet_markers(data: ReferenceData) -> None:
    """Poultry is its own marker beside meat; plant drinks sit with the dairy
    but contain none."""
    for i in data.ingredients:
        markers = set(i.diet_markers)
        if i.category == "meat":
            assert markers & {"meat", "poultry"}, i.key
        if i.category == "fish":
            assert markers & {"fish", "seafood"}, i.key
        if i.category == "dairy_eggs" and i.family != "plant_drinks":
            assert markers & {"dairy", "eggs"}, i.key


def test_pork_and_beef_are_meat(data: ReferenceData) -> None:
    for i in data.ingredients:
        if {"pork", "beef"} & set(i.diet_markers):
            assert "meat" in i.diet_markers, i.key


def test_families_imply_allergens_and_diet_markers(data: ReferenceData) -> None:
    for i in data.ingredients:
        if i.family not in FAMILY_RULES:
            continue
        allergen, marker = FAMILY_RULES[i.family]
        if allergen and not (allergen == "gluten" and i.key in GLUTEN_FREE):
            assert allergen in i.allergens, (i.key, i.family, allergen)
        if marker:
            assert marker in i.diet_markers, (i.key, i.family, marker)


def test_gluten_free_exceptions_are_really_gluten_free(data: ReferenceData) -> None:
    for key in GLUTEN_FREE:
        assert "gluten" not in data.ingredient(key).allergens, key


def test_families_are_well_formed_and_referenced(data: ReferenceData) -> None:
    keys = [f.key for f in data.families]
    assert len(keys) == len(set(keys))
    assert all(_is_key(k) for k in keys)
    for family in data.families:
        assert set(family.names) == set(LOCALES), family.key
    for ingredient in data.ingredients:
        assert ingredient.family is None or ingredient.family in keys, ingredient.key


def _collisions(data: ReferenceData, locale: str) -> list[tuple[str, str, str]]:
    """Names of different entries that meet once case, diacritics and
    spacing are ignored; a family and its own members may share one."""
    from src.cookbook.domain.services.names import name_key

    family_of = {f"ingredient:{i.key}": f"family:{i.family}" for i in data.ingredients if i.family}
    owners: dict[str, str] = {}
    found: list[tuple[str, str, str]] = []
    claims = [(i.names[locale][0], f"ingredient:{i.key}") for i in data.ingredients]
    claims += [
        (alias, f"ingredient:{i.key}")
        for i in data.ingredients
        for alias in i.aliases.get(locale, [])
    ]
    claims += [(f.names[locale], f"family:{f.key}") for f in data.families]
    for name, owner in claims:
        key = name_key(name)
        assert key, owner
        previous = owners.setdefault(key, owner)
        related = family_of.get(previous) == owner or family_of.get(owner) == previous
        if previous != owner and not related:
            found.append((name, previous, owner))
    return found


def test_names_and_aliases_share_one_namespace_per_locale(data: ReferenceData) -> None:
    """The rule the API enforces (src/cookbook/domain/services/names.py)."""
    for ingredient in data.ingredients:
        assert set(ingredient.aliases) <= set(LOCALES), ingredient.key
    for locale in LOCALES:
        assert not _collisions(data, locale), locale


def test_extended_nutrients_use_catalogue_keys_and_plausible_values(data: ReferenceData) -> None:
    with_values = [i for i in data.ingredients if i.extended_nutrition]
    assert len(with_values) > 300
    for ingredient in data.ingredients:
        assert set(ingredient.extended_nutrition) <= set(EXTENDED_KEYS), ingredient.key
        for key, value in ingredient.extended_nutrition.items():
            assert value >= 0, (ingredient.key, key)
            # Per 100 g: no nutrient in grams exceeds the whole, none in
            # milligrams or micrograms exceeds 100 g either.
            limit = {"g": 100, "mg": 100_000, "ug": 100_000_000}[BY_KEY[key].unit]
            assert value <= limit, (ingredient.key, key)
        fats = ingredient.extended_nutrition
        fat = ingredient.nutrition.get("fat")
        if fat is not None:
            parts = sum(
                fats.get(k, 0.0)
                for k in ("monounsaturated_fat_g", "polyunsaturated_fat_g", "trans_fat_g")
            )
            assert parts <= fat + 1.0, ingredient.key


def test_the_build_script_fills_exactly_the_catalogue_keys() -> None:
    from scripts.build_base_ingredients import EXTENDED

    assert sorted(EXTENDED) == sorted(EXTENDED_KEYS)
    assert len({n.usda_nutrient_id for n in EXTENDED_NUTRIENTS}) == len(EXTENDED_NUTRIENTS)


def test_season_months_are_valid_and_cover_fresh_produce(data: ReferenceData) -> None:
    seasonal = [i for i in data.ingredients if i.season_months]
    assert len(seasonal) > 50
    for ingredient in seasonal:
        assert ingredient.season_months == sorted(set(ingredient.season_months)), ingredient.key
        assert all(1 <= m <= 12 for m in ingredient.season_months), ingredient.key
        # Seasonal means not all year round.
        assert len(ingredient.season_months) < 12, ingredient.key
    categories = {i.category for i in seasonal}
    assert {"vegetables", "fruit"} <= categories


def test_equipment_is_well_formed(data: ReferenceData) -> None:
    from src.cookbook.domain.value_objects.enums import EquipmentKind

    keys = [e.key for e in data.equipment]
    assert len(keys) == len(set(keys))
    assert all(_is_key(k) for k in keys)
    for item in data.equipment:
        assert EquipmentKind(item.kind)
        assert set(item.names) == set(LOCALES), item.key
        assert set(item.aliases) <= set(LOCALES), item.key
        assert item.icon is None or item.icon.replace("-", "").isalnum(), item.key
    basic = {e.key for e in data.equipment if e.basic}
    assert {"saucepan", "frying_pan"} <= basic


def test_equipment_names_are_free_across_the_catalogue(data: ReferenceData) -> None:
    """Equipment names and aliases share the namespace of ingredient and
    family names, as the API enforces."""
    from src.cookbook.domain.services.names import name_key

    for locale in LOCALES:
        taken = {
            name_key(n)
            for i in data.ingredients
            for n in [i.names[locale][0], *i.aliases.get(locale, [])]
        } | {name_key(f.names[locale]) for f in data.families}
        owners: dict[str, str] = {}
        for item in data.equipment:
            for name in [item.names[locale], *item.aliases.get(locale, [])]:
                key = name_key(name)
                assert key not in taken, (locale, name)
                assert owners.setdefault(key, item.key) == item.key, (locale, name)


# The longest a food fact may be per language, so the start page card stays
# one short paragraph.
FACT_MAX_LENGTH = 220


@pytest.fixture(scope="module")
def raw_facts() -> list[dict[str, Any]]:
    return list(yaml.safe_load((DATA / "ingredient_facts.yaml").read_text(encoding="utf-8")) or [])


def test_every_base_ingredient_has_food_facts_in_catalogue_order(
    data: ReferenceData, raw_facts: list[dict[str, Any]]
) -> None:
    assert [g["ingredient"] for g in raw_facts] == [i.key for i in data.ingredients]
    for group in raw_facts:
        assert set(group) <= {"ingredient", "articles", "facts"}, group["ingredient"]
        assert 1 <= len(group["facts"]) <= 3, group["ingredient"]


def test_food_facts_are_well_formed_and_sourced(raw_facts: list[dict[str, Any]]) -> None:
    for group in raw_facts:
        name = group["ingredient"]
        articles = group["articles"]
        assert articles and set(articles) <= set(LOCALES), name
        for article in articles.values():
            assert str(article["title"]).strip(), name
            assert isinstance(article["revision"], int), name
        slugs = [f["key"] for f in group["facts"]]
        assert len(slugs) == len(set(slugs)), name
        for fact in group["facts"]:
            assert set(fact) == {"key", "source", "text"}, (name, fact)
            assert all(part.isalnum() for part in fact["key"].split("-")), (name, fact["key"])
            assert fact["key"] == fact["key"].lower(), (name, fact["key"])
            assert fact["source"] in articles, (name, fact["key"])
            assert set(fact["text"]) == set(LOCALES), (name, fact["key"])
            for locale, text in fact["text"].items():
                assert text.strip(), (name, fact["key"], locale)
                assert len(text) <= FACT_MAX_LENGTH, (name, fact["key"], locale)
                assert "—" not in text, (name, fact["key"], locale)


def test_food_fact_keys_are_unique(data: ReferenceData) -> None:
    keys = [f.key for f in data.food_facts]
    assert len(keys) == len(set(keys))
