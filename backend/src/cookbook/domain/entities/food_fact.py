"""
A food fact is a short, sourced piece of trivia about one base ingredient.
The start page shows one per day. Facts ship with each release as reference
data and are never edited on an instance, so they have no table: a fact
names its ingredient by seed key and is shown only while that ingredient is
in the catalogue.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FactSource:
    """The Wikipedia article that backs a fact: the language edition by
    content locale, the article title and the revision the fact was checked
    against."""

    locale: str
    title: str
    revision: int | None


@dataclass(frozen=True)
class FoodFact:
    # "<ingredient key>.<slug>", stable across releases.
    key: str
    ingredient_key: str
    # The fact by content locale.
    texts: dict[str, str]
    source: FactSource
