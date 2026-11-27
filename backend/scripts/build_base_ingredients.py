"""
Builds the machine-written part of the base ingredient catalogue. It reads
the hand-edited src/bootstrap/data/ingredients.yaml (and never writes it),
looks up each entry's food in the USDA FoodData Central datasets (public
domain, CC0) and writes src/bootstrap/data/ingredients.nutrition.json,
keyed by ingredient key, with the nutrition per 100 g (FDC's values, gaps
filled from the YAML), the extended nutrients (vitamins, minerals,
cholesterol, caffeine and fatty acids, under `extended`, absent where FDC
has no value) and the density and unit conversions derived from FDC
portions. The startup seed merges both files, the YAML winning
(src/bootstrap/reference_data.py).

The FDC datasets are downloaded once into a cache directory outside the
repository and never committed. Run the script whenever ingredients.yaml
changes, review the diff of the JSON and commit both files.

Usage:
    poetry run python scripts/build_base_ingredients.py
    poetry run python scripts/build_base_ingredients.py --cache-dir /tmp/fdc
    poetry run python scripts/build_base_ingredients.py --check   # exit 1 on drift
"""

import argparse
import csv
import json
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

import yaml

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "src" / "bootstrap" / "data"
CURATED = DATA / "ingredients.yaml"
CATEGORIES = DATA / "categories.yaml"
OUTPUT = DATA / "ingredients.nutrition.json"
DEFAULT_CACHE = Path.home() / ".cache" / "cuisine" / "fdc"

FDC_BASE_URL = "https://fdc.nal.usda.gov/fdc-datasets/"
# The dataset releases the JSON was built from. Bumping a release is a
# deliberate change: rebuild, review the nutrition diff, commit.
DATASETS: dict[str, str] = {
    "foundation": "FoodData_Central_foundation_food_csv_2026-10-29",
    "sr_legacy": "FoodData_Central_sr_legacy_food_csv_2018-04",
}
ID_FILES = {"foundation": "foundation_food.csv", "sr_legacy": "sr_legacy_food.csv"}

CREDIT = {
    "en-GB": "Nutrition data: USDA FoodData Central (public domain).",
    "de-AT": "Nährwerte: USDA FoodData Central (gemeinfrei).",
}
CITATION = (
    "U.S. Department of Agriculture, Agricultural Research Service. "
    "FoodData Central. https://fdc.nal.usda.gov/"
)

# FoodData Central nutrient ids per field, in order of preference. They
# match src/cookbook/adapters/outbound/external/usda_nutrition_lookup.py.
NUTRIENT_IDS: dict[str, tuple[int, ...]] = {
    "kcal": (1008, 2047, 2048),
    "protein": (1003,),
    "fat": (1004,),
    "saturated_fat": (1258,),
    "carbohydrates": (1005,),
    "sugar": (2000, 1063),
    "fibre": (1079,),
}
SODIUM_MG = 1093
NUTRIENTS = (*NUTRIENT_IDS, "salt")

# The extended nutrients per 100 g, by the stable key and unit the backend's
# nutrient catalogue uses, and the FDC nutrient ids that give them, in order
# of preference, each with the factor that converts FDC's unit into the
# key's. FDC already states all of them in the key's unit except vitamin D
# in international units (40 IU = 1 µg). Folate DFE is computed separately.
EXTENDED_IDS: dict[str, tuple[tuple[int, float], ...]] = {
    "cholesterol_mg": ((1253, 1.0),),
    "caffeine_mg": ((1057, 1.0),),
    "vitamin_a_ug": ((1106, 1.0),),
    "vitamin_b1_mg": ((1165, 1.0),),
    "vitamin_b2_mg": ((1166, 1.0),),
    "vitamin_b6_mg": ((1175, 1.0),),
    "vitamin_b12_ug": ((1178, 1.0),),
    "vitamin_c_mg": ((1162, 1.0),),
    "vitamin_d_ug": ((1114, 1.0), (1110, 1 / 40)),
    "vitamin_e_mg": ((1109, 1.0),),
    "vitamin_k_ug": ((1185, 1.0),),
    "calcium_mg": ((1087, 1.0),),
    "iron_mg": ((1089, 1.0),),
    "magnesium_mg": ((1090, 1.0),),
    "phosphorus_mg": ((1091, 1.0),),
    "potassium_mg": ((1092, 1.0),),
    "zinc_mg": ((1095, 1.0),),
    "iodine_ug": ((1100, 1.0),),
    "monounsaturated_fat_g": ((1292, 1.0),),
    "polyunsaturated_fat_g": ((1293, 1.0),),
    "trans_fat_g": ((1257, 1.0),),
}
FOLATE_DFE, FOLATE_FOOD, FOLATE_TOTAL, FOLIC_ACID = 1190, 1187, 1177, 1186
EXTENDED = (*list(EXTENDED_IDS)[:9], "folate_ug", *list(EXTENDED_IDS)[9:])

