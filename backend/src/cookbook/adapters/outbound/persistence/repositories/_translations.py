"""Reading and replacing the rows of a translation table, which every
translatable cookbook record keeps keyed by (parent id, locale)."""

from collections.abc import Callable
from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def load_translations[T](
    db: AsyncSession,
    model: Any,
    parent_column: str,
    parent_ids: list[int],
    make: Callable[[Any], T],
) -> dict[int, dict[str, T]]:
    result: dict[int, dict[str, T]] = {i: {} for i in parent_ids}
    if not parent_ids:
        return result
    column = getattr(model, parent_column)
    rows = await db.scalars(select(model).where(column.in_(parent_ids)))
    for row in rows.all():
        result.setdefault(getattr(row, parent_column), {})[row.locale] = make(row)
    return result


async def replace_translations[T](
    db: AsyncSession,
    model: Any,
    parent_column: str,
    parent_id: int,
    translations: Mapping[str, T],
    to_columns: Callable[[T], dict[str, Any]],
) -> None:
    await db.execute(delete(model).where(getattr(model, parent_column) == parent_id))
    for locale, text in sorted(translations.items()):
        db.add(model(**{parent_column: parent_id, "locale": locale, **to_columns(text)}))
