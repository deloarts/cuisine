"""
Recipes with their translations, tags, steps and step ingredients. A save
replaces the steps as a whole, which matches how the editor sends them, and
writes each step and line with the public id its entity carries.

Search runs on every translation of a recipe and on the names of its
ingredients. On Postgres the title and description are matched with full
text search in the dictionary of each translation's language, plus a
substring match on the title for words still being typed; elsewhere, as in
the SQLite test suite, a substring match stands in.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import delete
from sqlalchemy import false
from sqlalchemy import func
from sqlalchemy import literal
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.cooking_models import MealPlanEntryModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import StepEquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import (
    StepEquipmentTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeFavouriteModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeCoEditorModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeGroupShareModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import (
    RecipeIngredientTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipePeerShareModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeStepModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import (
    RecipeStepTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeTagModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeTranslationModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeUserShareModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import StepIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import (
    StepIngredientTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.repositories._like import contains_pattern
from src.cookbook.adapters.outbound.persistence.repositories._like import lower_contains
from src.cookbook.adapters.outbound.persistence.repositories._translations import load_translations
from src.cookbook.adapters.outbound.persistence.repositories._translations import (
    replace_translations,
)
from src.cookbook.adapters.outbound.persistence.repositories.ingredient_repository import (
    name_matches,
)
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepEquipment
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery
from src.cookbook.ports.outbound.repositories.recipe_repository import StepImageHit
from src.cookbook.ports.outbound.repositories.recipe_repository import StepImageQuery
from src.platform.adapters.outbound.persistence.repositories._common import parse_public_id


def _recipe_text(row: RecipeTranslationModel) -> RecipeText:
    return RecipeText(title=row.title, description=row.description, tips=row.tips)


def _using_ingredient(condition: Any) -> Any:
    """The ids of recipes with a step line matching `condition`."""
    return (
        select(RecipeStepModel.recipe_id)
        .join(StepIngredientModel, StepIngredientModel.step_id == RecipeStepModel.id)
        .where(condition)
    )


def _total_minutes() -> Any:
    return (
        func.coalesce(RecipeModel.prep_minutes, 0)
        + func.coalesce(RecipeModel.cook_minutes, 0)
        + func.coalesce(RecipeModel.rest_minutes, 0)
    )


class SqlAlchemyRecipeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    # ── Loading ──────────────────────────────────────────────────────

    async def _entities(self, rows: list[RecipeModel]) -> list[Recipe]:
        ids = [r.id for r in rows]
        if not ids:
            return []
        texts = await load_translations(
            self._db, RecipeTranslationModel, "recipe_id", ids, _recipe_text
        )
        tags: dict[int, list[int]] = {i: [] for i in ids}
        for recipe_id, tag_id in (
            await self._db.execute(
                select(RecipeTagModel.recipe_id, RecipeTagModel.tag_id).where(
                    RecipeTagModel.recipe_id.in_(ids)
                )
            )
        ).all():
            tags[recipe_id].append(tag_id)
        user_shares: dict[int, list[int]] = {i: [] for i in ids}
        for recipe_id, user_id in (
            await self._db.execute(
                select(RecipeUserShareModel.recipe_id, RecipeUserShareModel.user_id).where(
                    RecipeUserShareModel.recipe_id.in_(ids)
                )
            )
        ).all():
            user_shares[recipe_id].append(user_id)
        group_shares: dict[int, list[int]] = {i: [] for i in ids}
        for recipe_id, group_id in (
            await self._db.execute(
                select(RecipeGroupShareModel.recipe_id, RecipeGroupShareModel.group_id).where(
                    RecipeGroupShareModel.recipe_id.in_(ids)
                )
            )
        ).all():
            group_shares[recipe_id].append(group_id)
        peer_shares: dict[int, list[int]] = {i: [] for i in ids}
        for recipe_id, peer_id in (
            await self._db.execute(
                select(RecipePeerShareModel.recipe_id, RecipePeerShareModel.peer_id).where(
                    RecipePeerShareModel.recipe_id.in_(ids)
                )
            )
        ).all():
            peer_shares[recipe_id].append(peer_id)
        co_editors: dict[int, list[int]] = {i: [] for i in ids}
        for recipe_id, user_id in (
            await self._db.execute(
                select(RecipeCoEditorModel.recipe_id, RecipeCoEditorModel.user_id).where(
                    RecipeCoEditorModel.recipe_id.in_(ids)
                )
            )
        ).all():
            co_editors[recipe_id].append(user_id)

        step_rows = list(
            (
                await self._db.scalars(
                    select(RecipeStepModel)
                    .where(RecipeStepModel.recipe_id.in_(ids))
                    .order_by(RecipeStepModel.recipe_id, RecipeStepModel.position)
                )
            ).all()
        )
        step_ids = [s.id for s in step_rows]
        step_texts = await load_translations(
            self._db,
            RecipeStepTranslationModel,
            "step_id",
            step_ids,
            lambda r: StepText(text=r.text),
        )
        si_rows = (
            list(
                (
                    await self._db.scalars(
                        select(StepIngredientModel)
                        .where(StepIngredientModel.step_id.in_(step_ids))
                        .order_by(StepIngredientModel.step_id, StepIngredientModel.position)
                    )
                ).all()
            )
            if step_ids
            else []
        )
        notes = await load_translations(
            self._db,
            StepIngredientTranslationModel,
            "step_ingredient_id",
            [s.id for s in si_rows],
            lambda r: NoteText(note=r.note),
        )
        ingredients_by_step: dict[int, list[StepIngredient]] = {i: [] for i in step_ids}
        for si in si_rows:
            ingredients_by_step[si.step_id].append(
                StepIngredient(
                    public_id=si.public_id,
                    ingredient_id=si.ingredient_id,
                    sub_recipe_id=si.sub_recipe_id,
                    amount=si.amount,
                    unit_id=si.unit_id,
                    translations=notes.get(si.id, {}),
                )
            )
        se_rows = (
            list(
                (
                    await self._db.scalars(
                        select(StepEquipmentModel)
                        .where(StepEquipmentModel.step_id.in_(step_ids))
                        .order_by(StepEquipmentModel.step_id, StepEquipmentModel.position)
                    )
                ).all()
            )
            if step_ids
            else []
        )
        equipment_notes = await load_translations(
            self._db,
            StepEquipmentTranslationModel,
            "step_equipment_id",
            [s.id for s in se_rows],
            lambda r: NoteText(note=r.note),
        )
        equipment_by_step: dict[int, list[StepEquipment]] = {i: [] for i in step_ids}
        for se in se_rows:
            equipment_by_step[se.step_id].append(
                StepEquipment(
                    public_id=se.public_id,
                    equipment_id=se.equipment_id,
                    count=se.count,
                    translations=equipment_notes.get(se.id, {}),
                )
            )
        ri_rows = list(
            (
                await self._db.scalars(
                    select(RecipeIngredientModel)
                    .where(RecipeIngredientModel.recipe_id.in_(ids))
                    .order_by(RecipeIngredientModel.recipe_id, RecipeIngredientModel.position)
                )
            ).all()
        )
        declared_notes = await load_translations(
            self._db,
            RecipeIngredientTranslationModel,
            "recipe_ingredient_id",
            [r.id for r in ri_rows],
            lambda r: NoteText(note=r.note),
        )
        declared: dict[int, list[StepIngredient]] = {i: [] for i in ids}
        for ri in ri_rows:
            declared[ri.recipe_id].append(
                StepIngredient(
                    public_id=ri.public_id,
                    ingredient_id=ri.ingredient_id,
                    sub_recipe_id=ri.sub_recipe_id,
                    amount=ri.amount,
                    unit_id=ri.unit_id,
                    translations=declared_notes.get(ri.id, {}),
                )
            )
        steps_by_recipe: dict[int, list[RecipeStep]] = {i: [] for i in ids}
        for s in step_rows:
            steps_by_recipe[s.recipe_id].append(
                RecipeStep(
                    public_id=s.public_id,
                    translations=step_texts.get(s.id, {}),
                    duration_minutes=s.duration_minutes,
                    image_file_id=s.image_file_id,
                    ingredients=ingredients_by_step.get(s.id, []),
                    equipment=equipment_by_step.get(s.id, []),
                )
            )
        return [
            Recipe(
                id=r.id,
                public_id=r.public_id,
                owner_id=r.owner_id,
                original_locale=r.original_locale,
                created=r.created,
                changed=r.changed,
                translations=texts.get(r.id, {}),
                status=RecipeStatus(r.status),
                visibility=RecipeVisibility(r.visibility),
                shared_user_ids=sorted(user_shares.get(r.id, [])),
                shared_group_ids=sorted(group_shares.get(r.id, [])),
                shared_peer_ids=sorted(peer_shares.get(r.id, [])),
                co_editor_ids=sorted(co_editors.get(r.id, [])),
                based_on_recipe_id=r.based_on_recipe_id,
                origin_instance_id=r.origin_instance_id,
                origin_public_id=r.origin_public_id,
                mirror_peer_id=r.mirror_peer_id,
                peer_capped=r.peer_capped,
                base_servings=r.base_servings,
                prep_minutes=r.prep_minutes,
                cook_minutes=r.cook_minutes,
                rest_minutes=r.rest_minutes,
                difficulty=Difficulty(r.difficulty),
                cover_file_id=r.cover_file_id,
                source_url=r.source_url,
                source_name=r.source_name,
                tag_ids=sorted(tags.get(r.id, [])),
                created_via=CreatedVia(r.created_via),
                published_at=r.published_at,
                yield_amount=r.yield_amount,
                yield_unit_id=r.yield_unit_id,
                steps=steps_by_recipe.get(r.id, []),
                ingredients=declared.get(r.id, []),
            )
            for r in rows
        ]

    async def get(self, recipe_id: int) -> Recipe | None:
        row = await self._db.get(RecipeModel, recipe_id)
        return (await self._entities([row]))[0] if row is not None else None

    async def get_by_public_id(self, public_id: str) -> Recipe | None:
        uid = parse_public_id(public_id)
        if uid is None:
            return None
        row = await self._db.scalar(select(RecipeModel).where(RecipeModel.public_id == uid))
        return (await self._entities([row]))[0] if row is not None else None

    async def get_many(self, ids: list[int]) -> list[Recipe]:
        if not ids:
            return []
        rows = await self._db.scalars(
            select(RecipeModel).where(RecipeModel.id.in_(sorted(set(ids))))
        )
        return await self._entities(list(rows.all()))

    # ── Finding ──────────────────────────────────────────────────────

    def _text_match(self, search: str) -> Any:
        """The ids of recipes whose text or ingredients match `search`."""
        pattern = contains_pattern(search)
        title_like = lower_contains(RecipeTranslationModel.title, pattern)
        dialect = self._db.bind.dialect.name if self._db.bind is not None else ""
        if dialect == "postgresql":
            config = case(
                (RecipeTranslationModel.locale == "de-AT", literal("german")),
                else_=literal("english"),
            ).cast(REGCONFIG)
            document = func.to_tsvector(
                config,
                RecipeTranslationModel.title + literal(" ") + RecipeTranslationModel.description,
            )
            text_hit = or_(document.op("@@")(func.plainto_tsquery(config, search)), title_like)
        else:
            text_hit = or_(title_like, lower_contains(RecipeTranslationModel.description, pattern))
        by_text = select(RecipeTranslationModel.recipe_id).where(text_hit)
        by_ingredient = _using_ingredient(
            StepIngredientModel.ingredient_id.in_(name_matches(search))
        )
        by_declared = select(RecipeIngredientModel.recipe_id).where(
            RecipeIngredientModel.ingredient_id.in_(name_matches(search))
        )
        return or_(
            RecipeModel.id.in_(by_text),
            RecipeModel.id.in_(by_ingredient),
            RecipeModel.id.in_(by_declared),
        )

    def _filtered(self, query: RecipeQuery) -> Select[tuple[RecipeModel]]:
        stmt = select(RecipeModel)
        visibility = RecipeModel.visibility
        if query.anonymous:
            # The anonymous visitor reads published recipes that are public
            # in effect, so nothing while public recipes are not allowed
            # (`recipe_rules.can_view_recipe`).
            stmt = stmt.where(
                and_(
                    RecipeModel.status == RecipeStatus.PUBLISHED.value,
                    visibility == RecipeVisibility.PUBLIC.value,
                )
                if query.public_allowed
                else false()
            )
            if query.status == "drafts":
                stmt = stmt.where(false())
            return self._narrowed(stmt, query)
        own = RecipeModel.owner_id == query.viewer_id
        opened = [
            # A signed-in user reads instance, peers and public recipes
            # alike (`recipe_rules.can_view_recipe`).
            visibility.in_(
                (
                    RecipeVisibility.INSTANCE.value,
                    RecipeVisibility.PEERS.value,
                    RecipeVisibility.PUBLIC.value,
                )
            ),
            and_(
                visibility == RecipeVisibility.SHARED.value,
                RecipeModel.id.in_(
                    select(RecipeUserShareModel.recipe_id).where(
                        RecipeUserShareModel.user_id == query.viewer_id
                    )
                ),
            ),
        ]
        if query.viewer_group_ids:
            opened.append(
                and_(
                    visibility == RecipeVisibility.SHARED.value,
                    RecipeModel.id.in_(
                        select(RecipeGroupShareModel.recipe_id).where(
                            RecipeGroupShareModel.group_id.in_(query.viewer_group_ids)
                        )
                    ),
                )
            )
        if query.viewer_household_member_ids:
            opened.append(
                and_(
                    visibility == RecipeVisibility.HOUSEHOLD.value,
                    RecipeModel.owner_id.in_(query.viewer_household_member_ids),
                )
            )
        published = and_(RecipeModel.status == RecipeStatus.PUBLISHED.value, or_(own, *opened))
        own_draft = and_(RecipeModel.status == RecipeStatus.DRAFT.value, own)
        if query.status == "published":
            stmt = stmt.where(published)
        elif query.status == "drafts":
            stmt = stmt.where(own_draft)
        else:
            stmt = stmt.where(or_(published, own_draft))
        return self._narrowed(stmt, query)

    def visible_ids(self, query: RecipeQuery) -> Any:
        """The ids of the recipes the query matches, as a subquery for
        aggregates that must count only what the viewer may see."""
        return self._filtered(query).with_only_columns(RecipeModel.id)

    def _narrowed(
        self, stmt: Select[tuple[RecipeModel]], query: RecipeQuery
    ) -> Select[tuple[RecipeModel]]:
        """Applies the query's filters to the recipes the viewer may see."""
        if query.search and query.search.strip():
            stmt = stmt.where(self._text_match(query.search))
        for tag_id in sorted(set(query.tag_ids)):
            stmt = stmt.where(
                RecipeModel.id.in_(
                    select(RecipeTagModel.recipe_id).where(RecipeTagModel.tag_id == tag_id)
                )
            )
        if query.owner_id is not None:
            stmt = stmt.where(RecipeModel.owner_id == query.owner_id)
        if query.favourites_of is not None:
            stmt = stmt.where(
                RecipeModel.id.in_(
                    select(RecipeFavouriteModel.recipe_id).where(
                        RecipeFavouriteModel.user_id == query.favourites_of
                    )
                )
            )
        if query.max_total_minutes is not None:
            stmt = stmt.where(_total_minutes() <= query.max_total_minutes)
        if query.difficulty is not None:
            stmt = stmt.where(RecipeModel.difficulty == query.difficulty.value)
        if query.ingredient_id is not None:
            stmt = stmt.where(
                or_(
                    RecipeModel.id.in_(
                        _using_ingredient(StepIngredientModel.ingredient_id == query.ingredient_id)
                    ),
                    RecipeModel.id.in_(
                        select(RecipeIngredientModel.recipe_id).where(
                            RecipeIngredientModel.ingredient_id == query.ingredient_id
                        )
                    ),
                )
            )
        return stmt

    async def find(self, query: RecipeQuery) -> tuple[list[Recipe], int]:
        stmt = self._filtered(query)
        total = int(await self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        if query.sort == "title":
            original_title = (
                select(func.lower(RecipeTranslationModel.title))
                .where(
                    RecipeTranslationModel.recipe_id == RecipeModel.id,
                    RecipeTranslationModel.locale == RecipeModel.original_locale,
                )
                .scalar_subquery()
            )
            stmt = stmt.order_by(original_title, RecipeModel.id)
        elif query.sort == "changed":
            stmt = stmt.order_by(RecipeModel.changed.desc(), RecipeModel.id.desc())
        else:
            stmt = stmt.order_by(RecipeModel.created.desc(), RecipeModel.id.desc())
        rows = await self._db.scalars(stmt.limit(query.limit).offset(query.offset))
        return await self._entities(list(rows.all())), total

    # ── Writing ──────────────────────────────────────────────────────

    async def save(self, recipe: Recipe) -> Recipe:
        row = await self._db.get(RecipeModel, recipe.id) if recipe.id else None
        if row is None:
            row = RecipeModel(public_id=recipe.public_id, created=recipe.created)
            self._db.add(row)
        row.owner_id = recipe.owner_id
        row.status = recipe.status.value
        row.visibility = recipe.visibility.value
        row.original_locale = recipe.original_locale
        row.base_servings = recipe.base_servings
        row.prep_minutes = recipe.prep_minutes
        row.cook_minutes = recipe.cook_minutes
        row.rest_minutes = recipe.rest_minutes
        row.difficulty = recipe.difficulty.value
        row.cover_file_id = recipe.cover_file_id
        row.source_url = recipe.source_url
        row.source_name = recipe.source_name
        row.created_via = recipe.created_via.value
        row.changed = recipe.changed
        row.published_at = recipe.published_at
        row.yield_amount = recipe.yield_amount
        row.yield_unit_id = recipe.yield_unit_id
        row.based_on_recipe_id = recipe.based_on_recipe_id
        row.origin_instance_id = recipe.origin_instance_id
        row.origin_public_id = recipe.origin_public_id
        row.mirror_peer_id = recipe.mirror_peer_id
        row.peer_capped = recipe.peer_capped
        await self._db.flush()

        await replace_translations(
            self._db,
            RecipeTranslationModel,
            "recipe_id",
            row.id,
            recipe.translations,
            lambda t: {"title": t.title, "description": t.description, "tips": t.tips},
        )
        await self._db.execute(delete(RecipeTagModel).where(RecipeTagModel.recipe_id == row.id))
        for tag_id in sorted(set(recipe.tag_ids)):
            self._db.add(RecipeTagModel(recipe_id=row.id, tag_id=tag_id))
        await self._db.execute(
            delete(RecipeUserShareModel).where(RecipeUserShareModel.recipe_id == row.id)
        )
        await self._db.execute(
            delete(RecipeGroupShareModel).where(RecipeGroupShareModel.recipe_id == row.id)
        )
        for user_id in sorted(set(recipe.shared_user_ids)):
            self._db.add(RecipeUserShareModel(recipe_id=row.id, user_id=user_id))
        for group_id in sorted(set(recipe.shared_group_ids)):
            self._db.add(RecipeGroupShareModel(recipe_id=row.id, group_id=group_id))
        await self._db.execute(
            delete(RecipePeerShareModel).where(RecipePeerShareModel.recipe_id == row.id)
        )
        for peer_id in sorted(set(recipe.shared_peer_ids)):
            self._db.add(RecipePeerShareModel(recipe_id=row.id, peer_id=peer_id))
        await self._db.execute(
            delete(RecipeCoEditorModel).where(RecipeCoEditorModel.recipe_id == row.id)
        )
        for user_id in sorted(set(recipe.co_editor_ids)):
            self._db.add(RecipeCoEditorModel(recipe_id=row.id, user_id=user_id))

        # The steps are replaced as a whole; their translations and step
        # ingredients go with them through ON DELETE CASCADE. Every row is
        # written again with the public id its entity carries, so a step or
        # line the use case kept keeps its id.
        await self._db.execute(delete(RecipeStepModel).where(RecipeStepModel.recipe_id == row.id))
        await self._db.flush()
        for position, step in enumerate(recipe.steps):
            step_row = RecipeStepModel(
                public_id=step.public_id,
                recipe_id=row.id,
                position=position,
                duration_minutes=step.duration_minutes,
                image_file_id=step.image_file_id,
            )
            self._db.add(step_row)
            await self._db.flush()
            for locale, text in sorted(step.translations.items()):
                self._db.add(
                    RecipeStepTranslationModel(step_id=step_row.id, locale=locale, text=text.text)
                )
            for si_position, si in enumerate(step.ingredients):
                si_row = StepIngredientModel(
                    public_id=si.public_id,
                    step_id=step_row.id,
                    position=si_position,
                    ingredient_id=si.ingredient_id,
                    sub_recipe_id=si.sub_recipe_id,
                    amount=si.amount,
                    unit_id=si.unit_id,
                )
                self._db.add(si_row)
                await self._db.flush()
                for locale, note in sorted(si.translations.items()):
                    if note.note.strip():
                        self._db.add(
                            StepIngredientTranslationModel(
                                step_ingredient_id=si_row.id, locale=locale, note=note.note
                            )
                        )
            for se_position, se in enumerate(step.equipment):
                se_row = StepEquipmentModel(
                    public_id=se.public_id,
                    step_id=step_row.id,
                    position=se_position,
                    equipment_id=se.equipment_id,
                    count=se.count,
                )
                self._db.add(se_row)
                await self._db.flush()
                for locale, note in sorted(se.translations.items()):
                    if note.note.strip():
                        self._db.add(
                            StepEquipmentTranslationModel(
                                step_equipment_id=se_row.id, locale=locale, note=note.note
                            )
                        )
        # The declared list is replaced as a whole too, ids kept the same way.
        await self._db.execute(
            delete(RecipeIngredientModel).where(RecipeIngredientModel.recipe_id == row.id)
        )
        await self._db.flush()
        for position, line in enumerate(recipe.ingredients):
            ri_row = RecipeIngredientModel(
                public_id=line.public_id,
                recipe_id=row.id,
                position=position,
                ingredient_id=line.ingredient_id,
                sub_recipe_id=line.sub_recipe_id,
                amount=line.amount,
                unit_id=line.unit_id,
            )
            self._db.add(ri_row)
            await self._db.flush()
            for locale, note in sorted(line.translations.items()):
                if note.note.strip():
                    self._db.add(
                        RecipeIngredientTranslationModel(
                            recipe_ingredient_id=ri_row.id, locale=locale, note=note.note
                        )
                    )
        await self._db.flush()
        return (await self._entities([row]))[0]

    async def parent_ids(self, recipe_ids: list[int]) -> dict[int, list[int]]:
        """Per recipe, the recipes whose steps or declared list use it as a
        sub-recipe."""
        if not recipe_ids:
            return {}
        rows = await self._db.execute(
            select(StepIngredientModel.sub_recipe_id, RecipeStepModel.recipe_id)
            .join(RecipeStepModel, RecipeStepModel.id == StepIngredientModel.step_id)
            .where(StepIngredientModel.sub_recipe_id.in_(recipe_ids))
        )
        declared = await self._db.execute(
            select(RecipeIngredientModel.sub_recipe_id, RecipeIngredientModel.recipe_id).where(
                RecipeIngredientModel.sub_recipe_id.in_(recipe_ids)
            )
        )
        parents: dict[int, list[int]] = {i: [] for i in recipe_ids}
        for sub_id, parent_id in [*rows.all(), *declared.all()]:
            if sub_id is not None and parent_id not in parents[sub_id]:
                parents[sub_id].append(parent_id)
        return parents

    async def copies_of(self, recipe_id: int) -> list[Recipe]:
        """The recipes copied from this one, newest first."""
        rows = await self._db.scalars(
            select(RecipeModel)
            .where(RecipeModel.based_on_recipe_id == recipe_id)
            .order_by(RecipeModel.created.desc(), RecipeModel.id.desc())
        )
        return await self._entities(list(rows.all()))

    async def owned_by(self, owner_id: int) -> list[Recipe]:
        rows = await self._db.scalars(select(RecipeModel).where(RecipeModel.owner_id == owner_id))
        return await self._entities(list(rows.all()))

    async def by_origin(
        self, owner_id: int, origin_instance_id: UUID, origin_public_id: UUID
    ) -> Recipe | None:
        row = await self._db.scalar(
            select(RecipeModel).where(
                RecipeModel.owner_id == owner_id,
                RecipeModel.origin_instance_id == origin_instance_id,
                RecipeModel.origin_public_id == origin_public_id,
            )
        )
        return (await self._entities([row]))[0] if row is not None else None

    async def shared_with_peer(self, peer_id: int) -> list[Recipe]:
        """Published recipes whose owner shares them with the peer, whatever
        their visibility; the caller applies the sharing rule."""
        rows = await self._db.scalars(
            select(RecipeModel).where(
                RecipeModel.status == RecipeStatus.PUBLISHED.value,
                RecipeModel.id.in_(
                    select(RecipePeerShareModel.recipe_id).where(
                        RecipePeerShareModel.peer_id == peer_id
                    )
                ),
            )
        )
        return await self._entities(list(rows.all()))

    async def published_for_peers(self) -> list[Recipe]:
        """Published recipes stored as peers or public, mirrors and their
        copies excepted; the caller applies the peering and public switches."""
        rows = await self._db.scalars(
            select(RecipeModel).where(
                RecipeModel.status == RecipeStatus.PUBLISHED.value,
                RecipeModel.visibility.in_(
                    (RecipeVisibility.PEERS.value, RecipeVisibility.PUBLIC.value)
                ),
                RecipeModel.peer_capped.is_(False),
            )
        )
        return await self._entities(list(rows.all()))

    async def mirrors_of(self, peer_id: int) -> list[Recipe]:
        rows = await self._db.scalars(
            select(RecipeModel).where(RecipeModel.mirror_peer_id == peer_id)
        )
        return await self._entities(list(rows.all()))

    async def detach_from_meal_plans(self, recipe_id: int, title: str) -> None:
        """Planned meals of the recipe become free text with its title."""
        await self._db.execute(
            update(MealPlanEntryModel)
            .where(MealPlanEntryModel.recipe_id == recipe_id, MealPlanEntryModel.title == "")
            .values(title=title[:255])
        )
        await self._db.execute(
            update(MealPlanEntryModel)
            .where(MealPlanEntryModel.recipe_id == recipe_id)
            .values(recipe_id=None)
        )

    async def unlink_sub_recipe(self, recipe_id: int) -> None:
        """Removes the step lines and declared lines of other recipes that
        use this one."""
        await self._db.execute(
            delete(StepIngredientModel).where(StepIngredientModel.sub_recipe_id == recipe_id)
        )
        await self._db.execute(
            delete(RecipeIngredientModel).where(RecipeIngredientModel.sub_recipe_id == recipe_id)
        )

    async def file_ids(self, recipe: Recipe) -> list[int]:
        return sorted(
            {f for f in (recipe.cover_file_id, *(s.image_file_id for s in recipe.steps)) if f}
        )

    async def file_in_use_elsewhere(self, file_id: int, recipe_id: int) -> bool:
        covers = await self._db.scalar(
            select(func.count())
            .select_from(RecipeModel)
            .where(RecipeModel.cover_file_id == file_id, RecipeModel.id != recipe_id)
        )
        steps = await self._db.scalar(
            select(func.count())
            .select_from(RecipeStepModel)
            .where(RecipeStepModel.image_file_id == file_id, RecipeStepModel.recipe_id != recipe_id)
        )
        return bool(covers) or bool(steps)

    async def step_images(
        self, visible: RecipeQuery, query: StepImageQuery
    ) -> tuple[list[StepImageHit], int]:
        # How many of the edited step's ingredients and equipment items a
        # step shares, counted per step and summed.
        matches: Any = literal(0)
        if query.ingredient_ids:
            matches = matches + (
                select(func.count(func.distinct(StepIngredientModel.ingredient_id)))
                .where(
                    StepIngredientModel.step_id == RecipeStepModel.id,
                    StepIngredientModel.ingredient_id.in_(query.ingredient_ids),
                )
                .correlate(RecipeStepModel)
                .scalar_subquery()
            )
        if query.equipment_ids:
            matches = matches + (
                select(func.count(func.distinct(StepEquipmentModel.equipment_id)))
                .where(
                    StepEquipmentModel.step_id == RecipeStepModel.id,
                    StepEquipmentModel.equipment_id.in_(query.equipment_ids),
                )
                .correlate(RecipeStepModel)
                .scalar_subquery()
            )
        own = case((RecipeModel.owner_id == visible.viewer_id, 1), else_=0)
        stmt = (
            select(
                RecipeStepModel.image_file_id.label("file_id"),
                RecipeStepModel.recipe_id.label("recipe_id"),
                RecipeStepModel.position.label("position"),
                matches.label("matches"),
                own.label("own"),
                RecipeModel.changed.label("changed"),
                # One row per file: the step that fits best stands for it.
                func.row_number()
                .over(
                    partition_by=RecipeStepModel.image_file_id,
                    order_by=(
                        matches.desc(),
                        own.desc(),
                        RecipeModel.changed.desc(),
                        RecipeStepModel.id,
                    ),
                )
                .label("rank"),
            )
            .join(RecipeModel, RecipeModel.id == RecipeStepModel.recipe_id)
            .where(
                RecipeStepModel.image_file_id.is_not(None),
                RecipeModel.mirror_peer_id.is_(None),
                RecipeModel.id.in_(self.visible_ids(visible)),
            )
        )
        if query.search and query.search.strip():
            pattern = contains_pattern(query.search)
            stmt = stmt.where(
                or_(
                    RecipeStepModel.id.in_(
                        select(RecipeStepTranslationModel.step_id).where(
                            lower_contains(RecipeStepTranslationModel.text, pattern)
                        )
                    ),
                    RecipeStepModel.id.in_(
                        select(StepIngredientModel.step_id).where(
                            StepIngredientModel.ingredient_id.in_(name_matches(query.search))
                        )
                    ),
                    RecipeModel.id.in_(
                        select(RecipeTranslationModel.recipe_id).where(
                            lower_contains(RecipeTranslationModel.title, pattern)
                        )
                    ),
                )
            )
        ranked = stmt.subquery()
        best = select(ranked).where(ranked.c.rank == 1)
        total = int(await self._db.scalar(select(func.count()).select_from(best.subquery())) or 0)
        rows = await self._db.execute(
            best.order_by(
                ranked.c.matches.desc(),
                ranked.c.own.desc(),
                ranked.c.changed.desc(),
                ranked.c.file_id.desc(),
            )
            .limit(query.limit)
            .offset(query.offset)
        )
        return [
            StepImageHit(
                file_id=row.file_id,
                recipe_id=row.recipe_id,
                step_position=row.position,
                matches=int(row.matches),
            )
            for row in rows
        ], total

    async def using_file(self, file_id: int) -> list[Recipe]:
        covers = select(RecipeModel.id).where(RecipeModel.cover_file_id == file_id)
        steps = select(RecipeStepModel.recipe_id).where(RecipeStepModel.image_file_id == file_id)
        ids = set((await self._db.scalars(covers)).all()) | set(
            (await self._db.scalars(steps)).all()
        )
        return await self.get_many(sorted(ids))

    async def delete(self, recipe: Recipe) -> None:
        row = await self._db.get(RecipeModel, recipe.id)
        if row is not None:
            await self._db.delete(row)
            await self._db.flush()
