"""Recipe variations, oldest first per recipe."""

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.variation_models import RecipeVariationModel
from src.cookbook.domain.entities.variation import RecipeVariation
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id


def _entity(row: RecipeVariationModel) -> RecipeVariation:
    return RecipeVariation(
        id=row.id,
        public_id=row.public_id,
        recipe_id=row.recipe_id,
        author_id=row.author_id,
        name=row.name,
        note=row.note,
        locale=row.locale,
        private=row.private,
        based_on_revision=row.based_on_revision,
        changes=[dict(c) for c in row.changes or []],
        created=row.created,
        changed=row.changed,
        origin_public_id=row.origin_public_id,
        source_author_name=row.source_author_name,
    )


class SqlAlchemyRecipeVariationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get_by_public_id(self, public_id: str) -> RecipeVariation | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(RecipeVariationModel).where(RecipeVariationModel.public_id == uid)
        )
        return _entity(row) if row is not None else None

    async def get_many(self, ids: list[int]) -> list[RecipeVariation]:
        if not ids:
            return []
        rows = await self._db.scalars(
            select(RecipeVariationModel).where(RecipeVariationModel.id.in_(sorted(set(ids))))
        )
        return [_entity(r) for r in rows.all()]

    async def for_recipe(self, recipe_id: int) -> list[RecipeVariation]:
        return (await self.for_recipes([recipe_id])).get(recipe_id, [])

    async def for_recipes(self, recipe_ids: list[int]) -> dict[int, list[RecipeVariation]]:
        found: dict[int, list[RecipeVariation]] = {i: [] for i in recipe_ids}
        if not recipe_ids:
            return found
        rows = await self._db.scalars(
            select(RecipeVariationModel)
            .where(RecipeVariationModel.recipe_id.in_(sorted(set(recipe_ids))))
            .order_by(RecipeVariationModel.created, RecipeVariationModel.id)
        )
        for row in rows.all():
            found.setdefault(row.recipe_id, []).append(_entity(row))
        return found

    async def by_author(self, author_id: int) -> list[RecipeVariation]:
        rows = await self._db.scalars(
            select(RecipeVariationModel)
            .where(RecipeVariationModel.author_id == author_id)
            .order_by(RecipeVariationModel.id)
        )
        return [_entity(r) for r in rows.all()]

    async def visible_counts(self, recipe_ids: list[int], viewer_id: int) -> dict[int, int]:
        """Per recipe, the variations the viewer may see given they see the
        recipe: every shared one and their own private ones."""
        if not recipe_ids:
            return {}
        rows = await self._db.execute(
            select(RecipeVariationModel.recipe_id, func.count(RecipeVariationModel.id))
            .where(
                RecipeVariationModel.recipe_id.in_(sorted(set(recipe_ids))),
                or_(
                    RecipeVariationModel.private.is_(False),
                    RecipeVariationModel.author_id == viewer_id,
                ),
            )
            .group_by(RecipeVariationModel.recipe_id)
        )
        return {recipe_id: int(count) for recipe_id, count in rows.all()}

    async def save(self, variation: RecipeVariation) -> RecipeVariation:
        row = await self._db.get(RecipeVariationModel, variation.id) if variation.id else None
        if row is None:
            row = RecipeVariationModel(
                public_id=variation.public_id,
                recipe_id=variation.recipe_id,
                created=variation.created,
            )
            self._db.add(row)
        row.author_id = variation.author_id
        row.name = variation.name
        row.note = variation.note
        row.locale = variation.locale
        row.private = variation.private
        row.based_on_revision = variation.based_on_revision
        row.changes = [dict(c) for c in variation.changes]
        row.changed = variation.changed
        row.origin_public_id = variation.origin_public_id
        row.source_author_name = variation.source_author_name
        await self._db.flush()
        return _entity(row)

    async def delete(self, variation: RecipeVariation) -> None:
        await self._db.execute(
            delete(RecipeVariationModel).where(RecipeVariationModel.id == variation.id)
        )
        await self._db.flush()
