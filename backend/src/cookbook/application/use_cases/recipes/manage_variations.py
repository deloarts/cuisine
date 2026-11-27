"""
Recipe variations: listing, reading, creating, changing and deleting them,
the recipe with a variation applied, how stale a variation is, and adopting
its changes into the original.

Anyone with write:recipes who can see a recipe may add a variation; it is
visible to whoever sees the recipe, never more, unless its author keeps it
private. Only the author changes it; the author or manage:recipes deletes
it. The recipe's editors (owner, co-editors, manage:recipes) adopt all or
some of its changes, which writes an `adopted` revision crediting the
variation's author and moves the variation onto that revision.

Saving a variation also moves it onto the recipe's latest revision: its
author has just seen the recipe as it is now.
"""

from dataclasses import dataclass
from uuid import UUID
from uuid import uuid4

from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.application.services.revisions import RevisionRecorder
from src.cookbook.application.services.variation_resolver import VariationChangeCommand
from src.cookbook.application.services.variation_resolver import VariationResolver
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.entities.personal import Rating
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.variation import RecipeVariation
from src.cookbook.domain.exceptions import InvalidMentionError
from src.cookbook.domain.exceptions import InvalidVariationError
from src.cookbook.domain.exceptions import MirrorReadOnlyError
from src.cookbook.domain.exceptions import NotOwnerError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.exceptions import VariationNotFoundError
from src.cookbook.domain.services.mentions import mentions
from src.cookbook.domain.services.recipe_rules import assert_not_mirror
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.recipe_rules import validate_recipe
from src.cookbook.domain.services.translations import assert_locale
from src.cookbook.domain.services.variations import AppliedVariation
from src.cookbook.domain.services.variations import StaleStep
from src.cookbook.domain.services.variations import apply_variation
from src.cookbook.domain.services.variations import can_adopt_variation
from src.cookbook.domain.services.variations import can_create_variation
from src.cookbook.domain.services.variations import can_delete_variation
from src.cookbook.domain.services.variations import can_edit_variation
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.services.variations import referenced_steps
from src.cookbook.domain.services.variations import renumber_after_adoption
from src.cookbook.domain.services.variations import stale_steps
from src.cookbook.domain.services.variations import validate_changes
from src.cookbook.domain.services.variations import validate_header
from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import RevisionKind
from src.cookbook.domain.value_objects.viewer import Viewer
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import IRatingRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.revision_repository import IRecipeRevisionRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import NotFoundError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class VariationCommand:
    name: str
    locale: str
    note: str = ""
    private: bool = False
    changes: list[VariationChangeCommand] | None = None


@dataclass(frozen=True)
class Staleness:
    """How a variation relates to the recipe as it is now."""

    current_revision: int | None
    # False when the base revision is unknown or was purged, so nothing can
    # be compared.
    base_available: bool
    steps: list[StaleStep]


@dataclass(frozen=True)
class VariationInfo:
    """A variation with what the viewer sees about it."""

    variation: RecipeVariation
    staleness: Staleness
    unavailable_change_ids: list[str]
    skipped_change_ids: list[str]
    rating_average: float | None
    rating_count: int
    own_rating: Rating | None
    can_edit: bool
    can_delete: bool
    can_adopt: bool


