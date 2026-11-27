"""The exchange format layer: reading tolerates unknown fields and checks
types, the upgrade chain reads older versions and refuses newer ones, the
checked-in JSON Schemas match the format dataclasses, and a catalogue
document validates against its schema and reads back unchanged."""

import json
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Literal
from uuid import uuid4

import jsonschema
import pytest

from src.cookbook.application.services.formats.catalogue_mapper import catalogue_document
from src.cookbook.application.services.formats.codec import FormatError
from src.cookbook.application.services.formats.codec import json_schema
from src.cookbook.application.services.formats.codec import read
from src.cookbook.application.services.formats.codec import to_json
from src.cookbook.application.services.formats.recipes_v1 import RecipesDocumentV1
from src.cookbook.application.services.formats.specs import CATALOGUE
from src.cookbook.application.services.formats.specs import FORMATS
from src.cookbook.application.services.formats.specs import RECIPES
from src.cookbook.application.services.formats.specs import FormatSpec
from src.cookbook.domain.entities.equipment import Equipment
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.ingredient import UnitConversion
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText

SCHEMAS = Path(__file__).resolve().parents[2] / "formats"
NOW = datetime(2026, 11, 22, tzinfo=UTC)


@dataclass(frozen=True, kw_only=True)
class _Line:
    name: str
    amount: float | None = None


@dataclass(frozen=True, kw_only=True)
class _Doc:
    format: Literal["toy"]
    version: Literal[2]
    lines: list[_Line] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)


def test_reading_ignores_unknown_fields_and_fills_defaults() -> None:
    doc = read(
        _Doc,
        {
            "format": "toy",
            "version": 2,
            "lines": [{"name": "Salz", "amount": 3, "colour": "white"}],
            "added_later": {"anything": True},
        },
    )
    assert doc == _Doc(format="toy", version=2, lines=[_Line(name="Salz", amount=3.0)])
    assert isinstance(doc.lines[0].amount, float)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"format": "toy", "version": 2, "lines": [{}]}, "$.lines[0] lacks the required field"),
        ({"format": "toy", "version": 2, "lines": "x"}, "$.lines should be a list"),
        ({"format": "toy", "version": 2, "lines": [{"name": 1}]}, "$.lines[0].name should be"),
        (
            {"format": "toy", "version": 2, "lines": [{"name": "a", "amount": True}]},
            "should be a number",
        ),
        ({"format": "toy", "version": True}, "$.version should be 2"),
        ({"format": "other", "version": 2}, "$.format should be 'toy'"),
        ([], "$ should be an object"),
    ],
)
def test_reading_names_the_path_of_a_wrong_value(data: Any, message: str) -> None:
    with pytest.raises(FormatError, match=message.replace("$", r"\$").replace("[", r"\[")):
        read(_Doc, data)


def test_the_upgrade_chain_reads_older_versions_and_refuses_newer_ones() -> None:
    def v1_to_v2(raw: dict[str, Any]) -> dict[str, Any]:
        return {**raw, "lines": [{"name": n} for n in raw.get("names", [])]}

    spec: FormatSpec[_Doc] = FormatSpec(
        name="toy", current=2, versions={1: dict, 2: _Doc}, upgrades={1: v1_to_v2}, label="toy"
    )
    assert spec.read({"format": "toy", "version": 1, "names": ["Salz"]}).lines == [
        _Line(name="Salz")
    ]
    assert spec.read({"format": "toy", "version": 2, "lines": []}).lines == []
    with pytest.raises(FormatError, match="version 3, made by a newer Cuisine"):
        spec.read({"format": "toy", "version": 3})
    with pytest.raises(FormatError, match="not a Cuisine toy"):
        spec.read({"format": "cuisine-recipes", "version": 1})
    with pytest.raises(FormatError, match="no valid format version"):
        spec.read({"format": "toy", "version": "1"})


@pytest.mark.parametrize("spec", FORMATS, ids=lambda s: s.name)
def test_every_format_reads_every_released_version(spec: FormatSpec[Any]) -> None:
    assert set(spec.versions) == set(range(1, spec.current + 1))
    assert set(spec.upgrades) == set(range(1, spec.current))


