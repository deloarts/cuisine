from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.personal_models import FoodRestrictionModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeFavouriteModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeNoteModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeRatingModel
from src.cookbook.domain.entities.personal import CookNote
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.entities.personal import Rating
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import RestrictionKind
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id
from src.shared_kernel.domain.services.clock import now_utc


class SqlAlchemyFavouriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def add(self, user_id: int, recipe_id: int) -> None:
        if await self._db.get(RecipeFavouriteModel, (user_id, recipe_id)) is None:
            self._db.add(
                RecipeFavouriteModel(user_id=user_id, recipe_id=recipe_id, created=now_utc())
            )
            await self._db.flush()

    async def remove(self, user_id: int, recipe_id: int) -> None:
        await self._db.execute(
            delete(RecipeFavouriteModel).where(
                RecipeFavouriteModel.user_id == user_id,
                RecipeFavouriteModel.recipe_id == recipe_id,
            )
        )

    async def favourite_ids(self, user_id: int, recipe_ids: list[int]) -> set[int]:
        if not recipe_ids:
            return set()
        rows = await self._db.scalars(
            select(RecipeFavouriteModel.recipe_id).where(
                RecipeFavouriteModel.user_id == user_id,
                RecipeFavouriteModel.recipe_id.in_(recipe_ids),
            )
        )
        return set(rows.all())

    async def recipe_ids_of(self, user_id: int) -> list[int]:
        rows = await self._db.scalars(
            select(RecipeFavouriteModel.recipe_id)
            .where(RecipeFavouriteModel.user_id == user_id)
            .order_by(RecipeFavouriteModel.created.desc())
        )
        return list(rows.all())


def _rating(row: RecipeRatingModel) -> Rating:
    return Rating(
        id=row.id,
        public_id=row.public_id,
        user_id=row.user_id,
        recipe_id=row.recipe_id,
        stars=row.stars,
        comment=row.comment,
        created=row.created,
        changed=row.changed,
        variation_id=row.variation_id,
    )


class SqlAlchemyRatingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get_own(
        self, user_id: int, recipe_id: int, variation_id: int | None = None
    ) -> Rating | None:
        """The user's rating of the recipe itself, or of one of its
        variations."""
        row = await self._db.scalar(
            select(RecipeRatingModel).where(
                RecipeRatingModel.user_id == user_id,
                RecipeRatingModel.recipe_id == recipe_id,
                RecipeRatingModel.variation_id.is_(None)
                if variation_id is None
                else RecipeRatingModel.variation_id == variation_id,
            )
        )
        return _rating(row) if row is not None else None

    async def list_for_user(self, user_id: int) -> list[Rating]:
        rows = await self._db.scalars(
            select(RecipeRatingModel)
            .where(RecipeRatingModel.user_id == user_id)
            .order_by(RecipeRatingModel.id)
        )
        return [_rating(r) for r in rows.all()]

    async def own_many(self, user_id: int, recipe_ids: list[int]) -> dict[int, Rating]:
        if not recipe_ids:
            return {}
        rows = await self._db.scalars(
            select(RecipeRatingModel).where(
                RecipeRatingModel.user_id == user_id,
                RecipeRatingModel.recipe_id.in_(recipe_ids),
                RecipeRatingModel.variation_id.is_(None),
            )
        )
        return {r.recipe_id: _rating(r) for r in rows.all()}

    async def stats(
        self, recipe_ids: list[int], *, overall: bool = False
    ) -> dict[int, tuple[float, int]]:
        """Average and count per recipe of the ratings of the recipe itself,
        or with `overall` of the recipe and all its variations together."""
        if not recipe_ids:
            return {}
        stmt = select(
            RecipeRatingModel.recipe_id,
            func.avg(RecipeRatingModel.stars),
            func.count(RecipeRatingModel.id),
        ).where(RecipeRatingModel.recipe_id.in_(recipe_ids))
        if not overall:
            stmt = stmt.where(RecipeRatingModel.variation_id.is_(None))
        rows = await self._db.execute(stmt.group_by(RecipeRatingModel.recipe_id))
        return {rid: (round(float(avg), 2), int(count)) for rid, avg, count in rows.all()}

    async def variation_stats(self, variation_ids: list[int]) -> dict[int, tuple[float, int]]:
        if not variation_ids:
            return {}
        rows = await self._db.execute(
            select(
                RecipeRatingModel.variation_id,
                func.avg(RecipeRatingModel.stars),
                func.count(RecipeRatingModel.id),
            )
            .where(RecipeRatingModel.variation_id.in_(variation_ids))
            .group_by(RecipeRatingModel.variation_id)
        )
        return {
            vid: (round(float(avg), 2), int(count))
            for vid, avg, count in rows.all()
            if vid is not None
        }

    async def save(self, rating: Rating) -> Rating:
        row = await self._db.get(RecipeRatingModel, rating.id) if rating.id else None
        if row is None:
            row = RecipeRatingModel(
                public_id=rating.public_id,
                user_id=rating.user_id,
                recipe_id=rating.recipe_id,
                variation_id=rating.variation_id,
                created=rating.created,
            )
            self._db.add(row)
        row.stars = rating.stars
        row.comment = rating.comment
        row.changed = rating.changed
        await self._db.flush()
        return _rating(row)

    async def delete(self, rating: Rating) -> None:
        await self._db.execute(delete(RecipeRatingModel).where(RecipeRatingModel.id == rating.id))


