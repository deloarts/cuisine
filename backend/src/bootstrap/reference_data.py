"""
The production reference data every instance is seeded with, read from
src/bootstrap/data/: the hand-edited units.yaml, categories.yaml, tags.yaml,
families.yaml, ingredients.yaml, ingredient_facts.yaml and equipment.yaml,
and the machine-written ingredients.nutrition.json
(scripts/build_base_ingredients.py).
Ingredients merge both files: names, category, allergens, diet markers,
season months, density and conversions from the YAML, nutrition, extended
nutrients and what FDC portions yield from the JSON, the YAML winning where
both set a value.

The startup seed, the dev seed and the data validation test read it through
`load_reference_data`.
"""

import json
from dataclasses import dataclass
from dataclasses import field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from src.cookbook.domain.entities.food_fact import FactSource
from src.cookbook.domain.entities.food_fact import FoodFact

DATA = Path(__file__).resolve().parent / "data"
LOCALES = ("en-GB", "de-AT")


@dataclass(frozen=True)
class UnitData:
    key: str
    kind: str
    to_base: float | None
    # locale -> (singular, plural, abbreviation)
    names: dict[str, tuple[str, str, str]]


@dataclass(frozen=True)
class CategoryData:
    key: str
    names: dict[str, str]


@dataclass(frozen=True)
class FamilyData:
    key: str
    names: dict[str, str]


@dataclass(frozen=True)
class EquipmentData:
    key: str
    kind: str
    names: dict[str, str]
    aliases: dict[str, list[str]] = field(default_factory=dict)
    icon: str | None = None
    basic: bool = False


@dataclass(frozen=True)
class TagData:
    key: str
    kind: str
    color: str | None
    names: dict[str, str]


@dataclass(frozen=True)
class IngredientData:
    key: str
    # locale -> (singular, plural)
    names: dict[str, tuple[str, str]]
    category: str
    allergens: list[str]
    diet_markers: list[str]
    nutrition: dict[str, float | None]
    nutrition_source: str | None
    usda_fdc_id: int | None
    fdc_dataset: str | None
    density_g_per_ml: float | None
    # unit key -> grams per unit
    conversions: dict[str, float] = field(default_factory=dict)
    proxy: bool = False
    family: str | None = None
    # locale -> other names
    aliases: dict[str, list[str]] = field(default_factory=dict)
    # Extended nutrients per 100 g by catalogue key, from the JSON.
    extended_nutrition: dict[str, float] = field(default_factory=dict)
    # Months 1 to 12 when it is in season in Austria; empty is not seasonal.
    season_months: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class ReferenceData:
    units: list[UnitData]
    categories: list[CategoryData]
    tags: list[TagData]
    families: list[FamilyData]
    ingredients: list[IngredientData]
    equipment: list[EquipmentData]
    # The data source's credit line per locale and its citation.
    credit: dict[str, str]
    citation: str
    license: str
    # The food facts of the start page, about the base ingredients.
    food_facts: list[FoodFact] = field(default_factory=list)

    def ingredient(self, key: str) -> IngredientData:
        return next(i for i in self.ingredients if i.key == key)


def _yaml(name: str) -> list[dict[str, Any]]:
    loaded = yaml.safe_load((DATA / name).read_text(encoding="utf-8"))
    return list(loaded or [])


def _ingredient(entry: dict[str, Any], machine: dict[str, Any]) -> IngredientData:
    nutrition = dict(machine.get("nutrition") or {})
    for name, value in (entry.get("nutrition") or {}).items():
        if nutrition.get(name) is None:
            nutrition[name] = value
    conversions = {**(machine.get("conversions") or {}), **(entry.get("conversions") or {})}
    density = entry.get("density_g_per_ml")
    if density is None:
        density = machine.get("density_g_per_ml")
    return IngredientData(
        key=entry["key"],
        names={locale: (names[0], names[1]) for locale, names in entry["names"].items()},
        category=entry["category"],
        allergens=sorted(entry.get("allergens") or []),
        diet_markers=sorted(entry.get("diet_markers") or []),
        nutrition=nutrition,
        nutrition_source=machine.get("nutrition_source")
        or ("manual" if entry.get("nutrition") else None),
        usda_fdc_id=machine.get("usda_fdc_id"),
        fdc_dataset=machine.get("fdc_dataset"),
        density_g_per_ml=density,
        conversions={unit: float(grams) for unit, grams in sorted(conversions.items())},
        proxy=bool(entry.get("proxy", False)),
        family=entry.get("family"),
        aliases={
            locale: [str(n) for n in names]
            for locale, names in (entry.get("aliases") or {}).items()
            if names
        },
        extended_nutrition={
            str(key): float(value)
            for key, value in (machine.get("extended") or {}).items()
            if value is not None
        },
        season_months=sorted({int(m) for m in entry.get("season") or []}),
    )


def _food_facts(entries: list[dict[str, Any]]) -> list[FoodFact]:
    """The facts of ingredient_facts.yaml, one group per ingredient with
    the articles it draws on, each fact naming the article that backs it."""
    facts: list[FoodFact] = []
    for entry in entries:
        articles = entry.get("articles") or {}
        for fact in entry.get("facts") or []:
            article = articles[fact["source"]]
            facts.append(
                FoodFact(
                    key=f"{entry['ingredient']}.{fact['key']}",
                    ingredient_key=entry["ingredient"],
                    texts={str(k): str(v).strip() for k, v in fact["text"].items()},
                    source=FactSource(
                        locale=fact["source"],
                        title=str(article["title"]),
                        revision=article.get("revision"),
                    ),
                )
            )
    return facts


@cache
def load_reference_data() -> ReferenceData:
    machine_doc = json.loads((DATA / "ingredients.nutrition.json").read_text(encoding="utf-8"))
    machine = machine_doc.get("ingredients") or {}
    source = machine_doc.get("source") or {}
    return ReferenceData(
        units=[
            UnitData(
                key=u["key"],
                kind=u["kind"],
                to_base=float(u["to_base"]) if u.get("to_base") is not None else None,
                names={locale: (n[0], n[1], n[2]) for locale, n in u["names"].items()},
            )
            for u in _yaml("units.yaml")
        ],
        categories=[
            CategoryData(key=c["key"], names=dict(c["names"])) for c in _yaml("categories.yaml")
        ],
        tags=[
            TagData(key=t["key"], kind=t["kind"], color=t.get("color"), names=dict(t["names"]))
            for t in _yaml("tags.yaml")
        ],
        families=[FamilyData(key=f["key"], names=dict(f["names"])) for f in _yaml("families.yaml")],
        ingredients=[
            _ingredient(e, machine.get(e["key"]) or {}) for e in _yaml("ingredients.yaml")
        ],
        equipment=[
            EquipmentData(
                key=e["key"],
                kind=e["kind"],
                names={str(k): str(v) for k, v in e["names"].items()},
                aliases={
                    str(locale): [str(n) for n in names]
                    for locale, names in (e.get("aliases") or {}).items()
                    if names
                },
                icon=e.get("icon"),
                basic=bool(e.get("basic", False)),
            )
            for e in _yaml("equipment.yaml")
        ],
        credit=dict(source.get("credit") or {}),
        citation=str(source.get("citation") or ""),
        license=str(source.get("license") or ""),
        food_facts=_food_facts(_yaml("ingredient_facts.yaml")),
    )
