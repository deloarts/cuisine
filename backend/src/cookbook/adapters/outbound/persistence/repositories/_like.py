"""Case-insensitive substring matching with LIKE. A user's `%` and `_`
would otherwise act as wildcards, widening the result and costing extra
scans, so the search text is escaped and matched literally."""

from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy import func
from sqlalchemy.orm import QueryableAttribute

LIKE_ESCAPE = "\\"


def contains_pattern(search: str) -> str:
    """The LIKE pattern matching `search`, trimmed and lower-cased, anywhere
    in a value, with the backslash, `%` and `_` escaped."""
    text = search.strip().lower()
    for char in (LIKE_ESCAPE, "%", "_"):
        text = text.replace(char, LIKE_ESCAPE + char)
    return f"%{text}%"


def lower_contains(
    column: QueryableAttribute[Any] | ColumnElement[Any], pattern: str
) -> ColumnElement[bool]:
    """`column`, lower-cased, matches a pattern from `contains_pattern`."""
    return func.lower(column).like(pattern, escape=LIKE_ESCAPE)