def _note(row: RecipeNoteModel) -> CookNote:
    return CookNote(
        id=row.id,
        public_id=row.public_id,
        user_id=row.user_id,
        recipe_id=row.recipe_id,
        text=row.text,
        changed=row.changed,
    )


class SqlAlchemyCookNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get_own(self, user_id: int, recipe_id: int) -> CookNote | None:
        row = await self._db.scalar(
            select(RecipeNoteModel).where(
                RecipeNoteModel.user_id == user_id, RecipeNoteModel.recipe_id == recipe_id
            )
        )
        return _note(row) if row is not None else None

    async def list_for_user(self, user_id: int) -> list[CookNote]:
        rows = await self._db.scalars(
            select(RecipeNoteModel)
            .where(RecipeNoteModel.user_id == user_id)
            .order_by(RecipeNoteModel.id)
        )
        return [_note(r) for r in rows.all()]

    async def save(self, note: CookNote) -> CookNote:
        row = await self._db.get(RecipeNoteModel, note.id) if note.id else None
        if row is None:
            row = RecipeNoteModel(
                public_id=note.public_id, user_id=note.user_id, recipe_id=note.recipe_id
            )
            self._db.add(row)
        row.text = note.text
        row.changed = note.changed
        await self._db.flush()
        note.id = row.id
        return note

    async def delete(self, note: CookNote) -> None:
        await self._db.execute(delete(RecipeNoteModel).where(RecipeNoteModel.id == note.id))


def _restriction(row: FoodRestrictionModel) -> FoodRestriction:
    known = {a.value for a in Allergen}
    diets = {d.value for d in Diet}
    return FoodRestriction(
        id=row.id,
        public_id=row.public_id,
        user_id=row.user_id,
        kind=RestrictionKind(row.kind),
        allergen=Allergen(row.allergen) if row.allergen in known else None,
        ingredient_id=row.ingredient_id,
        diet=Diet(row.diet) if row.diet in diets else None,
        family_id=row.family_id,
        note=row.note,
        created=row.created,
    )


class SqlAlchemyFoodRestrictionRepository:
    """Every query is scoped to the users asked for. Besides a user's own
    list, only the dinner guest check reads the restrictions of other users,
    who opted in, and never hands them out."""

    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_for_user(self, user_id: int) -> list[FoodRestriction]:
        rows = await self._db.scalars(
            select(FoodRestrictionModel)
            .where(FoodRestrictionModel.user_id == user_id)
            .order_by(FoodRestrictionModel.created, FoodRestrictionModel.id)
        )
        return [_restriction(r) for r in rows.all()]

    async def list_for_users(self, user_ids: list[int]) -> list[FoodRestriction]:
        if not user_ids:
            return []
        rows = await self._db.scalars(
            select(FoodRestrictionModel).where(FoodRestrictionModel.user_id.in_(user_ids))
        )
        return [_restriction(r) for r in rows.all()]

    async def get_own(self, user_id: int, public_id: str) -> FoodRestriction | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(
            select(FoodRestrictionModel).where(
                FoodRestrictionModel.public_id == uid, FoodRestrictionModel.user_id == user_id
            )
        )
        return _restriction(row) if row is not None else None

    async def save(self, restriction: FoodRestriction) -> FoodRestriction:
        row = await self._db.get(FoodRestrictionModel, restriction.id) if restriction.id else None
        if row is None:
            row = FoodRestrictionModel(
                public_id=restriction.public_id,
                user_id=restriction.user_id,
                created=restriction.created,
            )
            self._db.add(row)
        row.kind = restriction.kind.value
        row.allergen = restriction.allergen.value if restriction.allergen else None
        row.ingredient_id = restriction.ingredient_id
        row.diet = restriction.diet.value if restriction.diet else None
        row.family_id = restriction.family_id
        row.note = restriction.note
        await self._db.flush()
        return _restriction(row)

    async def delete(self, restriction: FoodRestriction) -> None:
        await self._db.execute(
            delete(FoodRestrictionModel).where(FoodRestrictionModel.id == restriction.id)
        )

    async def delete_for_user(self, user_id: int) -> int:
        result = await self._db.execute(
            delete(FoodRestrictionModel).where(FoodRestrictionModel.user_id == user_id)
        )
        return int(getattr(result, "rowcount", 0) or 0)
