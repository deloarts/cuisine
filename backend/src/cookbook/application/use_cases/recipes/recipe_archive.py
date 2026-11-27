"""
Moving recipes between instances as `.cui` files. Anyone signed in who can
open a recipe exports it with its sub-recipes; an administrator exports many
recipes at once. Anyone with write:recipes imports such a file.

The archive is a `cuisine-recipes` document (`recipes.json`, built by the
format mappers in `application/services/formats/`) and the original image
bytes under `files/`. Each recipe carries its content, its source public id
and the variations the exporter may see; the document names the exporting
instance and holds a catalogue entry for every unit, tag, ingredient and
equipment item the recipes and variations refer to, so the importing
instance can match them. Sub-recipes the exporter may see are included and
come before the recipes that use them; a sub-recipe the exporter may not see
is left out without its title. A variation carries its author's display name
only when the exporter is the author or the author shows the name to other
instances.

Importing reads every released format version through the upgrade chain and
matches each catalogue entry to the local catalogue: by seed key first, then
by name or alias in any language (units by code). An unknown ingredient or
equipment item is created as a draft for the catalogue review queue; an
unknown unit or tag, a missing sub-recipe or an unreadable image is dropped
and reported as a conflict, as is a title that a recipe the importer can see
already has. Every imported recipe lands as a draft of the importer, with a
`created` revision, and its variations become the importer's own with an
"Originally by" note, all in one transaction.

An imported recipe records its origin: the exporting instance's id and the
recipe's public id there. When the importer already owns a recipe with the
same origin, a preview names it, and the importer chooses per recipe to
update that earlier import (a normal `updated` revision, keeping its
visibility, shares and status, and the ids of the steps, lines and
variations that came from the same source ids) or to import a new copy,
which carries no origin, since each cook holds at most one recipe per origin.
"""

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from dataclasses import replace
from typing import Any
from uuid import UUID
from uuid import uuid5

from src.cookbook.application.services._exchange import first_name
from src.cookbook.application.services._exchange import parse_uuid
from src.cookbook.application.services.catalogue_matching import CatalogueMatcher
from src.cookbook.application.services.formats.catalogue_mapper import equipment_entry
from src.cookbook.application.services.formats.catalogue_mapper import ingredient_entry
from src.cookbook.application.services.formats.catalogue_mapper import tag_entry
from src.cookbook.application.services.formats.catalogue_mapper import unit_entry
from src.cookbook.application.services.formats.catalogue_v1 import CatalogueSectionV1
from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import TagEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import UnitEntryV1
from src.cookbook.application.services.formats.codec import FormatError
from src.cookbook.application.services.formats.codec import to_json
from src.cookbook.application.services.formats.recipe_mapper import UsedRecords
from src.cookbook.application.services.formats.recipe_mapper import collect_used
from src.cookbook.application.services.formats.recipe_mapper import recipe_content
from src.cookbook.application.services.formats.recipe_mapper import variation_entry
from src.cookbook.application.services.formats.recipes_v1 import FORMAT
from src.cookbook.application.services.formats.recipes_v1 import MANIFEST
from src.cookbook.application.services.formats.recipes_v1 import VERSION
from src.cookbook.application.services.formats.recipes_v1 import FileEntryV1
from src.cookbook.application.services.formats.recipes_v1 import IngredientLineV1
from src.cookbook.application.services.formats.recipes_v1 import RecipeContentV1
from src.cookbook.application.services.formats.recipes_v1 import RecipeEntryV1
from src.cookbook.application.services.formats.recipes_v1 import RecipesDocumentV1
from src.cookbook.application.services.formats.recipes_v1 import ReferenceNamesV1
from src.cookbook.application.services.formats.recipes_v1 import VariationChangeV1
from src.cookbook.application.services.formats.recipes_v1 import VariationV1
from src.cookbook.application.services.formats.specs import RECIPES
from src.cookbook.application.services.revisions import RevisionRecorder
from src.cookbook.application.services.variation_resolver import VariationChangeCommand
from src.cookbook.application.services.variation_resolver import VariationEquipmentCommand
from src.cookbook.application.services.variation_resolver import VariationLineCommand
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.application.use_cases.equipment.manage_equipment import ManageEquipment
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ConversionCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import IngredientCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ManageIngredients
from src.cookbook.application.use_cases.recipes.manage_recipes import ManageRecipes
from src.cookbook.application.use_cases.recipes.manage_recipes import RecipeCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepEquipmentCommand
from src.cookbook.application.use_cases.recipes.manage_recipes import StepIngredientCommand
from src.cookbook.application.use_cases.recipes.manage_variations import ManageVariations
from src.cookbook.application.use_cases.recipes.manage_variations import VariationCommand
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import DuplicateNameError
from src.cookbook.domain.exceptions import MirrorReadOnlyError
from src.cookbook.domain.exceptions import RecipeArchiveError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.services.mentions import MENTION
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.translations import LOCALES
from src.cookbook.domain.services.translations import resolve
from src.cookbook.domain.services.variations import MAX_NAME
from src.cookbook.domain.services.variations import MAX_NOTE
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import VariationChangeKind
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NoteText
from src.cookbook.domain.value_objects.texts import RecipeText
from src.cookbook.domain.value_objects.texts import StepText
from src.cookbook.domain.value_objects.viewer import Viewer
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import FileTypeNotAcceptedError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.image_processor import IImageProcessor
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

