"""
Creating, editing, publishing and deleting recipes. write:recipes creates
recipes and changes the actor's own; manage:recipes changes the recipes the
manager can see. A recipe starts as a draft, its owner's alone; publishing
makes it visible to whom its visibility says. Only the owner decides the
visibility, and only when the privacy settings let users choose; otherwise
every recipe gets the instance default. Setting a recipe to public needs the
instance to allow public recipes; a recipe that is public already keeps its
stored value when the switch is off, and reads as instance meanwhile.

Every content change appends a revision in the same unit of work (create,
update, translation, image, restore); status changes do not. Whoever may
edit a recipe reads its revisions and restores one.

The editor sends a recipe as a whole: its text in every language, its tags
and its steps with their ingredients and equipment, all by public id. Unknown ids answer
404, so a stale editor never saves half a recipe. Steps and lines carry their
own ids, which a save keeps when the recipe already has them
(`step_ids.StepIdKeepers`); a create, an import or a copy always gets fresh ones.
"""

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import Any
from uuid import UUID
from uuid import uuid4

from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.application.services.recipe_deletion import RecipeDeletion
from src.cookbook.application.services.revisions import RevisionRecorder
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.recipe import RecipeStep
from src.cookbook.domain.entities.recipe import StepEquipment
from src.cookbook.domain.entities.recipe import StepIngredient
from src.cookbook.domain.entities.revision import RecipeRevision
from src.cookbook.domain.exceptions import CoEditorError
from src.cookbook.domain.exceptions import EquipmentNotFoundError
from src.cookbook.domain.exceptions import IngredientNotFoundError
from src.cookbook.domain.exceptions import InvalidMentionError
from src.cookbook.domain.exceptions import InvalidRecipeError
from src.cookbook.domain.exceptions import PeerShareNotAllowedError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.exceptions import RecipeRevisionNotFoundError
from src.cookbook.domain.exceptions import RevisionRestoreError
from src.cookbook.domain.exceptions import TagNotFoundError
from src.cookbook.domain.exceptions import UnitNotFoundError
from src.cookbook.domain.services.markdown import plain_text
from src.cookbook.domain.services.mentions import mentions
from src.cookbook.domain.services.recipe_rules import assert_can_delete_recipe
from src.cookbook.domain.services.recipe_rules import assert_can_edit_recipe
from src.cookbook.domain.services.recipe_rules import assert_not_mirror
from src.cookbook.domain.services.recipe_rules import can_change_visibility
from src.cookbook.domain.services.recipe_rules import can_edit_recipe
from src.cookbook.domain.services.recipe_rules import can_manage_co_editors
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.recipe_rules import narrower
from src.cookbook.domain.services.recipe_rules import validate_publishable
from src.cookbook.domain.services.recipe_rules import validate_recipe
from src.cookbook.domain.services.revisions import display_name
from src.cookbook.domain.services.revisions import upgrade_snapshot
from src.cookbook.domain.services.step_ids import IdKeeper
from src.cookbook.domain.services.step_ids import StepIdKeepers
from src.cookbook.domain.services.sub_recipes import MAX_DEPTH
from src.cookbook.domain.services.sub_recipes import assert_sub_recipes_allowed
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.value_objects.enums import CreatedVia
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.domain.value_objects.enums import RevisionKind
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.ports.outbound.event_publisher import RECIPE_PUBLISHED
from src.cookbook.ports.outbound.event_publisher import IEventPublisher
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.cookbook.ports.outbound.repositories.revision_repository import IRecipeRevisionRepository
from src.platform.application.services.file_access import FileAccess
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PeerNotFoundError
from src.platform.domain.exceptions import PeerRecipesNotAllowedError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.exceptions import PublicRecipesNotAllowedError
from src.platform.domain.exceptions import StoredFileNotFoundError
from src.platform.domain.exceptions import UserGroupNotFoundError
from src.platform.domain.exceptions import UserNotFoundError
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.repositories.user_group_repository import IUserGroupRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(frozen=True)
class StepIngredientCommand:
    """A catalogue ingredient or a sub-recipe, by public id, exactly one.
    `id` is the line's own public id, kept when the recipe already has it."""

    id: str | None = None
    ingredient_id: str | None = None
    sub_recipe_id: str | None = None
    amount: float | None = None
    unit_id: str | None = None
    notes: dict[str, NoteText] = field(default_factory=dict)


@dataclass(frozen=True)
class StepEquipmentCommand:
    """An item of the equipment catalogue, by public id. `id` is the line's
    own public id, kept when the recipe already has it."""

    equipment_id: str
    id: str | None = None
    count: int | None = None
    notes: dict[str, NoteText] = field(default_factory=dict)


@dataclass(frozen=True)
class StepCommand:
    translations: dict[str, StepText]
    # The step's own public id, kept when the recipe already has it.
    id: str | None = None
    duration_minutes: int | None = None
    image_file_id: str | None = None
    ingredients: list[StepIngredientCommand] = field(default_factory=list)
    equipment: list[StepEquipmentCommand] = field(default_factory=list)


@dataclass(frozen=True)
class RecipeCommand:
    original_locale: str
    translations: dict[str, RecipeText]
    base_servings: int = 4
    prep_minutes: int | None = None
    cook_minutes: int | None = None
    rest_minutes: int | None = None
    difficulty: Difficulty = Difficulty.EASY
    cover_file_id: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    tag_ids: list[str] = field(default_factory=list)
    steps: list[StepCommand] = field(default_factory=list)
    # The ingredient list declared for the whole recipe, in its order.
    ingredients: list[StepIngredientCommand] = field(default_factory=list)
    yield_amount: float | None = None
    yield_unit_id: str | None = None
    # None keeps the current visibility, or the default on create.
    visibility: RecipeVisibility | None = None
    # With visibility "shared": the users and groups, by public id.
    shared_user_ids: list[str] | None = None
    shared_group_ids: list[str] | None = None
    # With visibility "shared": the paired instances, by public id.
    shared_peer_ids: list[str] | None = None
    # A short note on the revision this save records.
    revision_note: str | None = None


