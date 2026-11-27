"""Small readers shared by the `.cui` import and the peer mirrors, so the
same document value behaves the same on both paths."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID


def first_name(names: Mapping[str, Any], preferred: str | None = None) -> str:
    """The name in `preferred`, else in English, else in German, else in the
    first other locale by code; empty when no locale has one."""
    for locale in (preferred, "en-GB", "de-AT", *sorted(names)):
        if locale and names.get(locale):
            return str(names[locale])
    return ""


def parse_uuid(value: str | None) -> UUID | None:
    """The UUID `value` spells, or None for an empty, missing or malformed
    value."""
    try:
        return UUID(value) if value else None
    except ValueError:
        return None