MAX_RECIPES = 2_000
MAX_ENTRIES = 20_000
# What an archive may unpack to, against archives that inflate enormously.
MAX_UNPACKED_BYTES = 1024 * 1024 * 1024
MAX_IMAGE_BYTES = 25 * 1024 * 1024
_ALL = 100_000


@dataclass(frozen=True)
class ImportedRecipe:
    source_id: str
    id: str
    title: str
    # True when the import updated the importer's earlier import of it.
    updated: bool = False


@dataclass(frozen=True)
class EarlierImport:
    """A recipe of the importer's that an earlier import of the same source
    recipe created."""

    id: str
    title: str
    status: str


@dataclass(frozen=True)
class PreviewedRecipe:
    source_id: str
    title: str
    earlier: EarlierImport | None


@dataclass(frozen=True)
class ImportPreview:
    recipes: list[PreviewedRecipe]
    source_instance_id: str | None


@dataclass(frozen=True)
class ExportedFile:
    data: bytes
    # The title of the exported recipe, for the file name.
    title: str


@dataclass(frozen=True)
class ImportConflict:
    # unit, tag, ingredient, equipment, sub_recipe, image, title, variation
    # or status.
    kind: str
    name: str
    detail: str
    # The title of the imported recipe it concerns, when it concerns one.
    recipe: str | None = None


@dataclass(frozen=True)
class ImportReport:
    recipes: list[ImportedRecipe]
    created_ingredients: list[str]
    created_equipment: list[str]
    matched_ingredients: int
    matched_equipment: int
    conflicts: list[ImportConflict]
    # The instance the archive was exported from, when the archive names it.
    source_instance_id: str | None = None


def _title(recipe: Recipe) -> str:
    return resolve(recipe.translations, None, recipe.original_locale)[1].title


