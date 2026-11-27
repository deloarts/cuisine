"""
The extended nutrients an ingredient may state per 100 g next to the eight
label values: vitamins, minerals, cholesterol, caffeine and fatty acids.
Each has a stable key that carries its unit, the key of its label in the
frontend's locale files and the USDA FoodData Central nutrient id it is
taken from. Ingredients store them as a map from key to amount; the API
refuses any other key.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtendedNutrient:
    key: str
    # mg, ug or g, per 100 g of the ingredient.
    unit: str
    # The key of the nutrient's label in the frontend's locale files.
    label_key: str
    # The FoodData Central nutrient id; folate counts as dietary folate
    # equivalents, which FDC either states (1190) or allows to compute.
    usda_nutrient_id: int


def _nutrient(key: str, usda_nutrient_id: int) -> ExtendedNutrient:
    unit = key.rsplit("_", 1)[1]
    return ExtendedNutrient(key, unit, f"nutrients.{key}", usda_nutrient_id)


EXTENDED_NUTRIENTS: tuple[ExtendedNutrient, ...] = (
    _nutrient("cholesterol_mg", 1253),
    _nutrient("caffeine_mg", 1057),
    # Retinol activity equivalents.
    _nutrient("vitamin_a_ug", 1106),
    _nutrient("vitamin_b1_mg", 1165),
    _nutrient("vitamin_b2_mg", 1166),
    _nutrient("vitamin_b6_mg", 1175),
    _nutrient("vitamin_b12_ug", 1178),
    # Dietary folate equivalents.
    _nutrient("folate_ug", 1190),
    _nutrient("vitamin_c_mg", 1162),
    _nutrient("vitamin_d_ug", 1114),
    _nutrient("vitamin_e_mg", 1109),
    _nutrient("vitamin_k_ug", 1185),
    _nutrient("calcium_mg", 1087),
    _nutrient("iron_mg", 1089),
    _nutrient("magnesium_mg", 1090),
    _nutrient("phosphorus_mg", 1091),
    _nutrient("potassium_mg", 1092),
    _nutrient("zinc_mg", 1095),
    _nutrient("iodine_ug", 1100),
    _nutrient("monounsaturated_fat_g", 1292),
    _nutrient("polyunsaturated_fat_g", 1293),
    _nutrient("trans_fat_g", 1257),
)

EXTENDED_KEYS: tuple[str, ...] = tuple(n.key for n in EXTENDED_NUTRIENTS)
BY_KEY: dict[str, ExtendedNutrient] = {n.key: n for n in EXTENDED_NUTRIENTS}


def clean_extended(values: Mapping[str, float | None]) -> dict[str, float]:
    """The known values in catalogue order. An unknown key or a negative
    amount raises ValueError naming it; None means unknown and is left out."""
    unknown = sorted(set(values) - set(BY_KEY))
    if unknown:
        raise ValueError(f"Unknown nutrient: {', '.join(unknown)}.")
    cleaned: dict[str, float] = {}
    for key in EXTENDED_KEYS:
        value = values.get(key)
        if value is None:
            continue
        if value < 0:
            raise ValueError(f"The nutrient {key} must not be negative.")
        cleaned[key] = float(value)
    return cleaned