class ManageRecipes:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        file_repo: IStoredFileRepository,
        settings_repo: ISettingsRepository,
        user_repo: IUserRepository,
        group_repo: IUserGroupRepository,
        viewers: ViewerResolver,
        revisions: RevisionRecorder,
        revision_repo: IRecipeRevisionRepository,
        uow: IUnitOfWork,
        events: IEventPublisher | None = None,
        sharing: PeerRecipeSharing | None = None,
        peer_repo: IPeerRepository | None = None,
        mirror_repo: IMirrorRepository | None = None,
        file_access: FileAccess | None = None,
    ) -> None:
        self._file_access = file_access
        self._sharing = sharing
        self._peers = peer_repo
        self._mirrors = mirror_repo
        self._events = events
        self._revisions = revisions
        self._revision_repo = revision_repo
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._files = file_repo
        self._settings = settings_repo
        self._users = user_repo
        self._groups = group_repo
        self._viewers = viewers
        self._uow = uow

    async def get_visible(self, actor: User, public_id: str) -> Recipe:
        """The recipe, or 404 when it does not exist or is a draft the actor
        may not see, so a draft's existence never leaks."""
        recipe = await self._recipes.get_by_public_id(public_id)
        if recipe is None or not can_view_recipe(await self._viewers.of(actor), recipe):
            raise RecipeNotFoundError("No such recipe.")
        return recipe

    async def get_editable(self, actor: User, public_id: str) -> Recipe:
        recipe = await self.get_visible(actor, public_id)
        assert_can_edit_recipe(await self._viewers.of(actor), recipe)
        return recipe

    async def get_deletable(self, actor: User, public_id: str) -> Recipe:
        """For deleting, publishing and unpublishing, which co-editors may
        not do."""
        recipe = await self.get_visible(actor, public_id)
        assert_can_delete_recipe(await self._viewers.of(actor), recipe)
        return recipe

    async def _sub_recipe_id(self, actor: User | None, public_id: str) -> int:
        """A recipe to link as a sub-recipe; it must be one the actor sees.
        A mirror may vanish whenever its source withdraws it, so only
        another mirror links one (the mirror builder, without an actor)."""
        sub = await self._recipes.get_by_public_id(public_id)
        if sub is None or (
            actor is not None and not can_view_recipe(await self._viewers.of(actor), sub)
        ):
            raise RecipeNotFoundError("A sub-recipe of the recipe does not exist.")
        if actor is not None and sub.is_mirror:
            raise InvalidRecipeError(
                "A recipe from another instance cannot be used as a sub-recipe; copy it as your "
                "own recipe first."
            )
        return sub.id

    async def _sync(self, *recipes: Recipe) -> None:
        """Tells the paired instances what changed for them."""
        if self._sharing is not None:
            await self._sharing.sync(recipes)

    async def peer_targets(self) -> list[Peer]:
        """The paired instances users may share recipes with now; none
        while peering is off."""
        if self._peers is None or not (await self._settings.get_features()).peering:
            return []
        return [p for p in await self._peers.list_active() if p.users_may_share]

    async def peer_hidden_sub_recipes(self, recipe: Recipe) -> list[Recipe]:
        """Direct sub-recipes that do not go to every paired instance the
        recipe goes to; those instances see them without a title."""
        if self._sharing is None:
            return []
        peers = await self._sharing.peers_of(recipe)
        if not peers:
            return []
        return [
            s
            for s in await self._recipes.get_many(recipe.sub_recipe_ids)
            if not peers <= await self._sharing.peers_of(s)
        ]

    async def _check_sub_recipes(self, recipe: Recipe) -> None:
        """No cycle and no tree deeper than allowed, counting the recipes
        that use this one as well as those it uses."""
        ancestors: set[int] = set()
        depth_above = 0
        frontier = {recipe.id} if recipe.id else set()
        while frontier and depth_above <= MAX_DEPTH:
            parents = await self._recipes.parent_ids(sorted(frontier))
            frontier = {p for found in parents.values() for p in found} - ancestors
            if not frontier:
                break
            ancestors |= frontier
            depth_above += 1
        tree: dict[int, Recipe] = {}
        wanted = set(recipe.sub_recipe_ids)
        for _ in range(MAX_DEPTH + 2):
            missing = sorted(wanted - set(tree) - {recipe.id})
            if not missing:
                break
            loaded = await self._recipes.get_many(missing)
            tree.update({r.id: r for r in loaded})
            wanted = {s for r in loaded for s in r.sub_recipe_ids}
        assert_sub_recipes_allowed(recipe, tree, depth_above, ancestors)

    async def less_visible_sub_recipes(self, recipe: Recipe) -> list[Recipe]:
        """Direct sub-recipes that some reader of the recipe may not see:
        drafts, and recipes shared more narrowly. Publishing warns about
        them; their readers see a placeholder."""
        subs = await self._recipes.get_many(recipe.sub_recipe_ids)
        public_allowed = (await self._settings.get_privacy()).allow_public_recipes
        peering = (await self._settings.get_features()).peering
        return [
            s for s in subs if narrower(s, recipe, public_allowed=public_allowed, peering=peering)
        ]

    async def can_edit(self, actor: User, recipe: Recipe) -> bool:
        return can_edit_recipe(await self._viewers.of(actor), recipe)

    async def _default_visibility(self, actor: User) -> RecipeVisibility:
        """The visibility a new recipe of the actor starts with: their own
        default when users may choose, else the instance default. A public
        default reads as instance while public recipes are not allowed, and a
        peers default while peering is off, so no new public or peers recipe
        appears then."""
        privacy = await self._settings.get_privacy()
        own = actor.default_recipe_visibility
        chosen = (
            own
            if own and privacy.users_may_change_visibility
            else privacy.default_recipe_visibility
        )
        peering = (await self._settings.get_features()).peering
        return RecipeVisibility(privacy.effective_visibility(chosen, peering=peering))

    @staticmethod
    def _capped(recipe: Recipe, visibility: RecipeVisibility) -> RecipeVisibility:
        """A copy of a mirror never becomes peers or public."""
        if recipe.peer_capped and visibility in (RecipeVisibility.PEERS, RecipeVisibility.PUBLIC):
            return RecipeVisibility.INSTANCE
        return visibility

    async def _peer_ids(self, recipe: Recipe, public_ids: list[str]) -> list[int]:
        """The paired instances to share with. Keeping or removing one is
        always allowed; adding one needs peering on, an active pairing and
        the instance letting users share with that peer, and never works for
        a mirror or a copy of one."""
        chosen: list[int] = []
        added = False
        for public_id in dict.fromkeys(public_ids):
            peer = await self._peers.get_by_public_id(public_id) if self._peers else None
            if peer is None:
                raise PeerNotFoundError("One of the instances to share with does not exist.")
            if peer.id not in recipe.shared_peer_ids:
                added = True
                if recipe.peer_capped or recipe.is_mirror:
                    raise PeerShareNotAllowedError(
                        "A recipe from another instance, or a copy of one, cannot be shared "
                        "with paired instances."
                    )
                if not peer.active or not peer.users_may_share:
                    raise PeerShareNotAllowedError(
                        f"Recipes cannot be shared with {peer.name} from this instance."
                    )
            chosen.append(peer.id)
        if added and not (await self._settings.get_features()).peering:
            raise PeerShareNotAllowedError("Sharing with other instances is switched off.")
        return chosen

    async def _apply_visibility(self, actor: User, recipe: Recipe, cmd: RecipeCommand) -> None:
        privacy = await self._settings.get_privacy()
        if not privacy.users_may_change_visibility:
            recipe.visibility = self._capped(recipe, await self._default_visibility(actor))
            recipe.shared_user_ids, recipe.shared_group_ids = [], []
            recipe.shared_peer_ids = []
            return
        if not recipe.id:
            recipe.visibility = self._capped(recipe, await self._default_visibility(actor))
        if not can_change_visibility(await self._viewers.of(actor), recipe):
            return
        if cmd.visibility is not None:
            if cmd.visibility is RecipeVisibility.PUBLIC and recipe.peer_capped:
                raise PeerShareNotAllowedError(
                    "A copy of a recipe from another instance cannot be made public."
                )
            if (
                cmd.visibility is RecipeVisibility.PUBLIC
                and recipe.visibility is not RecipeVisibility.PUBLIC
                and not privacy.allow_public_recipes
            ):
                raise PublicRecipesNotAllowedError(
                    "Public recipes are not allowed on this instance."
                )
            if cmd.visibility is RecipeVisibility.PEERS and recipe.peer_capped:
                raise PeerShareNotAllowedError(
                    "A copy of a recipe from another instance cannot go to paired instances."
                )
            if (
                cmd.visibility is RecipeVisibility.PEERS
                and recipe.visibility is not RecipeVisibility.PEERS
                and not (await self._settings.get_features()).peering
            ):
                raise PeerRecipesNotAllowedError(
                    "Peering is off on this instance, so a recipe cannot go to paired instances."
                )
            recipe.visibility = cmd.visibility
        if cmd.shared_user_ids is not None:
            users = []
            for public_id in dict.fromkeys(cmd.shared_user_ids):
                user = await self._users.get_by_public_id(public_id)
                if user is None or user.is_service_account:
                    raise UserNotFoundError("One of the people to share with does not exist.")
                users.append(user.id)
            recipe.shared_user_ids = users
        if cmd.shared_group_ids is not None:
            groups = []
            for public_id in dict.fromkeys(cmd.shared_group_ids):
                group = await self._groups.get_by_public_id(public_id)
                if group is None:
                    raise UserGroupNotFoundError("One of the groups to share with does not exist.")
                groups.append(group.id)
            recipe.shared_group_ids = groups
        if cmd.shared_peer_ids is not None:
            recipe.shared_peer_ids = await self._peer_ids(recipe, cmd.shared_peer_ids)

    async def _file_id(
        self,
        actor: User | None,
        public_id: str | None,
        *,
        kept: frozenset[int] = frozenset(),
        restored: frozenset[str] = frozenset(),
    ) -> int | None:
        """The internal id of an image to put on a recipe. An image the recipe
        has now (`kept`) or had in the revision being restored (`restored`)
        stays; any other must be one the actor may read already, and never an
        avatar or a branding image, which deleting the recipe would delete
        with it. A refused image answers like an unknown one."""
        if not public_id:
            return None
        stored = await self._files.get_by_public_id(public_id)
        if stored is None:
            raise StoredFileNotFoundError("An image of the recipe does not exist.")
        if stored.id in kept or public_id.lower() in restored:
            return stored.id
        access = self._file_access
        if actor is None or access is None:
            return stored.id
        if await access.platform_use(stored) or not await access.may_read(actor, stored):
            raise StoredFileNotFoundError("An image of the recipe does not exist.")
        return stored.id

    @staticmethod
    def _check_mentions(
        number: int,
        texts: dict[str, str],
        ingredient_ids: set[str],
        recipe_ids: set[str],
        equipment_ids: set[str],
    ) -> None:
        """Every mention in a step points at one of that step's lines or
        equipment items. The error names the step (from 1), the locale and
        the mention, so the editor can mark it."""
        for locale, text in texts.items():
            for mention in mentions(text):
                wanted = {
                    "ingredient": ingredient_ids,
                    "recipe": recipe_ids,
                    "equipment": equipment_ids,
                }[mention.kind]
                if mention.public_id not in wanted:
                    what = "equipment" if mention.kind == "equipment" else "ingredients"
                    raise InvalidMentionError(
                        f"Step {number} mentions {mention.name!r}, which is not among the "
                        f"{what} of that step; add it to the step or remove the mention.",
                        step=number,
                        locale=locale,
                        kind=mention.kind,
                        target_id=mention.public_id,
                    )

    async def _apply(
        self,
        actor: User | None,
        recipe: Recipe,
        cmd: RecipeCommand,
        *,
        restoring: dict[str, Any] | None = None,
        from_source: bool = False,
        unpublish_when_incomplete: bool = False,
    ) -> None:
        """Writes the command into the recipe. A step or line keeps the id
        the command names when the recipe has it now or, for a restore, when
        the restored snapshot recorded it; every other one gets a fresh id.
        With `from_source` (an import) the command names source ids, which
        become ids derived from the recipe's public id (`step_ids`). With
        `unpublish_when_incomplete` a published recipe whose new content may
        not be published goes back to draft instead of refusing the save."""
        ids = StepIdKeepers()
        ids.know_steps(recipe.steps)
        ids.know_declared(recipe.ingredients)
        if restoring is not None:
            ids.know_snapshot(restoring)
        kept = frozenset(await self._recipes.file_ids(recipe)) if recipe.id else frozenset()
        restored = _snapshot_images(restoring)
        if from_source:
            ids.derive_from_source(recipe.public_id)
        tag_ids: list[int] = []
        for public_id in dict.fromkeys(cmd.tag_ids):
            tag = await self._tags.get_by_public_id(public_id)
            if tag is None:
                raise TagNotFoundError("A tag of the recipe does not exist.")
            tag_ids.append(tag.id)
        ingredient_ids: dict[str, int] = {}
        equipment_ids: dict[str, int] = {}
        unit_ids: dict[str, int] = {}

        async def line(si: StepIngredientCommand, keeper: IdKeeper) -> StepIngredient:
            ingredient_id: int | None = None
            sub_recipe_id: int | None = None
            if si.sub_recipe_id:
                sub_recipe_id = await self._sub_recipe_id(actor, si.sub_recipe_id)
            elif si.ingredient_id:
                if si.ingredient_id not in ingredient_ids:
                    ingredient = await self._ingredients.get_by_public_id(si.ingredient_id)
                    if ingredient is None:
                        raise IngredientNotFoundError("An ingredient of the recipe does not exist.")
                    ingredient_ids[si.ingredient_id] = ingredient.id
                ingredient_id = ingredient_ids[si.ingredient_id]
            unit_id: int | None = None
            if si.unit_id:
                if si.unit_id not in unit_ids:
                    unit = await self._units.get_by_public_id(si.unit_id)
                    if unit is None:
                        raise UnitNotFoundError("A unit of the recipe does not exist.")
                    unit_ids[si.unit_id] = unit.id
                unit_id = unit_ids[si.unit_id]
            return StepIngredient(
                public_id=keeper.take(si.id),
                ingredient_id=ingredient_id,
                sub_recipe_id=sub_recipe_id,
                amount=si.amount,
                unit_id=unit_id,
                translations={
                    k: NoteText(v.note.strip()) for k, v in si.notes.items() if v.note.strip()
                },
            )

        steps: list[RecipeStep] = []
        for number, step in enumerate(cmd.steps, start=1):
            self._check_mentions(
                number,
                {locale: t.text for locale, t in step.translations.items()},
                {si.ingredient_id.lower() for si in step.ingredients if si.ingredient_id},
                {si.sub_recipe_id.lower() for si in step.ingredients if si.sub_recipe_id},
                {se.equipment_id.lower() for se in step.equipment},
            )
            ingredients = [await line(si, ids.lines) for si in step.ingredients]
            equipment: list[StepEquipment] = []
            for se in step.equipment:
                if se.equipment_id not in equipment_ids:
                    item = await self._equipment.get_by_public_id(se.equipment_id)
                    if item is None:
                        raise EquipmentNotFoundError(
                            "An equipment item of the recipe does not exist."
                        )
                    equipment_ids[se.equipment_id] = item.id
                if se.count is not None and not 1 <= se.count <= 100:
                    raise InvalidRecipeError("An equipment count runs from 1 to 100.")
                equipment.append(
                    StepEquipment(
                        public_id=ids.equipment.take(se.id),
                        equipment_id=equipment_ids[se.equipment_id],
                        count=se.count,
                        translations={
                            k: NoteText(v.note.strip())
                            for k, v in se.notes.items()
                            if v.note.strip()
                        },
                    )
                )
            steps.append(
                RecipeStep(
                    public_id=ids.steps.take(step.id),
                    translations={
                        k: StepText(v.text.strip())
                        for k, v in step.translations.items()
                        if v.text.strip()
                    },
                    duration_minutes=step.duration_minutes,
                    image_file_id=await self._file_id(
                        actor, step.image_file_id, kept=kept, restored=restored
                    ),
                    ingredients=ingredients,
                    equipment=equipment,
                )
            )
        recipe.original_locale = cmd.original_locale
        recipe.translations = {
            k: RecipeText(v.title.strip(), v.description.strip(), v.tips.strip())
            for k, v in cmd.translations.items()
        }
        recipe.base_servings = cmd.base_servings
        recipe.prep_minutes = cmd.prep_minutes
        recipe.cook_minutes = cmd.cook_minutes
        recipe.rest_minutes = cmd.rest_minutes
        recipe.difficulty = cmd.difficulty
        recipe.cover_file_id = await self._file_id(
            actor, cmd.cover_file_id, kept=kept, restored=restored
        )
        recipe.source_url = (cmd.source_url or "").strip() or None
        recipe.source_name = (cmd.source_name or "").strip() or None
        recipe.tag_ids = tag_ids
        recipe.steps = steps
        recipe.ingredients = [await line(si, ids.declared) for si in cmd.ingredients]
        recipe.yield_amount = cmd.yield_amount
        recipe.yield_unit_id = None
        if cmd.yield_unit_id:
            unit = await self._units.get_by_public_id(cmd.yield_unit_id)
            if unit is None:
                raise UnitNotFoundError("The unit of the yield does not exist.")
            recipe.yield_unit_id = unit.id
        recipe.changed = now_utc()
        if actor is not None:
            await self._apply_visibility(actor, recipe, cmd)
        validate_recipe(recipe)
        await self._check_sub_recipes(recipe)
        if recipe.status is RecipeStatus.PUBLISHED:
            try:
                validate_publishable(recipe)
            except InvalidRecipeError:
                if not unpublish_when_incomplete:
                    raise
                recipe.status = RecipeStatus.DRAFT

    async def create(
        self,
        actor: User,
        cmd: RecipeCommand,
        *,
        created_via: CreatedVia = CreatedVia.WEB,
        commit: bool = True,
        from_source: bool = False,
        origin: tuple[UUID, UUID] | None = None,
    ) -> Recipe:
        """A new draft of the actor's. An import passes `from_source` (the
        command names source step and line ids) and the `origin` it came
        from: the source instance id and the recipe's public id there."""
        if not actor.has_permission(Permission.WRITE_RECIPES):
            raise PermissionDeniedError("Creating recipes needs write:recipes.")
        now = now_utc()
        recipe = Recipe(
            owner_id=actor.id or None,
            original_locale=cmd.original_locale,
            created=now,
            changed=now,
            created_via=created_via,
        )
        if origin is not None:
            recipe.origin_instance_id, recipe.origin_public_id = origin
        await self._apply(actor, recipe, cmd, from_source=from_source)
        saved = await self._recipes.save(recipe)
        await self._revisions.record(
            saved, RevisionKind.CREATED, actor, via=created_via, note=cmd.revision_note
        )
        if commit:
            await self._uow.commit()
        return saved

    async def update(
        self,
        actor: User,
        public_id: str,
        cmd: RecipeCommand,
        *,
        via: CreatedVia = CreatedVia.WEB,
        from_source: bool = False,
        commit: bool = True,
    ) -> Recipe:
        """Saves new content. An import updating its earlier import passes
        `from_source` (source step and line ids) and `commit=False`, and a
        published recipe it updates goes back to draft when the new content
        may not be published."""
        recipe = await self.get_editable(actor, public_id)
        await self._apply(
            actor,
            recipe,
            cmd,
            from_source=from_source,
            unpublish_when_incomplete=from_source,
        )
        saved = await self._recipes.save(recipe)
        await self._revisions.record(
            saved, RevisionKind.UPDATED, actor, via=via, note=cmd.revision_note
        )
        await self._sync(saved)
        if commit:
            await self._uow.commit()
        return saved

    async def save_mirror(
        self,
        recipe: Recipe,
        cmd: RecipeCommand,
        *,
        system: User,
        note: str,
        record: bool = True,
    ) -> Recipe:
        """Writes a mirror's content, built from its source, without an
        actor's checks: the mirror builder decided what the content is.
        Step and line ids derive from the source ids (`step_ids`), so they
        stay the same across updates. With `record` a revision is appended,
        so variations on the mirror can tell that the source changed."""
        created = not recipe.id
        await self._apply(None, recipe, cmd, from_source=True)
        saved = await self._recipes.save(recipe)
        if record:
            await self._revisions.record(
                saved,
                RevisionKind.CREATED if created else RevisionKind.UPDATED,
                system,
                via=CreatedVia.PEER,
                note=note,
            )
        return saved

    async def publish(self, actor: User, public_id: str) -> Recipe:
        recipe = await self.get_deletable(actor, public_id)
        validate_publishable(recipe)
        recipe.status = RecipeStatus.PUBLISHED
        recipe.published_at = recipe.published_at or now_utc()
        recipe.changed = now_utc()
        saved = await self._recipes.save(recipe)
        await self._announce(saved)
        await self._sync(saved)
        await self._uow.commit()
        return saved

    async def _announce(self, recipe: Recipe) -> None:
        """`recipe.published` for subscribers, in plain text without
        Markdown or mentions; a private recipe is never announced. The
        visibility is the one that applies, so a public recipe is announced
        as instance while public recipes are not allowed, and a peers recipe
        while peering is off."""
        if self._events is None or recipe.visibility is RecipeVisibility.PRIVATE:
            return
        privacy = await self._settings.get_privacy()
        _, text = resolve(recipe.translations, None, recipe.original_locale)
        await self._events.publish(
            RECIPE_PUBLISHED,
            {
                "recipe": {
                    "id": str(recipe.public_id),
                    "title": plain_text(text.title),
                    "description": plain_text(text.description),
                    "locale": recipe.original_locale,
                    "visibility": privacy.effective_visibility(
                        recipe.visibility.value,
                        peering=(await self._settings.get_features()).peering,
                    ),
                }
            },
        )

    async def unpublish(self, actor: User, public_id: str) -> Recipe:
        recipe = await self.get_deletable(actor, public_id)
        recipe.status = RecipeStatus.DRAFT
        recipe.changed = now_utc()
        saved = await self._recipes.save(recipe)
        await self._sync(saved)
        await self._uow.commit()
        return saved

    async def deletion_impact(self, actor: User, public_id: str) -> tuple[list[Recipe], int]:
        """The recipes using this one as a sub-recipe that the actor can see,
        and how many others do; any of them blocks the deletion."""
        recipe = await self.get_deletable(actor, public_id)
        viewer = await self._viewers.of(actor)
        parents = await RecipeDeletion(recipe_repo=self._recipes, file_repo=self._files).parents(
            recipe
        )
        visible = [p for p in parents if can_view_recipe(viewer, p)]
        return visible, len(parents) - len(visible)

    async def delete(self, actor: User, public_id: str) -> None:
        recipe = await self.get_deletable(actor, public_id)
        await RecipeDeletion(
            recipe_repo=self._recipes,
            file_repo=self._files,
            events=self._events,
            sharing=self._sharing,
        ).stage(recipe)
        await self._uow.commit()

    # ── Co-editors and copies ────────────────────────────────────────

    async def co_editors(self, actor: User, public_id: str) -> list[int]:
        recipe = await self.get_editable(actor, public_id)
        return list(recipe.co_editor_ids)

    async def set_co_editors(self, actor: User, public_id: str, user_ids: list[str]) -> Recipe:
        """Replaces the recipe's co-editors; the owner's call alone. Each one
        is an active person other than the owner who can see the recipe."""
        recipe = await self.get_visible(actor, public_id)
        assert_not_mirror(await self._viewers.of(actor), recipe)
        if not can_manage_co_editors(await self._viewers.of(actor), recipe):
            raise PermissionDeniedError("Only the recipe's owner chooses its co-editors.")
        chosen: list[int] = []
        for user_public_id in dict.fromkeys(user_ids):
            user = await self._users.get_by_public_id(user_public_id)
            if user is None:
                raise UserNotFoundError("One of the co-editors does not exist.")
            if user.id == recipe.owner_id:
                raise CoEditorError("The owner edits the recipe anyway.")
            if not user.is_active or user.is_service_account:
                raise CoEditorError("A co-editor must be an active person.")
            if not can_view_recipe(await self._viewers.of(user), recipe):
                raise CoEditorError(
                    f"{user.display_name} cannot see this recipe; share it with them first."
                )
            chosen.append(user.id)
        recipe.co_editor_ids = chosen
        saved = await self._recipes.save(recipe)
        await self._uow.commit()
        return saved

    async def copy(self, actor: User, public_id: str) -> Recipe:
        """ "Copy as my recipe": an independent draft of the actor's with the
        same content, linked to the original. It keeps the original's images
        and sub-recipe lines; the visibility is the actor's default. A copy
        of a mirror, or of such a copy, is capped for good: it never goes to
        a paired instance and is never public. Its plain-text lines, which a
        local recipe cannot hold, are added to the text of their step."""
        if not actor.has_permission(Permission.WRITE_RECIPES):
            raise PermissionDeniedError("Copying a recipe needs write:recipes.")
        original = await self.get_visible(actor, public_id)
        plain = await self._plain_lines(original)
        mirrored_subs = {
            r.id: r for r in await self._recipes.get_many(original.sub_recipe_ids) if r.is_mirror
        }
        if mirrored_subs:
            await self._sub_recipe_labels(original, mirrored_subs, plain)
        now = now_utc()
        recipe = replace(
            original,
            id=0,
            public_id=uuid4(),
            owner_id=actor.id or None,
            status=RecipeStatus.DRAFT,
            published_at=None,
            created=now,
            changed=now,
            created_via=CreatedVia.WEB,
            co_editor_ids=[],
            shared_user_ids=[],
            shared_group_ids=[],
            shared_peer_ids=[],
            based_on_recipe_id=original.id,
            origin_instance_id=None,
            origin_public_id=None,
            mirror_peer_id=None,
            peer_capped=original.peer_capped or original.is_mirror,
            translations=dict(original.translations),
            tag_ids=list(original.tag_ids),
            # A copy is a recipe of its own, so its steps and lines get ids of
            # their own too.
            steps=[
                replace(
                    step,
                    public_id=uuid4(),
                    translations=_with_plain_lines(step.translations, plain.get(index, [])),
                    ingredients=[
                        replace(si, public_id=uuid4(), translations=dict(si.translations))
                        for si in step.ingredients
                        if si.sub_recipe_id not in mirrored_subs
                    ],
                    equipment=[
                        replace(se, public_id=uuid4(), translations=dict(se.translations))
                        for se in step.equipment
                    ],
                )
                for index, step in enumerate(original.steps)
            ],
            ingredients=[
                replace(line, public_id=uuid4(), translations=dict(line.translations))
                for line in original.ingredients
                if line.sub_recipe_id not in mirrored_subs
            ],
        )
        recipe.visibility = self._capped(recipe, await self._default_visibility(actor))
        validate_recipe(recipe)
        saved = await self._recipes.save(recipe)
        await self._revisions.record(saved, RevisionKind.CREATED, actor)
        await self._uow.commit()
        return saved

    async def _sub_recipe_labels(
        self,
        recipe: Recipe,
        mirrored: dict[int, Recipe],
        labels: dict[int, list[dict[str, str]]],
    ) -> None:
        """A copy never links a mirror as its sub-recipe, since the mirror
        may vanish; such a line becomes text in its step."""
        units = {u.id: u for u in await self._units.list_all()}
        for index, step in enumerate(recipe.steps):
            for si in step.ingredients:
                sub = mirrored.get(si.sub_recipe_id) if si.sub_recipe_id else None
                if sub is None:
                    continue
                label: dict[str, str] = {}
                for locale, text in sub.translations.items():
                    unit = units.get(si.unit_id) if si.unit_id is not None else None
                    unit_name = (
                        resolve(unit.translations, locale, "")[1].name
                        if unit is not None and unit.translations
                        else ""
                    )
                    amount = f"{si.amount:g} " if si.amount is not None else ""
                    label[locale] = f"{amount}{unit_name + ' ' if unit_name else ''}{text.title}"
                labels.setdefault(index, []).append(label)

    async def _plain_lines(self, recipe: Recipe) -> dict[int, list[dict[str, str]]]:
        """Per step index, the labels of a mirror's plain-text lines per
        locale."""
        if not recipe.is_mirror or self._mirrors is None:
            return {}
        mirror = await self._mirrors.get(recipe.id)
        found: dict[int, list[dict[str, str]]] = {}
        for line in (mirror.extras if mirror else {}).get("plain_lines", []):
            labels = line.get("labels") or {}
            if isinstance(labels, dict) and labels:
                found.setdefault(int(line.get("step", 0)), []).append(
                    {str(k): str(v) for k, v in labels.items()}
                )
        return found

    async def copies(self, actor: User, public_id: str) -> list[Recipe]:
        """The copies of a recipe the actor may see."""
        recipe = await self.get_visible(actor, public_id)
        viewer = await self._viewers.of(actor)
        return [r for r in await self._recipes.copies_of(recipe.id) if can_view_recipe(viewer, r)]

    async def _check_translation_mentions(
        self, recipe: Recipe, locale: str, steps: list[StepText]
    ) -> None:
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
        for number, (step, text) in enumerate(zip(recipe.steps, steps, strict=False), start=1):
            self._check_mentions(
                number,
                {locale: text.text},
                {
                    ingredients[si.ingredient_id]
                    for si in step.ingredients
                    if si.ingredient_id in ingredients
                },
                {subs[si.sub_recipe_id] for si in step.ingredients if si.sub_recipe_id in subs},
                {
                    equipment[se.equipment_id]
                    for se in step.equipment
                    if se.equipment_id in equipment
                },
            )

    async def set_image(
        self,
        actor: User,
        public_id: str,
        file_public_id: str,
        step_index: int | None,
        *,
        via: CreatedVia = CreatedVia.WEB,
    ) -> Recipe:
        """Makes a stored image the recipe's cover, or the image of the step
        at `step_index` (0-based)."""
        recipe = await self.get_editable(actor, public_id)
        file_id = await self._file_id(
            actor, file_public_id, kept=frozenset(await self._recipes.file_ids(recipe))
        )
        if step_index is None:
            recipe.cover_file_id = file_id
        else:
            if not 0 <= step_index < len(recipe.steps):
                raise InvalidRecipeError("The recipe has no such step.")
            recipe.steps[step_index].image_file_id = file_id
        recipe.changed = now_utc()
        saved = await self._recipes.save(recipe)
        await self._revisions.record(saved, RevisionKind.IMAGE_ATTACHED, actor, via=via)
        await self._sync(saved)
        await self._uow.commit()
        return saved

    async def add_translation(
        self,
        actor: User,
        public_id: str,
        locale: str,
        text: RecipeText,
        steps: list[StepText],
        notes: list[list[NoteText]] | None = None,
        ingredient_notes: list[NoteText] | None = None,
        *,
        via: CreatedVia = CreatedVia.WEB,
    ) -> Recipe:
        """Adds or replaces the text of one language: the recipe's title,
        description and tips, each step's text in order and optionally each
        step ingredient's note and each declared line's note."""
        recipe = await self.get_editable(actor, public_id)
        await self._check_translation_mentions(recipe, locale, steps)
        recipe.translations[locale] = RecipeText(
            text.title.strip(), text.description.strip(), text.tips.strip()
        )
        for index, step in enumerate(recipe.steps):
            if index < len(steps) and steps[index].text.strip():
                step.translations[locale] = StepText(steps[index].text.strip())
            if notes is not None and index < len(notes):
                for si, note in zip(step.ingredients, notes[index], strict=False):
                    if note.note.strip():
                        si.translations[locale] = NoteText(note.note.strip())
        if ingredient_notes is not None:
            for line, note in zip(recipe.ingredients, ingredient_notes, strict=False):
                if note.note.strip():
                    line.translations[locale] = NoteText(note.note.strip())
        recipe.changed = now_utc()
        validate_recipe(recipe)
        saved = await self._recipes.save(recipe)
        await self._revisions.record(saved, RevisionKind.TRANSLATED, actor, via=via)
        await self._sync(saved)
        await self._uow.commit()
        return saved

    # ── Revisions ────────────────────────────────────────────────────

    async def revisions(
        self, actor: User, public_id: str, *, limit: int, offset: int
    ) -> tuple[list[RecipeRevision], int]:
        """The recipe's history, newest first, for whoever may edit it."""
        recipe = await self.get_editable(actor, public_id)
        return await self._revision_repo.page(recipe.id, limit=limit, offset=offset)

    async def revision(self, actor: User, public_id: str, number: int) -> RecipeRevision:
        recipe = await self.get_editable(actor, public_id)
        found = await self._revision_repo.get(recipe.id, number)
        if found is None:
            raise RecipeRevisionNotFoundError("The recipe has no such revision.")
        return replace(found, snapshot=upgrade_snapshot(found.snapshot))

    async def _restorable(self, snapshot: dict[str, Any]) -> RecipeCommand:
        """The snapshot as a save command. Images that no longer exist are
        dropped; any other missing reference fails with its recorded name."""

        async def present(kind: str, public_id: str | None, exists: Any) -> str | None:
            if not public_id:
                return None
            if await exists(public_id) is None:
                label = {
                    "ingredients": "ingredient",
                    "units": "unit",
                    "tags": "tag",
                    "equipment": "equipment item",
                    "recipes": "sub-recipe",
                }[kind]
                name = display_name(snapshot, kind, public_id, snapshot.get("original_locale", ""))
                raise RevisionRestoreError(
                    f"The {label} {name!r} no longer exists, so this version cannot be restored.",
                    kind=label,
                    name=name,
                )
            return public_id

        async def image(public_id: str | None) -> str | None:
            if not public_id or await self._files.get_by_public_id(public_id) is None:
                return None
            return public_id

        async def line(si: dict[str, Any]) -> StepIngredientCommand:
            return StepIngredientCommand(
                id=si.get("id"),
                ingredient_id=await present(
                    "ingredients", si.get("ingredient_id"), self._ingredients.get_by_public_id
                ),
                sub_recipe_id=await present(
                    "recipes", si.get("sub_recipe_id"), self._recipes.get_by_public_id
                ),
                amount=si.get("amount"),
                unit_id=await present("units", si.get("unit_id"), self._units.get_by_public_id),
                notes={k: NoteText(v["note"]) for k, v in si.get("notes", {}).items()},
            )

        steps: list[StepCommand] = []
        for step in snapshot.get("steps", []):
            ingredients = [await line(si) for si in step.get("ingredients", [])]
            equipment = [
                StepEquipmentCommand(
                    id=se.get("id"),
                    equipment_id=str(
                        await present(
                            "equipment", se.get("equipment_id"), self._equipment.get_by_public_id
                        )
                    ),
                    count=se.get("count"),
                    notes={k: NoteText(v["note"]) for k, v in se.get("notes", {}).items()},
                )
                for se in step.get("equipment", [])
                if se.get("equipment_id")
            ]
            steps.append(
                StepCommand(
                    id=step.get("id"),
                    translations={
                        k: StepText(v["text"]) for k, v in step.get("translations", {}).items()
                    },
                    duration_minutes=step.get("duration_minutes"),
                    image_file_id=await image(step.get("image_id")),
                    ingredients=ingredients,
                    equipment=equipment,
                )
            )
        tag_ids = [
            t
            for t in [
                await present("tags", t, self._tags.get_by_public_id)
                for t in snapshot.get("tag_ids", [])
            ]
            if t
        ]
        return RecipeCommand(
            original_locale=snapshot["original_locale"],
            translations={
                k: RecipeText(v.get("title", ""), v.get("description", ""), v.get("tips", ""))
                for k, v in snapshot.get("translations", {}).items()
            },
            base_servings=snapshot.get("base_servings", 4),
            prep_minutes=snapshot.get("prep_minutes"),
            cook_minutes=snapshot.get("cook_minutes"),
            rest_minutes=snapshot.get("rest_minutes"),
            difficulty=Difficulty(snapshot.get("difficulty", Difficulty.EASY.value)),
            cover_file_id=await image(snapshot.get("cover_image_id")),
            source_url=snapshot.get("source_url"),
            source_name=snapshot.get("source_name"),
            tag_ids=tag_ids,
            steps=steps,
            # Snapshots written before the declared list existed have none.
            ingredients=[await line(si) for si in snapshot.get("ingredients", [])],
            yield_amount=snapshot.get("yield_amount"),
            yield_unit_id=await present(
                "units", snapshot.get("yield_unit_id"), self._units.get_by_public_id
            ),
        )

    async def restore(
        self, actor: User, public_id: str, number: int, *, via: CreatedVia = CreatedVia.WEB
    ) -> Recipe:
        """Writes an old revision's content as the current recipe and
        records a `restored` revision. History is never rewritten, and the
        status, visibility and shares stay as they are."""
        revision = await self.revision(actor, public_id, number)
        recipe = await self.get_editable(actor, public_id)
        await self._apply(
            actor, recipe, await self._restorable(revision.snapshot), restoring=revision.snapshot
        )
        saved = await self._recipes.save(recipe)
        await self._revisions.record(
            saved, RevisionKind.RESTORED, actor, via=via, restored_from=revision.number
        )
        await self._sync(saved)
        await self._uow.commit()
        return saved


def _snapshot_images(snapshot: dict[str, Any] | None) -> frozenset[str]:
    """The public ids of the cover and step images a revision recorded."""
    if not snapshot:
        return frozenset()
    ids = [snapshot.get("cover_image_id"), *(s.get("image_id") for s in snapshot.get("steps", []))]
    return frozenset(str(i).lower() for i in ids if i)


def _with_plain_lines(
    translations: dict[str, StepText], labels: list[dict[str, str]]
) -> dict[str, StepText]:
    """The step text with the plain-text lines of a mirror's step added as a
    list at its end, in each language the step is written in."""
    if not labels:
        return dict(translations)
    result: dict[str, StepText] = {}
    for locale, text in translations.items():
        lines = [
            f"- {label.get(locale) or next(iter(label.values()))}" for label in labels if label
        ]
        result[locale] = StepText(f"{text.text.rstrip()}\n\n" + "\n".join(lines))
    return result