class RecipeArchive:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        variation_repo: IRecipeVariationRepository,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        file_repo: IStoredFileRepository,
        images: IImageProcessor,
        recipes: ManageRecipes,
        ingredients: ManageIngredients,
        equipment: ManageEquipment,
        variations: ManageVariations,
        revisions: RevisionRecorder,
        viewers: ViewerResolver,
        uow: IUnitOfWork,
    ) -> None:
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._units = unit_repo
        self._tags = tag_repo
        self._categories = category_repo
        self._families = family_repo
        self._variations = variation_repo
        self._users = user_repo
        self._settings = settings_repo
        self._files = file_repo
        self._images = images
        self._manage_recipes = recipes
        self._manage_ingredients = ingredients
        self._manage_equipment = equipment
        self._manage_variations = variations
        self._revisions = revisions
        self._viewers = viewers
        self._uow = uow

    @staticmethod
    def _assert_admin(actor: User) -> None:
        if not actor.has_permission(Permission.MANAGE_RECIPES):
            raise PermissionDeniedError("Exporting and importing recipes needs manage:recipes.")

    # ── Export ───────────────────────────────────────────────────────

    async def _selection(self, viewer: Viewer, recipe_ids: list[str] | None) -> list[Recipe]:
        if recipe_ids:
            chosen = []
            for public_id in recipe_ids:
                recipe = await self._recipes.get_by_public_id(public_id)
                if recipe is None or not can_view_recipe(viewer, recipe):
                    raise RecipeNotFoundError(f"No such recipe: {public_id}.")
                chosen.append(recipe)
            return chosen
        found, _ = await self._recipes.find(
            RecipeQuery(
                viewer_id=viewer.id,
                viewer_group_ids=sorted(viewer.group_ids),
                viewer_household_member_ids=sorted(viewer.household_member_ids),
                limit=_ALL,
            )
        )
        return found

    async def _with_sub_recipes(self, viewer: Viewer, chosen: list[Recipe]) -> list[Recipe]:
        """The chosen recipes and every sub-recipe the viewer may see, each
        sub-recipe before the recipes that use it."""
        ordered: dict[int, Recipe] = {}

        async def visit(recipe: Recipe, depth: int) -> None:
            if recipe.id in ordered or depth > 10:
                return
            for sub in await self._recipes.get_many(recipe.sub_recipe_ids):
                if can_view_recipe(viewer, sub) and not sub.is_mirror:
                    await visit(sub, depth + 1)
            ordered[recipe.id] = recipe

        for recipe in chosen:
            await visit(recipe, 0)
        return list(ordered.values())

    async def _author_name(
        self, actor: User, author_id: int | None, known: dict[int, str | None]
    ) -> str | None:
        """The display name a variation travels with: the exporter's own, or
        the author's when the author shows it to other instances. Never the
        full name behind a nickname or the e-mail address."""
        if author_id is None:
            return None
        if author_id == actor.id:
            return actor.display_name
        if author_id not in known:
            author = await self._users.get(author_id)
            shown = author is not None and author.show_name_on_paired_instances
            known[author_id] = author.display_name if author is not None and shown else None
        return known[author_id]

    async def _variations_of(
        self, actor: User, viewer: Viewer, recipe: Recipe, known: dict[int, str | None]
    ) -> list[VariationV1]:
        """The variations the exporter may see: those as visible as the
        recipe, and the private ones only when the exporter wrote them."""
        return [
            variation_entry(v, await self._author_name(actor, v.author_id, known))
            for v in await self._variations.for_recipe(recipe.id)
            if can_view_variation(viewer, recipe, v)
        ]

    async def export(self, actor: User, recipe_ids: list[str] | None = None) -> bytes:
        """The recipes (all the actor may see, or the chosen ones) with
        their sub-recipes, variations, catalogue entries and images, as a
        zip archive. An administrator's bulk export. Mirrors of recipes from
        paired instances are left out, since they are never passed on."""
        self._assert_admin(actor)
        viewer = await self._viewers.of(actor)
        chosen = [r for r in await self._selection(viewer, recipe_ids) if not r.is_mirror]
        return await self._archive(actor, viewer, chosen)

    async def export_recipe(self, actor: User, public_id: str) -> ExportedFile:
        """One recipe as a `.cui` file, for anyone who can open it: reading
        is a session and the recipe's visibility, and so is exporting. A
        recipe the actor may not see answers 404 like an unknown one."""
        viewer = await self._viewers.of(actor)
        recipe = await self._recipes.get_by_public_id(public_id)
        if recipe is None or not can_view_recipe(viewer, recipe):
            raise RecipeNotFoundError("No such recipe.")
        if recipe.is_mirror:
            # A mirror is never passed on: its home instance decides who gets it.
            raise MirrorReadOnlyError(
                "This recipe comes from another instance and cannot be exported here; copy it "
                "as your own recipe to keep it."
            )
        return ExportedFile(data=await self._archive(actor, viewer, [recipe]), title=_title(recipe))

    async def _archive(self, actor: User, viewer: Viewer, chosen: list[Recipe]) -> bytes:
        recipes = await self._with_sub_recipes(viewer, chosen)
        if len(recipes) > MAX_RECIPES:
            raise RecipeArchiveError(f"An archive holds at most {MAX_RECIPES} recipes.")
        exported = {str(r.public_id) for r in recipes}
        entries: list[RecipeEntryV1] = []
        used = UsedRecords()
        authors: dict[int, str | None] = {}
        for recipe in recipes:
            content = recipe_content(recipe, await self._revisions.refs(recipe))
            # A sub-recipe left out keeps no title in the archive.
            content = replace(
                content,
                names=replace(
                    content.names,
                    recipes={k: v for k, v in content.names.recipes.items() if k in exported},
                ),
            )
            variations = await self._variations_of(actor, viewer, recipe, authors)
            collect_used(used, content, variations)
            entries.append(
                RecipeEntryV1(
                    id=str(recipe.public_id),
                    title=_title(recipe),
                    status=recipe.status.value,
                    snapshot=content,
                    variations=variations,
                )
            )
        catalogue = await self._catalogue(used)
        buffer = io.BytesIO()
        files: dict[str, FileEntryV1] = {}
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for public_id in sorted(used.files):
                stored = await self._files.get_by_public_id(public_id)
                data = await self._files.read_content(stored) if stored is not None else None
                if stored is None or data is None:
                    continue
                path = f"files/{public_id}"
                archive.writestr(path, data)
                files[public_id] = FileEntryV1(
                    path=path, name=stored.file_name, content_type=stored.content_type
                )
            document = RecipesDocumentV1(
                format=FORMAT,
                version=VERSION,
                exported_at=now_utc().isoformat(),
                instance_id=str(await self._settings.instance_id()),
                recipes=entries,
                catalogue=catalogue,
                files=files,
            )
            archive.writestr(MANIFEST, json.dumps(to_json(document), ensure_ascii=False, indent=2))
        return buffer.getvalue()

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

    # ── Import ───────────────────────────────────────────────────────

    @staticmethod
    def _open(data: bytes) -> tuple[zipfile.ZipFile, RecipesDocumentV1]:
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise RecipeArchiveError("This is not a recipe archive (no zip file).") from exc
        members = archive.infolist()
        if len(members) > MAX_ENTRIES or sum(m.file_size for m in members) > MAX_UNPACKED_BYTES:
            raise RecipeArchiveError("The archive is too large.")
        try:
            raw = json.loads(archive.read(MANIFEST))
        except (KeyError, ValueError) as exc:
            raise RecipeArchiveError(f"The archive has no readable {MANIFEST}.") from exc
        recipes = raw.get("recipes") if isinstance(raw, dict) else None
        if isinstance(recipes, list) and len(recipes) > MAX_RECIPES:
            raise RecipeArchiveError(f"An archive holds at most {MAX_RECIPES} recipes.")
        try:
            document = RECIPES.read(raw)
        except FormatError as exc:
            raise RecipeArchiveError(str(exc)) from exc
        return archive, document

    @staticmethod
    def _assert_importer(actor: User) -> None:
        if not actor.has_permission(Permission.WRITE_RECIPES):
            raise PermissionDeniedError("Importing recipes needs write:recipes.")

    @staticmethod
    def _origin(document: RecipesDocumentV1, entry: RecipeEntryV1) -> tuple[UUID, UUID] | None:
        """Where the entry came from, when the document names its instance
        (files of the first release do not)."""
        instance_id, public_id = parse_uuid(document.instance_id), parse_uuid(entry.id)
        if instance_id is None or public_id is None:
            return None
        return instance_id, public_id

    async def _earlier_import(self, actor: User, origin: tuple[UUID, UUID] | None) -> Recipe | None:
        """The actor's own recipe from an earlier import of the same source
        recipe, while they may still edit it."""
        if origin is None or not actor.id:
            return None
        found = await self._recipes.by_origin(actor.id, *origin)
        if found is None or not await self._manage_recipes.can_edit(actor, found):
            return None
        return found

    async def preview(self, actor: User, data: bytes) -> ImportPreview:
        """The recipes of the file and, for each, the importer's earlier
        import of it, so they can choose to update it or import a new copy.
        Reads the file with the same checks as the import and stores nothing."""
        self._assert_importer(actor)
        _, document = self._open(data)
        recipes = []
        for entry in document.recipes:
            earlier = await self._earlier_import(actor, self._origin(document, entry))
            recipes.append(
                PreviewedRecipe(
                    source_id=entry.id,
                    title=entry.title,
                    earlier=EarlierImport(
                        id=str(earlier.public_id),
                        title=_title(earlier),
                        status=earlier.status.value,
                    )
                    if earlier is not None
                    else None,
                )
            )
        return ImportPreview(recipes=recipes, source_instance_id=document.instance_id)

    async def import_archive(
        self, actor: User, data: bytes, update: set[str] | None = None
    ) -> ImportReport:
        """Imports every recipe of the file as a draft of the actor's. A
        recipe whose source id is in `update` and that the actor imported
        before updates that earlier import instead; one they imported before
        but did not choose to update becomes a new copy without an origin."""
        self._assert_importer(actor)
        archive, document = self._open(data)
        catalogue = document.catalogue
        run = _ImportRun()
        matcher = self._matcher()
        units = await self._match_units(matcher, catalogue.units, run)
        tags = await self._match_tags(matcher, catalogue.tags, run)
        ingredients = await self._match_ingredients(
            actor, matcher, catalogue.ingredients, units, run
        )
        equipment = await self._match_equipment(matcher, catalogue.equipment, run)
        files = await self._store_files(actor, archive, document.files, run)
        ids = _Ids(
            ingredient=ingredients,
            equipment=equipment,
            unit=units,
            tag=tags,
            file=files,
            recipe={},
            catalogue=catalogue,
        )
        viewer = await self._viewers.of(actor)
        taken: set[tuple[UUID, UUID]] = set()
        for entry in document.recipes:
            origin = self._origin(document, entry)
            if origin in taken:
                # A file naming one source recipe twice: the first keeps it.
                origin = None
            if origin is not None:
                taken.add(origin)
            await self._import_recipe(
                actor, viewer, entry, ids, run, origin, entry.id in (update or set())
            )
        await self._uow.commit()
        return ImportReport(
            recipes=run.recipes,
            created_ingredients=run.created_ingredients,
            created_equipment=run.created_equipment,
            matched_ingredients=run.matched_ingredients,
            matched_equipment=run.matched_equipment,
            conflicts=run.conflicts,
            source_instance_id=document.instance_id,
        )

    def _matcher(self) -> CatalogueMatcher:
        return CatalogueMatcher(
            unit_repo=self._units,
            tag_repo=self._tags,
            category_repo=self._categories,
            family_repo=self._families,
            ingredient_repo=self._ingredients,
            equipment_repo=self._equipment,
        )

    async def _match_units(
        self, matcher: CatalogueMatcher, entries: dict[str, UnitEntryV1], run: "_ImportRun"
    ) -> dict[str, str]:
        found: dict[str, str] = {}
        for public_id, entry in entries.items():
            unit = await matcher.unit(entry)
            if unit is None:
                run.conflict(
                    "unit",
                    entry.code or first_name(entry.names),
                    "No unit with this code here; amounts in it lose their unit.",
                )
                continue
            found[public_id] = str(unit.public_id)
        return found

    async def _match_tags(
        self, matcher: CatalogueMatcher, entries: dict[str, TagEntryV1], run: "_ImportRun"
    ) -> dict[str, str]:
        found: dict[str, str] = {}
        for public_id, entry in entries.items():
            tag = await matcher.tag(entry)
            if tag is None:
                run.conflict("tag", first_name(entry.names), "No such tag here; recipes lose it.")
                continue
            found[public_id] = str(tag.public_id)
        return found

    async def _match_ingredients(
        self,
        actor: User,
        matcher: CatalogueMatcher,
        entries: dict[str, IngredientEntryV1],
        units: dict[str, str],
        run: "_ImportRun",
    ) -> dict[str, str]:
        await matcher.prime(ingredient_keys=[e.seed_key for e in entries.values() if e.seed_key])
        found: dict[str, str] = {}
        for public_id, entry in entries.items():
            match = await matcher.ingredient(entry)
            if match is not None:
                found[public_id] = str(match.public_id)
                run.matched_ingredients += 1
                continue
            created = await self._create_ingredient(actor, matcher, entry, units, run)
            if created is not None:
                found[public_id] = str(created.public_id)
        return found

    async def _create_ingredient(
        self,
        actor: User,
        matcher: CatalogueMatcher,
        entry: IngredientEntryV1,
        units: dict[str, str],
        run: "_ImportRun",
    ) -> Ingredient | None:
        texts = {
            k: IngredientText(name=v.name, plural_name=v.plural_name)
            for k, v in entry.names.items()
            if v.name
        }
        name = first_name({k: v.name for k, v in texts.items()}, entry.original_locale)
        original = entry.original_locale
        if original not in texts:
            original = next(iter(sorted(texts)), None)
        if original is None:
            run.conflict("ingredient", "?", "An ingredient without a name was skipped.")
            return None
        allergens = [Allergen(a) for a in entry.allergens if a in Allergen]
        markers = [DietMarker(m) for m in entry.diet_markers if m in DietMarker]
        unknown = [a for a in entry.allergens if a not in Allergen]
        unknown += [m for m in entry.diet_markers if m not in DietMarker]
        if unknown:
            run.conflict(
                "ingredient",
                name,
                f"Unknown allergens or diet markers left out: {', '.join(unknown)}.",
            )
        n = entry.nutrition
        category = (
            await matcher.category(entry.category.seed_key, entry.category.names)
            if entry.category is not None
            else None
        )
        command = IngredientCommand(
            original_locale=original,
            translations=texts,
            category_id=str(category.public_id) if category is not None else None,
            aliases={k: list(v) for k, v in entry.aliases.items()},
            nutrition=Nutrition(
                kcal=n.kcal,
                protein=n.protein,
                fat=n.fat,
                saturated_fat=n.saturated_fat,
                carbohydrates=n.carbohydrates,
                sugar=n.sugar,
                fibre=n.fibre,
                salt=n.salt,
            ),
            extended_nutrition=dict(entry.extended_nutrition),
            season_months=list(entry.season_months),
            density_g_per_ml=entry.density_g_per_ml,
            conversions=[
                ConversionCommand(unit_id=units[c.unit_id], grams=c.grams)
                for c in entry.conversions
                if c.unit_id in units
            ],
            allergens=allergens,
            diet_markers=markers,
        )
        for attempt in (command, replace(command, aliases={})):
            try:
                created = await self._manage_ingredients.create(
                    actor, attempt, status=IngredientStatus.DRAFT, commit=False
                )
            except DuplicateNameError:
                continue
            run.created_ingredients.append(name)
            return created
        run.conflict(
            "ingredient",
            name,
            "Its name is taken by another catalogue entry here; recipe lines with it are left out.",
        )
        return None

    async def _match_equipment(
        self, matcher: CatalogueMatcher, entries: dict[str, EquipmentEntryV1], run: "_ImportRun"
    ) -> dict[str, str]:
        await matcher.prime(equipment_keys=[e.seed_key for e in entries.values() if e.seed_key])
        found: dict[str, str] = {}
        for public_id, entry in entries.items():
            names = entry.names
            match = await matcher.equipment(entry)
            if match is not None:
                found[public_id] = str(match.public_id)
                run.matched_equipment += 1
                continue
            locale = next((loc for loc in ("en-GB", "de-AT") if names.get(loc)), None)
            if locale is None:
                run.conflict("equipment", "?", "An equipment item without a name was skipped.")
                continue
            try:
                kind = EquipmentKind(entry.kind or EquipmentKind.UTENSIL.value)
            except ValueError:
                kind = EquipmentKind.UTENSIL
            try:
                created = await self._manage_equipment.create_draft(
                    names[locale], locale, kind=kind
                )
            except DuplicateNameError:
                run.conflict(
                    "equipment",
                    names[locale],
                    "Its name is taken by another catalogue entry here; steps lose it.",
                )
                continue
            found[public_id] = str(created.public_id)
            run.created_equipment.append(names[locale])
        return found

    async def _store_files(
        self,
        actor: User,
        archive: zipfile.ZipFile,
        entries: dict[str, FileEntryV1],
        run: "_ImportRun",
    ) -> dict[str, str]:
        """Every image of the archive, stored as an upload would store it."""
        found: dict[str, str] = {}
        for public_id, entry in entries.items():
            name = entry.name or public_id
            try:
                info = archive.getinfo(entry.path)
                if info.file_size > MAX_IMAGE_BYTES:
                    raise FileTypeNotAcceptedError("too large")
                processed = await self._images.process(archive.read(info))
            except (KeyError, FileTypeNotAcceptedError):
                run.conflict("image", name, "The image is missing or unreadable; left out.")
                continue
            stored = await self._files.add(
                StoredFile(
                    file_name=f"{name.rsplit('.', 1)[0] or 'image'}.webp",
                    content_type="image/webp",
                    size=len(processed.data),
                    content_hash=hashlib.sha256(processed.data).hexdigest(),
                    created=now_utc(),
                    creator_id=actor.id or None,
                    width=processed.width,
                    height=processed.height,
                    thumbnail_size=len(processed.thumbnail),
                    thumbnail_hash=hashlib.sha256(processed.thumbnail).hexdigest(),
                ),
                processed.data,
                processed.thumbnail,
            )
            found[public_id] = str(stored.public_id)
        return found

    async def _title_taken(self, viewer: Viewer, title: str) -> bool:
        found, _ = await self._recipes.find(
            RecipeQuery(
                viewer_id=viewer.id,
                viewer_group_ids=sorted(viewer.group_ids),
                viewer_household_member_ids=sorted(viewer.household_member_ids),
                search=title,
                limit=50,
            )
        )
        wanted = title.casefold()
        return any(t.title.casefold() == wanted for r in found for t in r.translations.values())

    async def _import_recipe(
        self,
        actor: User,
        viewer: Viewer,
        entry: RecipeEntryV1,
        ids: "_Ids",
        run: "_ImportRun",
        origin: tuple[UUID, UUID] | None,
        update: bool,
    ) -> None:
        """Creates the draft, or updates the earlier import when the importer
        chose so. A recipe imported before but not chosen for an update
        becomes a new copy that carries no origin."""
        title = entry.title
        command = _command(entry.snapshot, ids, title, run)
        earlier = await self._earlier_import(actor, origin)
        if earlier is not None and update:
            was_published = earlier.status is RecipeStatus.PUBLISHED
            saved = await self._manage_recipes.update(
                actor,
                str(earlier.public_id),
                replace(command, revision_note="Updated from import"),
                from_source=True,
                commit=False,
            )
            if was_published and saved.status is not RecipeStatus.PUBLISHED:
                run.conflict(
                    "status",
                    title,
                    "The update has no steps, so the recipe may not stay published; "
                    "it is a draft again.",
                    title,
                )
        else:
            if await self._title_taken(viewer, title):
                run.conflict(
                    "title", title, "A recipe with this title exists here; imported anyway.", title
                )
            saved = await self._manage_recipes.create(
                actor,
                replace(command, revision_note="Imported"),
                commit=False,
                from_source=True,
                origin=origin if earlier is None else None,
            )
        ids.recipe[entry.id] = str(saved.public_id)
        run.recipes.append(
            ImportedRecipe(
                source_id=entry.id,
                id=str(saved.public_id),
                title=title,
                updated=earlier is not None and update,
            )
        )
        for variation in entry.variations:
            await self._import_variation(actor, saved, variation, entry.snapshot, ids, title, run)

    async def _import_variation(
        self,
        actor: User,
        recipe: Recipe,
        variation: VariationV1,
        content: RecipeContentV1,
        ids: "_Ids",
        title: str,
        run: "_ImportRun",
    ) -> None:
        """Attaches the variation to the recipe as the importer's own, under
        a public id derived from its source id, so updating an earlier import
        replaces the variation that import brought instead of adding it
        twice. Changes naming a record without a match here, or no longer
        fitting the recipe, are left out and reported."""
        locale = variation.locale if variation.locale in LOCALES else recipe.original_locale
        mapped = [
            (change, command)
            for change in variation.changes
            if (command := _variation_change(change, ids, content.names, title, variation, run))
        ]
        kept, dropped = await self._manage_variations.fitting_changes(
            recipe, [command for _, command in mapped], locale
        )
        for change, command in mapped:
            if command not in dropped:
                continue
            named = change.ingredient_id or change.sub_recipe_id
            if named is None:
                run.conflict(
                    "variation",
                    variation.name,
                    f"A change of kind {change.kind!r} does not fit the imported recipe; left out.",
                    title,
                )
                continue
            kind = "ingredient" if change.ingredient_id else "sub_recipe"
            run.conflict(
                kind,
                ids.name(content.names, kind, named),
                f"A change of the variation {variation.name!r} does not fit the imported "
                "recipe; left out.",
                title,
            )
        origin = f"Originally by {variation.author_name or 'another cook'}."
        room = MAX_NOTE - len(origin) - 2
        note = f"{variation.note.strip()[:room]}\n\n{origin}" if variation.note.strip() else origin
        cmd = VariationCommand(
            name=(variation.name.strip() or "Variation")[:MAX_NAME],
            locale=locale,
            note=note,
            private=variation.private,
            changes=kept,
        )
        source_id = parse_uuid(variation.id)
        if source_id is None:
            await self._manage_variations.add(actor, recipe, cmd, commit=False)
            return
        saved = await self._manage_variations.save_imported(
            actor, recipe, uuid5(recipe.public_id, f"variation:{source_id}"), cmd
        )
        if saved is None:
            run.conflict(
                "variation",
                variation.name,
                "The variation an earlier import brought belongs to someone else now; "
                "kept as it is.",
                title,
            )


