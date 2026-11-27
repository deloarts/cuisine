"""
Resolves a public id to the page it opens by probing every registered table
with one indexed lookup each, combined into a single UNION ALL query, so a
lookup costs one round trip however many tables are registered.

Each package registers its tables from the composition root (src/bootstrap),
so Platform never imports the cookbook. A source names the table that holds
the public id and the kind and row the answer reports: a table of its own
reports itself, a child row reports its parent (a step its recipe) through
the joins it lists. A personal record names its owner column, so only its
owner resolves it. Tables that are not registered never resolve.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean
from sqlalchemy import Integer
from sqlalchemy import cast
from sqlalchemy import literal
from sqlalchemy import null
from sqlalchemy import select
from sqlalchemy import union_all
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.ports.outbound.repositories.public_id_resolver import ResolvedPublicId


@dataclass(frozen=True)
class PublicIdSource:
    """One table whose public ids resolve.

    `model` holds the public id. `kind` is the kind the answer reports and
    `target` the public id column of the row it reports, `model.public_id`
    when None. `joins` are (model, on clause) pairs from `model` to the
    target's table. `owner` is the user id column of a personal record."""

    model: Any
    kind: str
    target: Any = None
    joins: Sequence[tuple[Any, Any]] = ()
    owner: Any = None


_SOURCES: list[PublicIdSource] = []


def register_public_id_sources(sources: Sequence[PublicIdSource]) -> None:
    """Adds tables whose public ids resolve. Registering the same model
    again replaces its entry, since tests build the app more than once."""
    models = {s.model for s in sources}
    _SOURCES[:] = [s for s in _SOURCES if s.model not in models] + list(sources)


def registered_public_id_sources() -> list[PublicIdSource]:
    return list(_SOURCES)


class SqlAlchemyPublicIdResolver:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def resolve(self, public_id: UUID) -> ResolvedPublicId | None:
        if not _SOURCES:
            return None
        selects = []
        for source in _SOURCES:
            target = source.target if source.target is not None else source.model.public_id
            stmt = select(
                literal(source.kind).label("kind"),
                target.label("target"),
                literal(source.owner is not None, Boolean).label("personal"),
                (source.owner if source.owner is not None else cast(null(), Integer)).label(
                    "owner_id"
                ),
            ).select_from(source.model)
            for model, onclause in source.joins:
                stmt = stmt.join(model, onclause)
            selects.append(stmt.where(source.model.public_id == public_id))
        row = (await self._db.execute(union_all(*selects).limit(1))).first()
        if row is None:
            return None
        return ResolvedPublicId(
            kind=row.kind,
            public_id=row.target if isinstance(row.target, UUID) else UUID(str(row.target)),
            personal=bool(row.personal),
            owner_id=row.owner_id,
        )
