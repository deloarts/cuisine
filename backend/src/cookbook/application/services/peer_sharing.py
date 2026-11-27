"""
Sending recipes to paired instances: which peers receive a recipe, what
they receive, and the peer channel events that tell them.

A peer whose switch `users_may_share` is on receives a published recipe of
this instance when the owner shares it with that peer inside the visibility
`shared`, and every published recipe whose effective visibility is `peers`
or `public` (`peers` reads as `instance` while peering is off, `public`
while public recipes are not allowed). A peer with the switch off receives
nothing. Drafts, recipes without an owner, mirrors and copies of mirrors
(`peer_capped`) never leave.

Every path that changes what a peer receives calls `sync` (or `refresh` by
public id, or `resync` for a switch that touches many recipes: a peer's
switch, the peering feature, the public recipes switch) inside its own
transaction, and a new pairing calls `announce`. `sync` compares, per peer,
what the peer should hold now with the latest event the peer was sent and
publishes exactly the difference: `item.shared` for a peer that gains the
recipe, `item.updated` when its content for that peer changed,
`item.withdrawn` for a peer that loses it. The recipes using a changed
recipe as a sub-recipe are compared too, since their payload names the
sub-recipe's title only while that sub-recipe goes to the same peer.

The payload is a `.cui` file of the one recipe for that peer: its content,
its author's display name and avatar only when the author shows their name
on paired instances, its variations that are as visible as the recipe (never a
private one, and none for a peer without the `variations` capability), a
catalogue entry for everything it names and its images. A sub-recipe is an
item of its own; the payload names it by its public id, and by title only
when it goes to the same peer. The revision of an item is a hash over that
payload and the images' content, so it changes with the content, the
variations, the images and anything else the peer receives.
"""

import hashlib
import io
import json
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from dataclasses import replace

from src.cookbook.application.services.formats.catalogue_mapper import equipment_entry
from src.cookbook.application.services.formats.catalogue_mapper import ingredient_entry
from src.cookbook.application.services.formats.catalogue_mapper import tag_entry
from src.cookbook.application.services.formats.catalogue_mapper import unit_entry
from src.cookbook.application.services.formats.catalogue_v1 import CatalogueSectionV1
from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.codec import to_json
from src.cookbook.application.services.formats.recipe_mapper import UsedRecords
from src.cookbook.application.services.formats.recipe_mapper import collect_used
from src.cookbook.application.services.formats.recipe_mapper import recipe_content
from src.cookbook.application.services.formats.recipe_mapper import variation_entry
from src.cookbook.application.services.formats.recipes_v1 import FORMAT
from src.cookbook.application.services.formats.recipes_v1 import MANIFEST
from src.cookbook.application.services.formats.recipes_v1 import VERSION
from src.cookbook.application.services.formats.recipes_v1 import FileEntryV1
from src.cookbook.application.services.formats.recipes_v1 import RecipeEntryV1
from src.cookbook.application.services.formats.recipes_v1 import RecipesDocumentV1
from src.cookbook.application.services.formats.recipes_v1 import VariationV1
from src.cookbook.application.services.revisions import RevisionRecorder
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.recipe_rules import effective_visibility
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RecipeVisibility
from src.cookbook.ports.outbound.peer_publisher import IPeerPublisher
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.peer import Peer
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.services.peer_channel_rules import ITEM_SHARED
from src.platform.domain.services.peer_channel_rules import ITEM_UPDATED
from src.platform.domain.services.peer_channel_rules import ITEM_WITHDRAWN
from src.platform.ports.outbound.peer_content import PeerItem
from src.platform.ports.outbound.peer_content import SharedItem
from src.platform.ports.outbound.repositories.peer_repository import IPeerRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.shared_kernel.domain.services.clock import now_utc

# The item kind of recipes on a peer channel.
RECIPE_KIND = "recipe"
CUI_MEDIA_TYPE = "application/vnd.cuisine.recipe+zip"
# The capability a peer announces when it can show variations.
VARIATIONS_CAPABILITY = "variations"
# How far up the sub-recipe tree a change is compared: three levels of
# sub-recipes below the top recipe.
_MAX_PARENT_LEVELS = 4


@dataclass(frozen=True)
class _Context:
    """What decides the audience, read once per call."""

    peers: dict[int, Peer]
    public_allowed: bool
    peering: bool
    instance_id: str