class _ImportRun:
    """What one import found, created and could not place."""

    def __init__(self) -> None:
        self.recipes: list[ImportedRecipe] = []
        self.created_ingredients: list[str] = []
        self.created_equipment: list[str] = []
        self.matched_ingredients = 0
        self.matched_equipment = 0
        self.conflicts: list[ImportConflict] = []

    def conflict(self, kind: str, name: str, detail: str, recipe: str | None = None) -> None:
        self.conflicts.append(ImportConflict(kind=kind, name=name, detail=detail, recipe=recipe))


@dataclass
class _Ids:
    """The archive's ids mapped to this instance's, per kind."""

    ingredient: dict[str, str]
    equipment: dict[str, str]
    unit: dict[str, str]
    tag: dict[str, str]
    file: dict[str, str]
    recipe: dict[str, str]
    catalogue: CatalogueSectionV1

    def name(self, names: ReferenceNamesV1, kind: str, public_id: str) -> str:
        """The name the archive records for a record it names."""
        recorded: dict[str, str] = {}
        match kind:
            case "ingredient":
                recorded = names.ingredients.get(public_id) or {}
                entry = self.catalogue.ingredients.get(public_id)
                if not recorded and entry is not None:
                    recorded = {k: v.name for k, v in entry.names.items()}
            case "sub_recipe":
                recorded = names.recipes.get(public_id) or {}
        return first_name(recorded) or (
            "a recipe that was not exported" if kind == "sub_recipe" else public_id
        )

    def mentions(self) -> dict[str, str]:
        found: dict[str, str] = {}
        for mapping in (self.ingredient, self.recipe, self.equipment):
            found |= {old.lower(): new for old, new in mapping.items()}
        return found

    def rewrite(self, text: str) -> str:
        """Mentions pointed at this instance's records, or plain text."""
        targets = self.mentions()

        def one(match: Any) -> str:
            new = targets.get(match.group(3).lower())
            return f"@[{match.group(1)}]({match.group(2)}:{new})" if new else match.group(1)

        return str(MENTION.sub(one, text))


