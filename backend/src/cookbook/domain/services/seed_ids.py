"""
The public id of a seeded reference row. A row the startup seed inserts gets
`uuid5(SEED_NAMESPACE, "<kind>:<seed key>")`, so a base unit, category,
family, tag, ingredient or equipment item has the same public id on every
Cuisine instance. Rows people or agents create keep a random `uuid4`.

The namespace is fixed forever: changing it would give every new instance
other ids than the existing ones.
"""

from uuid import UUID
from uuid import uuid5

SEED_NAMESPACE = UUID("2538fe05-07f1-4b04-a2ba-fea846a8eb65")


def seeded_public_id(kind: str, key: str) -> UUID:
    """The public id of the seeded row of `kind` ("unit", "category", "tag",
    "family", "ingredient", "equipment") with seed key `key`."""
    return uuid5(SEED_NAMESPACE, f"{kind}:{key}")
