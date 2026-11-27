"""The translatable text of each cookbook record, one dataclass per kind.
A record keeps them in a dict keyed by content locale."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NameText:
    """Tags and ingredient categories."""

    name: str


@dataclass(frozen=True)
class UnitText:
    name: str
    plural_name: str
    abbreviation: str


@dataclass(frozen=True)
class IngredientText:
    name: str
    plural_name: str


@dataclass(frozen=True)
class RecipeText:
    title: str
    description: str = ""
    tips: str = ""


@dataclass(frozen=True)
class StepText:
    text: str


@dataclass(frozen=True)
class NoteText:
    """The note of a step ingredient, such as "finely chopped"."""

    note: str