def _difficulty(value: str) -> Difficulty:
    try:
        return Difficulty(value)
    except ValueError:
        return Difficulty.EASY


def _command(content: RecipeContentV1, ids: _Ids, title: str, run: _ImportRun) -> RecipeCommand:
    """The recipe content with the archive's ids replaced by this
    instance's, as a save command naming the source step and line ids, which
    the save turns into ids of this recipe (`step_ids`). Lines whose
    ingredient or sub-recipe found no match are dropped, and mentions of
    anything without a match become plain text."""

    def placed(line: IngredientLineV1) -> StepIngredientCommand | None:
        notes = {k: NoteText(v.note) for k, v in line.notes.items()}
        unit = ids.unit.get(line.unit_id) if line.unit_id else None
        if line.sub_recipe_id:
            target = ids.recipe.get(line.sub_recipe_id)
            if target is None:
                run.conflict(
                    "sub_recipe",
                    ids.name(content.names, "sub_recipe", line.sub_recipe_id),
                    "The sub-recipe is not in the archive; its line is left out.",
                    title,
                )
                return None
            return StepIngredientCommand(
                id=line.id, sub_recipe_id=target, amount=line.amount, unit_id=unit, notes=notes
            )
        target = ids.ingredient.get(line.ingredient_id) if line.ingredient_id else None
        if target is None:
            run.conflict(
                "ingredient",
                ids.name(content.names, "ingredient", str(line.ingredient_id)),
                "No ingredient matched; its line is left out.",
                title,
            )
            return None
        return StepIngredientCommand(
            id=line.id, ingredient_id=target, amount=line.amount, unit_id=unit, notes=notes
        )

    steps: list[StepCommand] = []
    for step in content.steps:
        lines = [found for line in step.ingredients if (found := placed(line)) is not None]
        equipment = [
            StepEquipmentCommand(
                id=item.id,
                equipment_id=ids.equipment[item.equipment_id],
                count=item.count,
                notes={k: NoteText(v.note) for k, v in item.notes.items()},
            )
            for item in step.equipment
            if item.equipment_id and item.equipment_id in ids.equipment
        ]
        steps.append(
            StepCommand(
                id=step.id,
                translations={
                    k: StepText(ids.rewrite(v.text)) for k, v in step.translations.items()
                },
                duration_minutes=step.duration_minutes,
                image_file_id=ids.file.get(step.image_id) if step.image_id else None,
                ingredients=lines,
                equipment=equipment,
            )
        )
    yield_unit = ids.unit.get(content.yield_unit_id) if content.yield_unit_id else None
    return RecipeCommand(
        original_locale=content.original_locale,
        translations={
            k: RecipeText(v.title, v.description, v.tips) for k, v in content.translations.items()
        },
        base_servings=content.base_servings,
        prep_minutes=content.prep_minutes,
        cook_minutes=content.cook_minutes,
        rest_minutes=content.rest_minutes,
        difficulty=_difficulty(content.difficulty),
        cover_file_id=ids.file.get(content.cover_image_id) if content.cover_image_id else None,
        source_url=content.source_url,
        source_name=content.source_name,
        tag_ids=[ids.tag[t] for t in content.tag_ids if t in ids.tag],
        steps=steps,
        ingredients=[found for line in content.ingredients if (found := placed(line)) is not None],
        yield_amount=content.yield_amount if yield_unit else None,
        yield_unit_id=yield_unit,
    )


