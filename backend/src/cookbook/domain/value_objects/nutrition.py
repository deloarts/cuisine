"""Nutrition values per 100 g of an ingredient, and the sums built from
them. Every value may be unknown."""

from dataclasses import dataclass
from dataclasses import fields

NUTRIENTS: tuple[str, ...] = (
    "kcal",
    "protein",
    "fat",
    "saturated_fat",
    "carbohydrates",
    "sugar",
    "fibre",
    "salt",
)


@dataclass(frozen=True)
class Nutrition:
    """Energy in kcal, everything else in grams."""

    kcal: float | None = None
    protein: float | None = None
    fat: float | None = None
    saturated_fat: float | None = None
    carbohydrates: float | None = None
    sugar: float | None = None
    fibre: float | None = None
    salt: float | None = None

    @property
    def is_empty(self) -> bool:
        return all(getattr(self, f.name) is None for f in fields(self))

    def scaled(self, factor: float) -> "Nutrition":
        return Nutrition(
            **{
                name: (value * factor if value is not None else None)
                for name in NUTRIENTS
                for value in (getattr(self, name),)
            }
        )

    def plus(self, other: "Nutrition") -> "Nutrition":
        """The sum; a value known on either side counts, unknown is zero."""
        result: dict[str, float | None] = {}
        for name in NUTRIENTS:
            a, b = getattr(self, name), getattr(other, name)
            result[name] = None if a is None and b is None else (a or 0.0) + (b or 0.0)
        return Nutrition(**result)

    def rounded(self, digits: int = 1) -> "Nutrition":
        return Nutrition(
            **{
                name: (round(value, digits) if value is not None else None)
                for name in NUTRIENTS
                for value in (getattr(self, name),)
            }
        )