class ManageVariations:
    def __init__(
        self,
        *,
        variation_repo: IRecipeVariationRepository,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        rating_repo: IRatingRepository,
        revision_repo: IRecipeRevisionRepository,
        revisions: RevisionRecorder,
        resolver: VariationResolver,
        viewers: ViewerResolver,
        uow: IUnitOfWork,
        sharing: PeerRecipeSharing | None = None,
    ) -> None:
        self._sharing = sharing
        self._variations = variation_repo
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._ratings = rating_repo
        self._revision_repo = revision_repo
        self._revisions = revisions
        self.resolver = resolver
        self._viewers = viewers
        self._uow = uow

    # ── Loading ──────────────────────────────────────────────────────

    async def recipe(self, actor: User, public_id: str) -> Recipe:
        recipe = await self._recipes.get_by_public_id(public_id)
        if recipe is None or not can_view_recipe(await self._viewers.of(actor), recipe):
            raise RecipeNotFoundError("No such recipe.")
        return recipe

    async def get(
        self, actor: User, recipe_public_id: str, public_id: str
    ) -> tuple[Recipe, RecipeVariation]:
        """The recipe and its variation, or 404 when either is missing or
        hidden from the actor, so a private variation never leaks."""
        recipe = await self.recipe(actor, recipe_public_id)
        variation = await self._variations.get_by_public_id(public_id)
        if (
            variation is None
            or variation.recipe_id != recipe.id
            or not can_view_variation(await self._viewers.of(actor), recipe, variation)
        ):
            raise VariationNotFoundError("No such variation of this recipe.")
        return recipe, variation

    async def for_recipe(
        self, actor: User, recipe_public_id: str
    ) -> tuple[Recipe, list[RecipeVariation]]:
        recipe = await self.recipe(actor, recipe_public_id)
        viewer = await self._viewers.of(actor)
        return recipe, [
            v
            for v in await self._variations.for_recipe(recipe.id)
            if can_view_variation(viewer, recipe, v)
        ]

    async def visible_for(
        self, viewer: Viewer, recipes: list[Recipe]
    ) -> dict[int, list[RecipeVariation]]:
        """The variations the viewer may see, per recipe they may see."""
        by_recipe = await self._variations.for_recipes([r.id for r in recipes])
        return {
            r.id: [v for v in by_recipe.get(r.id, []) if can_view_variation(viewer, r, v)]
            for r in recipes
        }

    # ── Derived ──────────────────────────────────────────────────────

    async def applied(
        self, recipe: Recipe, variation: RecipeVariation
    ) -> tuple[AppliedVariation, list[str]]:
        """The recipe with the variation applied, and the changes naming a
        record that no longer exists."""
        resolved = await self.resolver.resolve(variation.changes, variation.locale)
        return (
            apply_variation(recipe, resolved.changes, variation.locale),
            resolved.unavailable_ids,
        )

    async def staleness(self, recipe: Recipe, variation: RecipeVariation) -> Staleness:
        current = await self._revision_repo.latest_number(recipe.id)
        base = (
            await self._revision_repo.get(recipe.id, variation.based_on_revision)
            if variation.based_on_revision is not None
            else None
        )
        if base is None:
            return Staleness(current_revision=current, base_available=False, steps=[])
        if current == variation.based_on_revision:
            return Staleness(current_revision=current, base_available=True, steps=[])
        steps = stale_steps(
            base.snapshot,
            await self._revisions.snapshot(recipe),
            referenced_steps(variation.changes),
            variation.locale,
        )
        return Staleness(current_revision=current, base_available=True, steps=steps)

    async def infos(
        self, actor: User, recipe: Recipe, variations: list[RecipeVariation]
    ) -> list[VariationInfo]:
        viewer = await self._viewers.of(actor)
        stats = await self._ratings.variation_stats([v.id for v in variations])
        result = []
        for variation in variations:
            applied, unavailable = await self.applied(recipe, variation)
            average, count = stats.get(variation.id, (None, 0))
            result.append(
                VariationInfo(
                    variation=variation,
                    staleness=await self.staleness(recipe, variation),
                    unavailable_change_ids=unavailable,
                    skipped_change_ids=applied.skipped_change_ids,
                    rating_average=average,
                    rating_count=count,
                    own_rating=await self._ratings.get_own(actor.id, recipe.id, variation.id),
                    can_edit=can_edit_variation(viewer, recipe, variation),
                    can_delete=can_delete_variation(viewer, recipe, variation),
                    can_adopt=can_adopt_variation(viewer, recipe, variation),
                )
            )
        return result

    # ── Writing ──────────────────────────────────────────────────────

    async def _check(
        self, recipe: Recipe, variation: RecipeVariation, cmd: VariationCommand
    ) -> None:
        """Stores the command's changes on the variation once they fit the
        recipe as it is now."""
        validate_header(cmd.name, cmd.note)
        assert_locale(cmd.locale)
        stored = await self.resolver.stored(cmd.changes or [])
        resolved = await self.resolver.resolve(stored, cmd.locale)
        validate_changes(recipe, resolved.changes)
        applied = apply_variation(recipe, resolved.changes, cmd.locale)
        await self._check_mentions(applied)
        variation.name = cmd.name.strip()
        variation.note = cmd.note.strip()
        variation.locale = cmd.locale
        variation.private = cmd.private
        variation.changes = stored
        variation.based_on_revision = await self._revision_repo.latest_number(recipe.id)
        variation.changed = now_utc()

    async def _check_mentions(self, applied: AppliedVariation) -> None:
        """Every mention in a step the variation writes points at a line or
        an equipment item of that step, as in the editor."""
        recipe = applied.recipe
        ingredients = {
            i.id: str(i.public_id).lower()
            for i in await self._ingredients.get_many(recipe.ingredient_ids)
        }
        subs = {
            r.id: str(r.public_id).lower()
            for r in await self._recipes.get_many(recipe.sub_recipe_ids)
        }
        equipment = {
            e.id: str(e.public_id).lower()
            for e in await self._equipment.get_many(recipe.equipment_ids)
        }
        for marker, step in zip(applied.steps, recipe.steps, strict=True):
            if not (marker.added or marker.text_changed):
                continue
            allowed = {
                "ingredient": {
                    ingredients[si.ingredient_id]
                    for si in step.ingredients
                    if si.ingredient_id in ingredients
                },
                "recipe": {
                    subs[si.sub_recipe_id] for si in step.ingredients if si.sub_recipe_id in subs
                },
                "equipment": {
                    equipment[se.equipment_id]
                    for se in step.equipment
                    if se.equipment_id in equipment
                },
            }
            for locale, text in step.translations.items():
                for mention in mentions(text.text):
                    if mention.public_id not in allowed[mention.kind]:
                        raise InvalidMentionError(
                            f"Step {marker.position} mentions {mention.name!r}, which is not "
                            "among the lines or equipment of that step.",
                            step=marker.position,
                            locale=locale,
                            kind=mention.kind,
                            target_id=mention.public_id,
                        )

    async def create(
        self, actor: User, recipe_public_id: str, cmd: VariationCommand
    ) -> tuple[Recipe, RecipeVariation]:
        recipe = await self.recipe(actor, recipe_public_id)
        return recipe, await self.add(actor, recipe, cmd)

    async def add(
        self,
        actor: User,
        recipe: Recipe,
        cmd: VariationCommand,
        *,
        commit: bool = True,
        public_id: UUID | None = None,
    ) -> RecipeVariation:
        """A new variation of the actor's on a recipe the caller has loaded.
        The recipe archive import adds variations to a draft it has just
        created, inside its own transaction, with `commit=False` and the
        public id it derived from the variation's source id."""
        if not can_create_variation(await self._viewers.of(actor), recipe):
            raise PermissionDeniedError("Adding a variation needs write:recipes.")
        now = now_utc()
        variation = RecipeVariation(
            public_id=public_id or uuid4(),
            recipe_id=recipe.id,
            author_id=actor.id or None,
            name=cmd.name,
            locale=cmd.locale,
            created=now,
            changed=now,
        )
        await self._check(recipe, variation, cmd)
        saved = await self._variations.save(variation)
        if commit:
            await self._sync(recipe)
            await self._uow.commit()
        return saved

    async def _sync(self, recipe: Recipe) -> None:
        """A variation travels with its recipe, so the paired instances the
        recipe goes to hear of the change."""
        if self._sharing is not None:
            await self._sharing.sync([recipe])

    async def save_mirrored(
        self,
        recipe: Recipe,
        public_id: UUID,
        origin_public_id: UUID,
        source_author_name: str | None,
        cmd: VariationCommand,
    ) -> RecipeVariation:
        """A variation that came with a mirror, under the public id derived
        from its source id, without an author here and without committing.
        The mirror builder passes only changes that fit (`fitting_changes`)."""
        existing = await self._variations.get_by_public_id(str(public_id))
        now = now_utc()
        variation = existing or RecipeVariation(
            public_id=public_id,
            recipe_id=recipe.id,
            author_id=None,
            name=cmd.name,
            locale=cmd.locale,
            created=now,
            changed=now,
        )
        variation.origin_public_id = origin_public_id
        variation.source_author_name = source_author_name
        await self._check(recipe, variation, cmd)
        return await self._variations.save(variation)

    async def save_imported(
        self, actor: User, recipe: Recipe, public_id: UUID, cmd: VariationCommand
    ) -> RecipeVariation | None:
        """An imported variation under the public id the import derived from
        its source id, without committing. When an earlier import of the
        same source variation into this recipe left a variation with that id,
        it is replaced, as long as the actor is still its author; otherwise
        it is added. None when the variation with that id is someone else's
        now, which leaves it as it is."""
        existing = await self._variations.get_by_public_id(str(public_id))
        if existing is None:
            return await self.add(actor, recipe, cmd, commit=False, public_id=public_id)
        viewer = await self._viewers.of(actor)
        if existing.recipe_id != recipe.id or not can_edit_variation(viewer, recipe, existing):
            return None
        await self._check(recipe, existing, cmd)
        return await self._variations.save(existing)

    async def fitting_changes(
        self, recipe: Recipe, changes: list[VariationChangeCommand], locale: str
    ) -> tuple[list[VariationChangeCommand], list[VariationChangeCommand]]:
        """The changes that fit the recipe as it is now and those that do not.
        Each change is checked together with the ones kept before it, by the
        same rules as a save, so the kept ones save as a whole."""
        kept: list[VariationChangeCommand] = []
        dropped: list[VariationChangeCommand] = []
        for change in changes:
            try:
                stored = await self.resolver.stored([*kept, change])
                resolved = await self.resolver.resolve(stored, locale)
                if resolved.unavailable_ids:
                    raise InvalidVariationError("A change names a record that does not exist.")
                validate_changes(recipe, resolved.changes)
                await self._check_mentions(apply_variation(recipe, resolved.changes, locale))
            except (InvalidVariationError, InvalidMentionError, NotFoundError):
                dropped.append(change)
                continue
            kept.append(change)
        return kept, dropped

    async def update(
        self, actor: User, recipe_public_id: str, public_id: str, cmd: VariationCommand
    ) -> tuple[Recipe, RecipeVariation]:
        recipe, variation = await self.get(actor, recipe_public_id, public_id)
        self._assert_local(variation)
        if not can_edit_variation(await self._viewers.of(actor), recipe, variation):
            raise NotOwnerError("Only its author changes a variation.")
        await self._check(recipe, variation, cmd)
        saved = await self._variations.save(variation)
        await self._sync(recipe)
        await self._uow.commit()
        return recipe, saved

    async def delete(self, actor: User, recipe_public_id: str, public_id: str) -> None:
        recipe, variation = await self.get(actor, recipe_public_id, public_id)
        self._assert_local(variation)
        if not can_delete_variation(await self._viewers.of(actor), recipe, variation):
            raise NotOwnerError("Only its author or someone with manage:recipes deletes it.")
        await self._variations.delete(variation)
        await self._sync(recipe)
        await self._uow.commit()

    @staticmethod
    def _assert_local(variation: RecipeVariation) -> None:
        if variation.mirrored:
            raise MirrorReadOnlyError(
                "This variation came with a recipe from another instance and changes only there."
            )

    async def adopt(
        self,
        actor: User,
        recipe_public_id: str,
        public_id: str,
        change_ids: list[str] | None,
        note: str | None = None,
    ) -> tuple[Recipe, RecipeVariation]:
        """Writes all changes, or the chosen ones, into the original as an
        `adopted` revision crediting the variation's author. The adopted
        changes leave the variation, the rest move past the steps it added,
        and the variation moves onto the new revision."""
        recipe, variation = await self.get(actor, recipe_public_id, public_id)
        viewer = await self._viewers.of(actor)
        assert_not_mirror(viewer, recipe)
        if not can_adopt_variation(viewer, recipe, variation):
            if not actor.has_permission(Permission.WRITE_RECIPES):
                raise PermissionDeniedError("Adopting a variation needs write:recipes.")
            raise NotOwnerError("Only the recipe's editors adopt a variation.")
        known = [str(c.get("id")) for c in variation.changes]
        wanted = set(known) if change_ids is None else set(change_ids)
        if not wanted or not wanted <= set(known):
            raise InvalidVariationError("Choose changes this variation has.")
        resolved = await self.resolver.resolve(
            [c for c in variation.changes if str(c.get("id")) in wanted], variation.locale
        )
        applied = apply_variation(recipe, resolved.changes, variation.locale)
        taken = {c.id for c in resolved.changes} - set(applied.skipped_change_ids)
        if not taken:
            raise InvalidVariationError("None of the chosen changes fits the recipe as it is now.")
        recipe.steps = applied.recipe.steps
        recipe.ingredients = applied.recipe.ingredients
        recipe.changed = now_utc()
        validate_recipe(recipe)
        saved = await self._recipes.save(recipe)
        revision = await self._revisions.record(
            saved,
            RevisionKind.ADOPTED,
            actor,
            via=CreatedVia.WEB,
            note=note or variation.name,
            credited_author_id=variation.author_id,
        )
        variation.changes = renumber_after_adoption(variation.changes, taken)
        variation.based_on_revision = revision.number
        variation.changed = now_utc()
        kept = await self._variations.save(variation)
        await self._sync(saved)
        await self._uow.commit()
        return saved, kept
