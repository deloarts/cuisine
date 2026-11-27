"""Helpers the repositories share."""

import uuid
from dataclasses import fields


def parse_public_id(value: str) -> uuid.UUID | None:
    """The UUID of an API-supplied id, None when it is not one, so a
    malformed id answers 404 like an unknown one."""
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def entity_from_row[E](entity_cls: type[E], row: object) -> E:
    """Builds a dataclass entity from a row whose columns carry the same
    names as the entity's fields. Only for entities without enums or
    derived fields."""
    names = [f.name for f in fields(entity_cls)]  # type: ignore[arg-type]
    return entity_cls(**{name: getattr(row, name) for name in names})


def copy_entity_to_row(entity: object, row: object, *, skip: frozenset[str]) -> None:
    """Writes every entity field onto the row, except `skip` (always id and
    public_id, which an update must never touch)."""
    for f in fields(entity):  # type: ignore[arg-type]
        if f.name in skip or f.name in {"id", "public_id"}:
            continue
        setattr(row, f.name, getattr(entity, f.name))