WANTED_IDS = (
    {i for ids in NUTRIENT_IDS.values() for i in ids}
    | {i for ids in EXTENDED_IDS.values() for i, _ in ids}
    | {SODIUM_MG, FOLATE_DFE, FOLATE_FOOD, FOLATE_TOTAL, FOLIC_ACID}
)

# Millilitres per US household measure, for densities from FDC portions.
VOLUME_ML = {"cup": 236.588, "tbsp": 14.787, "tsp": 4.929, "fl oz": 29.574}

LOCALES = ("en-GB", "de-AT")


@dataclass
class Food:
    dataset: str
    description: str
    nutrients: dict[int, float] = field(default_factory=dict)
    # (measure, grams per one measure) from the FDC portion table.
    portions: list[tuple[str, float]] = field(default_factory=list)


def download(cache: Path) -> dict[str, Path]:
    """Makes sure both datasets are unpacked in the cache and returns the
    directory of each one's CSV files."""
    cache.mkdir(parents=True, exist_ok=True)
    folders: dict[str, Path] = {}
    for dataset, name in DATASETS.items():
        folder = cache / name
        if not folder.is_dir():
            archive = cache / f"{name}.zip"
            if not archive.is_file():
                print(f"Downloading {name} ...", file=sys.stderr)
                urllib.request.urlretrieve(f"{FDC_BASE_URL}{name}.zip", archive)
            with zipfile.ZipFile(archive) as zipped:
                zipped.extractall(folder)
        # The archives nest their CSV files in a folder of the same name.
        nested = folder / name
        folders[dataset] = nested if nested.is_dir() else folder
    return folders


def _rows(path: Path) -> Any:
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def load_foods(folders: dict[str, Path], wanted: set[int]) -> dict[int, Food]:
    """Reads the curated foods' descriptions, nutrients and portions."""
    foods: dict[int, Food] = {}
    for dataset, folder in folders.items():
        ids = {int(r["fdc_id"]) for r in _rows(folder / ID_FILES[dataset])} & wanted
        for row in _rows(folder / "food.csv"):
            fdc_id = int(row["fdc_id"])
            if fdc_id in ids:
                foods[fdc_id] = Food(dataset=dataset, description=row["description"])
        for row in _rows(folder / "food_nutrient.csv"):
            if not row["fdc_id"] or not row["nutrient_id"] or not row["amount"]:
                continue
            fdc_id = int(row["fdc_id"])
            nutrient_id = int(row["nutrient_id"])
            if fdc_id in ids and nutrient_id in WANTED_IDS:
                foods[fdc_id].nutrients.setdefault(nutrient_id, float(row["amount"]))
        units = {r["id"]: r["name"] for r in _rows(folder / "measure_unit.csv")}
        for row in _rows(folder / "food_portion.csv"):
            if not row["fdc_id"] or not row["gram_weight"]:
                continue
            fdc_id = int(row["fdc_id"])
            if fdc_id not in ids:
                continue
            amount = float(row["amount"] or 1) or 1.0
            unit = units.get(row["measure_unit_id"], "")
            # SR Legacy keeps the measure in `modifier` with an undetermined
            # unit; Foundation Foods name the unit and describe the portion.
            measure = row["modifier"] if unit in ("", "undetermined") else unit
            measure = " ".join(p for p in (measure, row["portion_description"]) if p).strip()
            foods[fdc_id].portions.append((measure.lower(), float(row["gram_weight"]) / amount))
    return foods


def nutrition_of(food: Food) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for name, ids in NUTRIENT_IDS.items():
        found = next((food.nutrients[i] for i in ids if i in food.nutrients), None)
        values[name] = round(found, 2) if found is not None else None
    sodium = food.nutrients.get(SODIUM_MG)
    values["salt"] = round(sodium * 2.5 / 1000, 3) if sodium is not None else None
    return values


def folate_dfe(nutrients: dict[int, float]) -> float | None:
    """Folate as dietary folate equivalents: FDC's DFE where it has one, else
    food folate plus 1.7 times the added folic acid, else total folate for a
    food stated to have no folic acid. Unknown when the folic acid is."""
    if FOLATE_DFE in nutrients:
        return nutrients[FOLATE_DFE]
    folic_acid = nutrients.get(FOLIC_ACID)
    if folic_acid is None:
        return None
    if FOLATE_FOOD in nutrients:
        return nutrients[FOLATE_FOOD] + 1.7 * folic_acid
    if folic_acid == 0 and FOLATE_TOTAL in nutrients:
        return nutrients[FOLATE_TOTAL]
    return None


def extended_of(food: Food) -> dict[str, float]:
    """The extended nutrients FDC has for the food; missing ones stay absent,
    never zero."""
    found: dict[str, float | None] = {}
    for key, ids in EXTENDED_IDS.items():
        found[key] = next(
            (food.nutrients[i] * factor for i, factor in ids if i in food.nutrients), None
        )
    found["folate_ug"] = folate_dfe(food.nutrients)
    return {key: round(value, 3) for key in EXTENDED if (value := found.get(key)) is not None}