@pytest.mark.parametrize(
    ("spec", "version"),
    [(s, v) for s in FORMATS for v in s.versions],
    ids=lambda x: x.name if isinstance(x, FormatSpec) else f"v{x}",
)
def test_the_checked_in_schemas_match_the_dataclasses(spec: FormatSpec[Any], version: int) -> None:
    path = SCHEMAS / f"{spec.name}.v{version}.schema.json"
    expected = json_schema(
        spec.versions[version],
        schema_id=f"urn:cuisine:format:{spec.name}:{version}",
        title=f"{spec.name} version {version}",
    )
    assert json.loads(path.read_text(encoding="utf-8")) == expected, (
        "Run scripts/export_formats.py."
    )


def test_a_minimal_recipes_document_reads_with_defaults() -> None:
    document = RECIPES.read(
        {
            "format": "cuisine-recipes",
            "version": 1,
            "recipes": [{"id": "r1", "snapshot": {"original_locale": "de-AT"}}],
        }
    )
    assert isinstance(document, RecipesDocumentV1)
    assert document.instance_id is None
    assert document.recipes[0].variations == []
    assert document.recipes[0].snapshot.base_servings == 4


def _catalogue_records() -> dict[str, Any]:
    g = Unit(
        id=1,
        public_id=uuid4(),
        code="g",
        kind=UnitKind.MASS,
        to_base=1.0,
        created=NOW,
        translations={"de-AT": UnitText("Gramm", "Gramm", "g")},
        seed_key="g",
    )
    category = IngredientCategory(
        id=2, public_id=uuid4(), created=NOW, translations={"de-AT": NameText("Obst")}
    )
    family = IngredientFamily(
        id=3, public_id=uuid4(), created=NOW, translations={"de-AT": NameText("Äpfel")}
    )
    apple = Ingredient(
        id=4,
        public_id=uuid4(),
        owner_id=None,
        original_locale="de-AT",
        created=NOW,
        changed=NOW,
        translations={"de-AT": IngredientText("Apfel", "Äpfel")},
        category_id=2,
        family_id=3,
        aliases={"de-AT": ["Paradiesapfel"]},
        nutrition=Nutrition(kcal=52, sugar=10.4),
        extended_nutrition={"vitamin_c_mg": 4.6},
        season_months=[9, 10, 8],
        density_g_per_ml=0.8,
        conversions=[UnitConversion(unit_id=1, grams=180)],
        allergens=[Allergen.CELERY],
        diet_markers=[DietMarker.HONEY],
    )
    tag = Tag(
        id=5,
        public_id=uuid4(),
        kind=TagKind.MEAL,
        created=NOW,
        translations={"de-AT": NameText("Jause")},
        color="#d97706",
    )
    whisk = Equipment(
        id=6,
        public_id=uuid4(),
        kind=EquipmentKind.UTENSIL,
        created=NOW,
        changed=NOW,
        translations={"de-AT": NameText("Schneebesen")},
        basic=True,
    )
    return {
        "units": [g],
        "tags": [tag],
        "categories": [category],
        "families": [family],
        "ingredients": [apple],
        "equipment": [whisk],
    }


def test_a_catalogue_document_validates_and_reads_back_unchanged() -> None:
    records = _catalogue_records()
    document = catalogue_document(exported_at=NOW.isoformat(), instance_id=None, **records)
    data = json.loads(json.dumps(to_json(document)))
    schema = json.loads((SCHEMAS / "cuisine-catalogue.v1.schema.json").read_text("utf-8"))
    jsonschema.validate(data, schema)
    assert CATALOGUE.read(data) == document

    apple = next(iter(data["ingredients"].values()))
    assert apple["category"]["names"] == {"de-AT": "Obst"}
    assert apple["family"]["id"] == str(records["families"][0].public_id)
    assert apple["conversions"] == [{"unit_id": str(records["units"][0].public_id), "grams": 180}]
    assert apple["season_months"] == [8, 9, 10]
    assert apple["allergens"] == ["celery"] and apple["diet_markers"] == ["honey"]
    unit = next(iter(data["units"].values()))
    assert unit["abbreviations"] == {"de-AT": "g"} and unit["kind"] == "mass"
