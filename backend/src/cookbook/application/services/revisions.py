"""
Recording recipe revisions. Every use case that changes a recipe's content
(create, update, translation, an agent's image, restore) calls `record`
after saving the recipe, in the same unit of work, so the revision and the
change commit together. Publishing and unpublishing change the status only
and record nothing.
"""

from typing import Any

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.revision import RecipeRevision
from src.cookbook.domain.services.revisions import Reference
from src.cookbook.domain.services.revisions import SnapshotRefs
from src.cookbook.domain.services.revisions import build_snapshot
from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import RevisionKind
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.cookbook.ports.outbound.repositories.revision_repository import IRecipeRevisionRepository
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.shared_kernel.domain.services.clock import now_utc

MAX_NOTE = 255


class RevisionRecorder:
    def __init__(
        self,
        *,
        revision_repo: IRecipeRevisionRepository,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        file_repo: IStoredFileRepository,
    ) -> None:
        self._revisions = revision_repo
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._files = file_repo

    async def refs(self, recipe: Recipe) -> SnapshotRefs:
        """The public ids and names of everything the recipe refers to."""
        ingredients = await self._ingredients.get_many(recipe.ingredient_ids)
        equipment = await self._equipment.get_many(recipe.equipment_ids)
        subs = await self._recipes.get_many(recipe.sub_recipe_ids)
        units = await self._units.list_all()
        tags = await self._tags.list_all()
        file_ids = [recipe.cover_file_id, *(s.image_file_id for s in recipe.steps)]
        files = await self._files.public_ids([f for f in file_ids if f is not None])
        return SnapshotRefs(
            ingredients={
                i.id: Reference(str(i.public_id), {k: v.name for k, v in i.translations.items()})
                for i in ingredients
            },
            units={
                u.id: Reference(str(u.public_id), {k: v.name for k, v in u.translations.items()})
                for u in units
            },
            tags={
                t.id: Reference(str(t.public_id), {k: v.name for k, v in t.translations.items()})
                for t in tags
            },
            equipment={
                e.id: Reference(str(e.public_id), {k: v.name for k, v in e.translations.items()})
                for e in equipment
            },
            recipes={
                r.id: Reference(str(r.public_id), {k: v.title for k, v in r.translations.items()})
                for r in subs
            },
            files={k: str(v) for k, v in files.items()},
        )

    async def snapshot(self, recipe: Recipe) -> dict[str, Any]:
        """The recipe as a revision would record it now."""
        return build_snapshot(recipe, await self.refs(recipe))

    async def record(
        self,
        recipe: Recipe,
        kind: RevisionKind,
        actor: User,
        *,
        via: CreatedVia = CreatedVia.WEB,
        note: str | None = None,
        restored_from: int | None = None,
        credited_author_id: int | None = None,
    ) -> RecipeRevision:
        cleaned = (note or "").strip()[:MAX_NOTE] or None
        return await self._revisions.add(
            RecipeRevision(
                recipe_id=recipe.id,
                number=await self._revisions.next_number(recipe.id),
                kind=kind,
                created=now_utc(),
                created_via=via,
                author_id=actor.id or None,
                restored_from=restored_from,
                note=cleaned,
                snapshot=await self.snapshot(recipe),
                credited_author_id=credited_author_id,
            )
        )