def _variation_change(
    change: VariationChangeV1,
    ids: _Ids,
    names: ReferenceNamesV1,
    title: str,
    variation: VariationV1,
    run: _ImportRun,
) -> VariationChangeCommand | None:
    """The change with this instance's ids, or None when it names an
    ingredient or sub-recipe without a match here (reported). As for recipes,
    a unit without a match leaves the amount without a unit, and an
    equipment item without a match is left out of an added step."""
    try:
        kind = VariationChangeKind(change.kind)
    except ValueError:
        run.conflict(
            "variation",
            variation.name,
            f"A change of the unknown kind {change.kind!r} is left out.",
            title,
        )
        return None
    left_out = f"No match here; a change of the variation {variation.name!r} is left out."

    def ingredient(public_id: str | None) -> str | None:
        if public_id is None:
            return None
        found = ids.ingredient.get(public_id)
        if found is None:
            run.conflict("ingredient", ids.name(names, "ingredient", public_id), left_out, title)
            raise LookupError(public_id)
        return found

    try:
        ingredient_id = ingredient(change.ingredient_id)
        to_ingredient_id = ingredient(change.to_ingredient_id)
        sub_recipe_id = None
        if change.sub_recipe_id:
            sub_recipe_id = ids.recipe.get(change.sub_recipe_id)
            if sub_recipe_id is None:
                run.conflict(
                    "sub_recipe",
                    ids.name(names, "sub_recipe", change.sub_recipe_id),
                    left_out,
                    title,
                )
                return None
        lines = [
            VariationLineCommand(
                ingredient_id=str(ingredient(line.ingredient_id)),
                amount=line.amount,
                unit_id=ids.unit.get(line.unit_id) if line.unit_id else None,
                note=line.note,
            )
            for line in change.lines
        ]
    except LookupError:
        return None
    return VariationChangeCommand(
        kind=kind,
        id=change.id or None,
        step=change.step,
        ingredient_id=ingredient_id,
        sub_recipe_id=sub_recipe_id,
        to_ingredient_id=to_ingredient_id,
        amount=change.amount,
        unit_id=ids.unit.get(change.unit_id) if change.unit_id else None,
        keep_amount=change.keep_amount,
        note=change.note,
        text=ids.rewrite(change.text),
        duration_minutes=change.duration_minutes,
        lines=lines,
        equipment=[
            VariationEquipmentCommand(
                equipment_id=ids.equipment[item.equipment_id],
                count=item.count,
                note=item.note,
            )
            for item in change.equipment
            if item.equipment_id in ids.equipment
        ],
    )
