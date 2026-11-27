from datetime import datetime

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.revision_models import RecipeRevisionModel
from src.cookbook.domain.entities.revision import RecipeRevision
from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import RevisionKind


def _entity(row: RecipeRevisionModel) -> RecipeRevision:
    return RecipeRevision(
        id=row.id,
        public_id=row.public_id,
        recipe_id=row.recipe_id,
        number=row.number,
        kind=RevisionKind(row.kind),
        created=row.created,
        created_via=CreatedVia(row.created_via),
        author_id=row.author_id,
        restored_from=row.restored_from,
        note=row.note,
        snapshot=dict(row.snapshot or {}),
        credited_author_id=row.credited_author_id,
    )


class SqlAlchemyRecipeRevisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def next_number(self, recipe_id: int) -> int:
        highest = await self._db.scalar(
            select(func.max(RecipeRevisionModel.number)).where(
                RecipeRevisionModel.recipe_id == recipe_id
            )
        )
        return int(highest or 0) + 1

    async def add(self, revision: RecipeRevision) -> RecipeRevision:
        row = RecipeRevisionModel(
            public_id=revision.public_id,
            recipe_id=revision.recipe_id,
            number=revision.number,
            snapshot=revision.snapshot,
            author_id=revision.author_id,
            created_via=revision.created_via.value,
            kind=revision.kind.value,
            restored_from=revision.restored_from,
            note=revision.note,
            created=revision.created,
            credited_author_id=revision.credited_author_id,
        )
        self._db.add(row)
        await self._db.flush()
        return _entity(row)

    async def page(
        self, recipe_id: int, *, limit: int, offset: int
    ) -> tuple[list[RecipeRevision], int]:
        """Newest first."""
        total = await self._db.scalar(
            select(func.count())
            .select_from(RecipeRevisionModel)
            .where(RecipeRevisionModel.recipe_id == recipe_id)
        )
        rows = await self._db.scalars(
            select(RecipeRevisionModel)
            .where(RecipeRevisionModel.recipe_id == recipe_id)
            .order_by(RecipeRevisionModel.number.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_entity(r) for r in rows.all()], int(total or 0)

    async def get(self, recipe_id: int, number: int) -> RecipeRevision | None:
        row = await self._db.scalar(
            select(RecipeRevisionModel).where(
                RecipeRevisionModel.recipe_id == recipe_id, RecipeRevisionModel.number == number
            )
        )
        return _entity(row) if row is not None else None

    async def latest_number(self, recipe_id: int) -> int | None:
        highest = await self._db.scalar(
            select(func.max(RecipeRevisionModel.number)).where(
                RecipeRevisionModel.recipe_id == recipe_id
            )
        )
        return int(highest) if highest is not None else None

    async def for_recipes(self, recipe_ids: list[int]) -> list[RecipeRevision]:
        if not recipe_ids:
            return []
        rows = await self._db.scalars(
            select(RecipeRevisionModel)
            .where(RecipeRevisionModel.recipe_id.in_(recipe_ids))
            .order_by(RecipeRevisionModel.recipe_id, RecipeRevisionModel.number)
        )
        return [_entity(r) for r in rows.all()]

    async def delete_older_than(self, cutoff: datetime) -> int:
        """Deletes revisions created before `cutoff`, except each recipe's
        newest, so every recipe keeps its current state on record."""
        newest = (
            select(
                func.max(RecipeRevisionModel.number).label("number"), RecipeRevisionModel.recipe_id
            )
            .group_by(RecipeRevisionModel.recipe_id)
            .subquery()
        )
        keep = select(RecipeRevisionModel.id).join(
            newest,
            (newest.c.recipe_id == RecipeRevisionModel.recipe_id)
            & (newest.c.number == RecipeRevisionModel.number),
        )
        result = await self._db.execute(
            delete(RecipeRevisionModel).where(
                RecipeRevisionModel.created < cutoff, RecipeRevisionModel.id.not_in(keep)
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)