def implied_zeros(values: dict[str, float | None]) -> dict[str, float | None]:
    """Fills the values FDC leaves out although they follow from the others:
    a food without carbohydrates has no sugar or fibre, and one without fat
    has no saturated fat."""
    filled = dict(values)
    if filled["carbohydrates"] == 0:
        for name in ("sugar", "fibre"):
            if filled[name] is None:
                filled[name] = 0.0
    if filled["fat"] == 0 and filled["saturated_fat"] is None:
        filled["saturated_fat"] = 0.0
    return filled


def density_of(food: Food) -> float | None:
    """Grams per millilitre from a plain volume portion such as "cup" or
    "tbsp"; portions of chopped or sliced food are bulk measures and skipped."""
    for measure, ml in VOLUME_ML.items():
        for text, grams in food.portions:
            if text == measure:
                return round(grams / ml, 2)
    return None


def _first(food: Food, *prefixes: str) -> float | None:
    for prefix in prefixes:
        for text, grams in food.portions:
            if text == prefix or text.startswith((f"{prefix} ", f"{prefix},", f"{prefix}(")):
                return round(grams, 1)
    return None


def conversions_of(food: Food) -> dict[str, float]:
    """Grams per count unit, where an FDC portion maps cleanly onto one."""
    derived = {
        "piece": _first(food, "medium", "fruit", "each", "whole", "large"),
        "clove": _first(food, "clove"),
        "slice": _first(food, "slice"),
        "sprig": _first(food, "sprig"),
    }
    return {unit: grams for unit, grams in derived.items() if grams}


def build(
    curated: list[dict[str, Any]], foods: dict[int, Food], category_keys: set[str]
) -> tuple[dict[str, Any], list[str]]:
    report: list[str] = []
    ingredients: dict[str, dict[str, Any]] = {}
    for entry in curated:
        key = entry["key"]
        fdc_id = entry.get("fdc_id")
        food = foods.get(fdc_id) if fdc_id else None
        manual = entry.get("nutrition")
        if fdc_id and food is None:
            report.append(f"{key}: FDC id {fdc_id} not found in the datasets")
        if food and food.description != entry.get("fdc_description"):
            report.append(f"{key}: FDC {fdc_id} is now described as {food.description!r}")
        if entry["category"] not in category_keys:
            report.append(f"{key}: unknown category {entry['category']!r}")
        if food and food.dataset != entry.get("fdc_dataset"):
            report.append(
                f"{key}: FDC {fdc_id} is in {food.dataset}, not {entry.get('fdc_dataset')}"
            )

        if food:
            nutrition = implied_zeros(nutrition_of(food))
            # Curated values only fill the gaps FDC leaves.
            for name, value in (manual or {}).items():
                if nutrition.get(name) is None:
                    nutrition[name] = value
            source = "usda"
        elif manual:
            nutrition = {name: manual.get(name) for name in NUTRIENTS}
            source = "manual"
        else:
            nutrition = dict.fromkeys(NUTRIENTS)
            source = None
        missing = [name for name, value in nutrition.items() if value is None]
        if missing:
            report.append(f"{key}: no value for {', '.join(missing)}")

        # Only what FDC yields; the YAML's own density and conversions win
        # when the seed merges, so they are left out here.
        conversions = {
            unit: grams
            for unit, grams in (conversions_of(food) if food else {}).items()
            if unit not in (entry.get("conversions") or {})
        }
        density = None
        if entry.get("density_g_per_ml") is None and food:
            density = density_of(food)

        ingredients[key] = {
            "nutrition": nutrition,
            "extended": extended_of(food) if food and source == "usda" else {},
            "nutrition_source": source,
            "usda_fdc_id": fdc_id if source == "usda" else None,
            "fdc_dataset": entry.get("fdc_dataset") if source == "usda" else None,
            "density_g_per_ml": density,
            "conversions": dict(sorted(conversions.items())),
        }
    document = {
        "source": {
            "datasets": DATASETS,
            "license": "CC0 1.0 (USDA FoodData Central is in the public domain)",
            "citation": CITATION,
            "credit": CREDIT,
        },
        "ingredients": ingredients,
    }
    return document, report


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="verify only, exit 1 on drift")
    args = parser.parse_args()

    curated = yaml.safe_load(CURATED.read_text(encoding="utf-8"))
    category_keys = {c["key"] for c in yaml.safe_load(CATEGORIES.read_text(encoding="utf-8"))}
    wanted = {int(e["fdc_id"]) for e in curated if e.get("fdc_id")}
    foods = load_foods(download(args.cache_dir), wanted)
    document, report = build(curated, foods, category_keys)
    text = render(document)

    for line in report:
        print(line, file=sys.stderr)
    print(f"{len(document['ingredients'])} ingredients, {len(report)} notes.", file=sys.stderr)

    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        if current != text:
            print(f"{args.output} is out of date; rerun without --check.", file=sys.stderr)
            return 1
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output.relative_to(BACKEND)}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