@dataclass(frozen=True)
class PeerPayload:
    document: RecipesDocumentV1
    files: dict[str, StoredFile]
    revision: str
    # The keys of `files` that are avatars; they travel as their thumbnail.
    avatars: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _Author:
    """What a peer learns of an author: nothing, or the display name and
    the avatar, when the author shows their name on paired instances."""

    name: str | None = None
    avatar: StoredFile | None = None

    @property
    def avatar_key(self) -> str | None:
        return str(self.avatar.public_id) if self.avatar is not None else None


class PeerRecipeSharing:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        variation_repo: IRecipeVariationRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        peer_repo: IPeerRepository,
        file_repo: IStoredFileRepository,
        revisions: RevisionRecorder,
        publisher: IPeerPublisher,
    ) -> None:
        self._recipes = recipe_repo
        self._variations = variation_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._categories = category_repo
        self._families = family_repo
        self._users = user_repo
        self._settings = settings_repo
        self._peers = peer_repo
        self._files = file_repo
        self._revisions = revisions
        self._publisher = publisher

    async def _context(self) -> _Context:
        return _Context(
            peers={p.id: p for p in await self._peers.list_active()},
            public_allowed=(await self._settings.get_privacy()).allow_public_recipes,
            peering=(await self._settings.get_features()).peering,
            instance_id=str(await self._settings.instance_id()),
        )

    # ── Who receives a recipe ────────────────────────────────────────

    @staticmethod
    def _audience(recipe: Recipe, ctx: _Context) -> set[int]:
        if (
            recipe.status is not RecipeStatus.PUBLISHED
            or recipe.owner_id is None
            or recipe.is_mirror
            or recipe.peer_capped
        ):
            return set()
        allowed = {p.id for p in ctx.peers.values() if p.users_may_share}
        if recipe.visibility is RecipeVisibility.SHARED:
            return {p for p in recipe.shared_peer_ids if p in allowed}
        effective = effective_visibility(
            recipe.visibility, public_allowed=ctx.public_allowed, peering=ctx.peering
        )
        if effective in (RecipeVisibility.PEERS, RecipeVisibility.PUBLIC):
            return allowed
        return set()

    async def peers_of(self, recipe: Recipe) -> set[int]:
        """The peers that receive the recipe as it is now."""
        return self._audience(recipe, await self._context())

    # ── What a peer receives ─────────────────────────────────────────

    async def _author(self, user_id: int | None, known: dict[int, _Author]) -> _Author:
        if user_id is None:
            return _Author()
        if user_id not in known:
            user = await self._users.get(user_id)
            if user is None or not user.show_name_on_paired_instances:
                known[user_id] = _Author()
            else:
                avatar = await self._files.get(user.avatar_file_id) if user.avatar_file_id else None
                shown = avatar if avatar is not None and avatar.thumbnail_hash else None
                known[user_id] = _Author(name=user.display_name, avatar=shown)
        return known[user_id]

    async def _catalogue(self, used: UsedRecords) -> CatalogueSectionV1:
        units = {str(u.public_id): u for u in await self._units.list_all()}
        tags = {str(t.public_id): t for t in await self._tags.list_all()}
        categories = {c.id: c for c in await self._categories.list_all()}
        families = {f.id: f for f in await self._families.list_all()}
        unit_ids = {u.id: public_id for public_id, u in units.items()}
        ingredients: dict[str, IngredientEntryV1] = {}
        for public_id in sorted(used.ingredients):
            found = await self._ingredients.get_by_public_id(public_id)
            if found is None:
                continue
            entry = ingredient_entry(
                found, categories=categories, families=families, unit_ids=unit_ids
            )
            used.units |= {c.unit_id for c in entry.conversions}
            ingredients[public_id] = entry
        equipment: dict[str, EquipmentEntryV1] = {}
        for public_id in sorted(used.equipment):
            item = await self._equipment.get_by_public_id(public_id)
            if item is not None:
                equipment[public_id] = equipment_entry(item)
        return CatalogueSectionV1(
            units={k: unit_entry(units[k]) for k in sorted(used.units) if k in units},
            tags={k: tag_entry(tags[k]) for k in sorted(used.tags) if k in tags},
            ingredients=ingredients,
            equipment=equipment,
        )

    async def payload(self, recipe: Recipe, peer: Peer, ctx: _Context | None = None) -> PeerPayload:
        """The recipe as `peer` receives it, with the revision that names
        this exact content."""
        ctx = ctx or await self._context()
        content = recipe_content(recipe, await self._revisions.refs(recipe))
        subs = await self._recipes.get_many(recipe.sub_recipe_ids)
        shown = {str(s.public_id) for s in subs if peer.id in self._audience(s, ctx)}
        content = replace(
            content,
            names=replace(
                content.names,
                recipes={k: v for k, v in content.names.recipes.items() if k in shown},
            ),
        )
        authors: dict[int, _Author] = {}
        variations: list[VariationV1] = []
        if VARIATIONS_CAPABILITY in peer.capabilities:
            for v in await self._variations.for_recipe(recipe.id):
                if v.private or v.mirrored:
                    continue
                author = await self._author(v.author_id, authors)
                variations.append(
                    replace(variation_entry(v, author.name), author_avatar=author.avatar_key)
                )
        owner = await self._author(recipe.owner_id, authors)
        used = UsedRecords()
        collect_used(used, content, variations)
        catalogue = await self._catalogue(used)
        files: dict[str, StoredFile] = {}
        entries: dict[str, FileEntryV1] = {}
        for public_id in sorted(used.files):
            stored = await self._files.get_by_public_id(public_id)
            if stored is None:
                continue
            files[public_id] = stored
            entries[public_id] = FileEntryV1(
                path=f"files/{public_id}", name=stored.file_name, content_type=stored.content_type
            )
        avatars: set[str] = set()
        for author in authors.values():
            if author.avatar is None or author.avatar_key in files:
                continue
            key = str(author.avatar.public_id)
            avatars.add(key)
            files[key] = author.avatar
            entries[key] = FileEntryV1(
                path=f"files/{key}", name="avatar.webp", content_type="image/webp"
            )
        document = RecipesDocumentV1(
            format=FORMAT,
            version=VERSION,
            exported_at="",
            instance_id=ctx.instance_id,
            recipes=[
                RecipeEntryV1(
                    id=str(recipe.public_id),
                    title=resolve(recipe.translations, None, recipe.original_locale)[1].title,
                    status=recipe.status.value,
                    snapshot=content,
                    variations=variations,
                    author_name=owner.name,
                    author_avatar=owner.avatar_key,
                )
            ],
            catalogue=catalogue,
            files=entries,
        )
        digest = hashlib.sha256(
            json.dumps(to_json(document), sort_keys=True, ensure_ascii=False).encode()
        )
        for public_id, stored in sorted(files.items()):
            digest.update(f"{public_id}:{stored.content_hash}".encode())
        return PeerPayload(
            document=document,
            files=files,
            revision=digest.hexdigest()[:40],
            avatars=frozenset(avatars),
        )

    async def _package(self, payload: PeerPayload) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for public_id, stored in sorted(payload.files.items()):
                data = await self._files.read_content(
                    stored, thumbnail=public_id in payload.avatars
                )
                if data is not None:
                    archive.writestr(f"files/{public_id}", data)
            document = replace(payload.document, exported_at=now_utc().isoformat())
            archive.writestr(MANIFEST, json.dumps(to_json(document), ensure_ascii=False))
        return buffer.getvalue()

    # ── The provider side of the peer channel ────────────────────────

    async def _candidates(self, peer: Peer) -> list[Recipe]:
        found = {r.id: r for r in await self._recipes.shared_with_peer(peer.id)}
        found |= {r.id: r for r in await self._recipes.published_for_peers()}
        return list(found.values())

    async def shared_with(self, peer: Peer) -> list[SharedItem]:
        ctx = await self._context()
        if peer.id not in ctx.peers:
            return []
        items = []
        for recipe in await self._candidates(peer):
            if peer.id in self._audience(recipe, ctx):
                payload = await self.payload(recipe, ctx.peers[peer.id], ctx)
                items.append(SharedItem(item_id=str(recipe.public_id), revision=payload.revision))
        return sorted(items, key=lambda i: i.item_id)

    async def fetch(self, peer: Peer, item_id: str) -> PeerItem | None:
        """The recipe as the peer receives it, or None when it does not go
        to that peer (any more). Checked now, whatever the channel says."""
        recipe = await self._recipes.get_by_public_id(item_id)
        if recipe is None:
            return None
        ctx = await self._context()
        if peer.id not in self._audience(recipe, ctx):
            return None
        payload = await self.payload(recipe, ctx.peers[peer.id], ctx)
        return PeerItem(
            item_id=str(recipe.public_id),
            content=await self._package(payload),
            media_type=CUI_MEDIA_TYPE,
            etag=f'"{payload.revision}"',
        )

    # ── Publishing changes ───────────────────────────────────────────

    async def _with_parents(self, recipes: Iterable[Recipe]) -> list[Recipe]:
        found: dict[int, Recipe] = {r.id: r for r in recipes if r.id}
        frontier = set(found)
        for _ in range(_MAX_PARENT_LEVELS):
            parents = await self._recipes.parent_ids(sorted(frontier))
            new = {p for ids in parents.values() for p in ids} - set(found)
            if not new:
                break
            for parent in await self._recipes.get_many(sorted(new)):
                found[parent.id] = parent
            frontier = new
        return list(found.values())

    async def _compare(self, recipe: Recipe, ctx: _Context) -> None:
        item_id = str(recipe.public_id)
        before = await self._publisher.last_published(RECIPE_KIND, item_id)
        now = self._audience(recipe, ctx)
        for peer_id in sorted(now):
            revision = (await self.payload(recipe, ctx.peers[peer_id], ctx)).revision
            held = before.get(peer_id)
            if held is None or held[0] == ITEM_WITHDRAWN:
                await self._publisher.publish(peer_id, ITEM_SHARED, RECIPE_KIND, item_id, revision)
            elif held[1] != revision:
                await self._publisher.publish(peer_id, ITEM_UPDATED, RECIPE_KIND, item_id, revision)
        for peer_id, (type_, _) in sorted(before.items()):
            if peer_id not in now and type_ != ITEM_WITHDRAWN:
                await self._publisher.publish(peer_id, ITEM_WITHDRAWN, RECIPE_KIND, item_id, None)

    async def sync(self, recipes: Iterable[Recipe]) -> None:
        """Publishes what changed for every peer, for the recipes and the
        recipes using them. The caller commits."""
        ctx = await self._context()
        for recipe in await self._with_parents(recipes):
            await self._compare(recipe, ctx)

    async def withdraw(self, item_ids: Iterable[str]) -> None:
        """Withdraws deleted recipes from every peer that holds them."""
        for item_id in dict.fromkeys(item_ids):
            for peer_id, (type_, _) in sorted(
                (await self._publisher.last_published(RECIPE_KIND, item_id)).items()
            ):
                if type_ != ITEM_WITHDRAWN:
                    await self._publisher.publish(
                        peer_id, ITEM_WITHDRAWN, RECIPE_KIND, item_id, None
                    )

    async def refresh(self, item_ids: Iterable[str]) -> None:
        """`sync` by public id: recipes that no longer exist are withdrawn."""
        existing: list[Recipe] = []
        gone: list[str] = []
        for item_id in dict.fromkeys(item_ids):
            recipe = await self._recipes.get_by_public_id(item_id)
            if recipe is None:
                gone.append(item_id)
            else:
                existing.append(recipe)
        await self.withdraw(gone)
        await self.sync(existing)

    async def announce(self, peer: Peer) -> None:
        """Tells a peer that was just paired, for the first time or again
        after a revoke, about every recipe it should hold now: every peers
        and public recipe, since nothing is shared with it explicitly yet.
        It runs inside the pairing transaction, where the other instance
        waits for the handshake's answer, so it builds no payloads: the
        events carry no revision, the peer fetches each recipe anyway, and
        the next comparison of a recipe (a change of it, or the daily one)
        records its revision."""
        ctx = await self._context()
        if peer.id not in ctx.peers:
            return
        for recipe in sorted(await self._candidates(peer), key=lambda r: r.id):
            if peer.id in self._audience(recipe, ctx):
                await self._publisher.publish(
                    peer.id, ITEM_SHARED, RECIPE_KIND, str(recipe.public_id), None
                )

    async def resync(self, peer_ids: Iterable[int] | None = None) -> None:
        """Compares every recipe that goes, or went, to the peers (all
        active peers without `peer_ids`), after a switch that changes the
        audience of many recipes at once."""
        ctx = await self._context()
        wanted = set(peer_ids) if peer_ids is not None else set(ctx.peers)
        item_ids: set[str] = {str(r.public_id) for r in await self._recipes.published_for_peers()}
        for peer_id in sorted(wanted):
            item_ids |= {
                item_id
                for item_id, (type_, _) in (
                    await self._publisher.published_items(peer_id, RECIPE_KIND)
                ).items()
                if type_ != ITEM_WITHDRAWN
            }
            item_ids |= {str(r.public_id) for r in await self._recipes.shared_with_peer(peer_id)}
        await self.refresh(sorted(item_ids))
