"""
The catalogue file: the whole catalogue (units, tags, ingredient categories
and families, ingredients and equipment) as one `cuisine-catalogue` JSON
document, exported by an administrator and imported into another instance in
two steps.

Exporting needs manage:ingredients or write:resources and writes every unit,
tag, category and family and every active ingredient and equipment item,
since every signed-in user may read the catalogue anyway.

Importing first answers a preview and writes nothing: each entry of the file
is matched to this instance's catalogue (`CatalogueMatcher`, the matching of
the recipe import) or is new, and a matched entry lists the fields whose
values differ, with the value here and the value in the file. Allergens and
diet markers come first, since they drive the allergy and diet warnings. The
apply step then creates every new entry, active, because the administrator
imports a catalogue on purpose, and writes only the differences the
administrator accepted, field by field; nothing else of a matched entry
changes. References inside the file are kept: an ingredient's category and
family and its conversions' units point at the entries of the same file,
matched or created. Every write goes through the checks of a normal edit,
so a name another catalogue entry holds is reported and not written. All of
it happens in one transaction.

Ingredients need manage:ingredients and write:ingredients; units, tags,
categories, families and equipment need write:resources. A caller who holds
only one of the two sets gets the other kinds reported as skipped, and a
caller who holds neither is refused.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import Any
from typing import Final

from src.cookbook.application.services.catalogue_fields import CatalogueLookups
from src.cookbook.application.services.catalogue_fields import CatalogueWriter
from src.cookbook.application.services.catalogue_fields import FieldDifference
from src.cookbook.application.services.catalogue_fields import Fields
from src.cookbook.application.services.catalogue_fields import Local
from src.cookbook.application.services.catalogue_fields import Ref
from src.cookbook.application.services.catalogue_fields import current_fields
from src.cookbook.application.services.catalogue_fields import equipment_fields
from src.cookbook.application.services.catalogue_fields import find_differences
from src.cookbook.application.services.catalogue_fields import first_name
from src.cookbook.application.services.catalogue_fields import in_locales
from src.cookbook.application.services.catalogue_fields import ingredient_fields
from src.cookbook.application.services.catalogue_fields import is_safety
from src.cookbook.application.services.catalogue_fields import local_ref
from src.cookbook.application.services.catalogue_fields import named_fields
from src.cookbook.application.services.catalogue_fields import plain
from src.cookbook.application.services.catalogue_fields import resolve_local
from src.cookbook.application.services.catalogue_fields import row_names
from src.cookbook.application.services.catalogue_fields import sorted_conversions
from src.cookbook.application.services.catalogue_fields import tag_fields
from src.cookbook.application.services.catalogue_fields import unit_fields
from src.cookbook.application.services.catalogue_matching import CatalogueMatcher
from src.cookbook.application.services.formats.catalogue_mapper import catalogue_document
from src.cookbook.application.services.formats.catalogue_v1 import CatalogueDocumentV1
from src.cookbook.application.services.formats.catalogue_v1 import EquipmentEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import IngredientEntryV1
from src.cookbook.application.services.formats.catalogue_v1 import NamedRefV1
from src.cookbook.application.services.formats.catalogue_v1 import UnitEntryV1
from src.cookbook.application.services.formats.codec import FormatError
from src.cookbook.application.services.formats.codec import to_json
from src.cookbook.application.services.formats.specs import CATALOGUE
from src.cookbook.application.use_cases.equipment.manage_equipment import EquipmentCommand
from src.cookbook.application.use_cases.equipment.manage_equipment import ManageEquipment
from src.cookbook.application.use_cases.ingredients.manage_ingredients import IngredientCommand
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ManageIngredients
from src.cookbook.application.use_cases.resources.manage_resources import CategoryCommand
from src.cookbook.application.use_cases.resources.manage_resources import ManageResources
from src.cookbook.application.use_cases.resources.manage_resources import TagCommand
from src.cookbook.application.use_cases.resources.manage_resources import UnitCommand
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.resources import IngredientCategory
from src.cookbook.domain.entities.resources import IngredientFamily
from src.cookbook.domain.entities.resources import Unit
from src.cookbook.domain.exceptions import CatalogueFileError
from src.cookbook.domain.exceptions import DuplicateNameError
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import DietMarker
from src.cookbook.domain.value_objects.enums import EquipmentKind
from src.cookbook.domain.value_objects.enums import EquipmentStatus
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.domain.value_objects.enums import UnitKind
from src.cookbook.domain.value_objects.nutrients import EXTENDED_KEYS
from src.cookbook.domain.value_objects.nutrition import NUTRIENTS
from src.cookbook.domain.value_objects.nutrition import Nutrition
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.domain.value_objects.texts import NameText
from src.cookbook.domain.value_objects.texts import UnitText
from src.cookbook.ports.outbound.repositories.equipment_repository import EquipmentQuery
from src.cookbook.ports.outbound.repositories.equipment_repository import IEquipmentRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.ingredient_repository import IngredientQuery
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientCategoryRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import IUnitRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import NotFoundError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.value_objects.permission import Permission
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# The largest file an import reads, and the most entries it holds in all.
MAX_FILE_BYTES: Final = 32 * 1024 * 1024
MAX_ENTRIES: Final = 50_000

# The kinds in the order an import writes them: whatever an ingredient
# refers to comes before the ingredients.
KINDS: Final = ("category", "family", "unit", "tag", "ingredient", "equipment")
RESOURCE_KINDS: Final = frozenset({"category", "family", "unit", "tag", "equipment"})


@dataclass(frozen=True)
class PreviewEntry:
    kind: str
    # The entry's public id in the file.
    source_id: str
    name: str
    # The public id of the matched entry here; None for a new entry.
    local_id: str | None
    differences: list[FieldDifference]


@dataclass(frozen=True)
class KindSummary:
    kind: str
    total: int
    new: int
    matched: int
    # Matched entries with at least one differing field.
    different: int
    # True when the caller may not write this kind.
    skipped: bool


@dataclass(frozen=True)
class CatalogueConflict:
    kind: str
    name: str
    detail: str


@dataclass(frozen=True)
class CataloguePreview:
    source_instance_id: str | None
    exported_at: str
    kinds: list[KindSummary]
    # Every new entry and every matched entry with differences, entries
    # with allergen or diet marker differences first.
    entries: list[PreviewEntry]
    conflicts: list[CatalogueConflict]


@dataclass(frozen=True)
class AcceptedField:
    kind: str
    source_id: str
    field: str


@dataclass(frozen=True)
class CreatedEntry:
    kind: str
    source_id: str
    name: str
    id: str


@dataclass(frozen=True)
class UpdatedEntry:
    kind: str
    source_id: str
    name: str
    id: str
    fields: list[str]


@dataclass(frozen=True)
class CatalogueImportReport:
    created: list[CreatedEntry]
    updated: list[UpdatedEntry]
    skipped: list[str]
    conflicts: list[CatalogueConflict]


def _has_safety(entry: PreviewEntry) -> bool:
    return any(is_safety(d.field) for d in entry.differences)


@dataclass
class _Run:
    """One preview or import: the file, its matches, the local lookups and
    what was found, created and could not be placed."""

    actor: User
    document: CatalogueDocumentV1
    matcher: CatalogueMatcher
    allowed: set[str]
    locale: str
    # Per kind, the source id of each entry and its match here or None.
    matches: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Per kind, the public id here of each entry of the file once known.
    resolved: dict[str, dict[str, str]] = field(default_factory=dict)
    categories: dict[int, IngredientCategory] = field(default_factory=dict)
    families: dict[int, IngredientFamily] = field(default_factory=dict)
    units: dict[int, Unit] = field(default_factory=dict)
    conflicts: list[CatalogueConflict] = field(default_factory=list)
    created: list[CreatedEntry] = field(default_factory=list)
    updated: list[UpdatedEntry] = field(default_factory=list)

    @property
    def lookups(self) -> CatalogueLookups:
        return CatalogueLookups(self.categories, self.families, self.units)

    def conflict(self, kind: str, name: str, detail: str) -> None:
        self.conflicts.append(CatalogueConflict(kind=kind, name=name, detail=detail))

    def entries(self, kind: str) -> Mapping[str, Any]:
        sections: dict[str, Mapping[str, Any]] = {
            "category": self.document.categories,
            "family": self.document.families,
            "unit": self.document.units,
            "tag": self.document.tags,
            "ingredient": self.document.ingredients,
            "equipment": self.document.equipment,
        }
        return sections[kind]

    def name(self, kind: str, entry: Any, local: Any = None) -> str:
        """The entry's name in the actor's language: the matched entry's
        name here when there is one, else the file's."""
        if local is not None:
            return first_name(row_names(local), self.locale) or "?"
        if kind == "ingredient":
            return first_name({k: v.name for k, v in entry.names.items()}, self.locale) or "?"
        if kind == "unit":
            return first_name(entry.names, self.locale) or entry.code or "?"
        return first_name(entry.names, self.locale) or "?"


class CatalogueFile:
    def __init__(
        self,
        *,
        unit_repo: IUnitRepository,
        tag_repo: ITagRepository,
        category_repo: IIngredientCategoryRepository,
        family_repo: IIngredientFamilyRepository,
        ingredient_repo: IIngredientRepository,
        equipment_repo: IEquipmentRepository,
        settings_repo: ISettingsRepository,
        resources: ManageResources,
        ingredients: ManageIngredients,
        equipment: ManageEquipment,
        uow: IUnitOfWork,
    ) -> None:
        self._units = unit_repo
        self._tags = tag_repo
        self._categories = category_repo
        self._families = family_repo
        self._ingredients = ingredient_repo
        self._equipment = equipment_repo
        self._settings = settings_repo
        self._manage_resources = resources
        self._manage_ingredients = ingredients
        self._manage_equipment = equipment
        self._writer = CatalogueWriter(
            resources=resources, ingredients=ingredients, equipment=equipment
        )
        self._uow = uow

    # ── Permissions ──────────────────────────────────────────────────

    @staticmethod
    def allowed_kinds(actor: User) -> set[str]:
        """The kinds the actor may write: ingredients with manage:ingredients
        and write:ingredients, every other kind with write:resources."""
        kinds: set[str] = set()
        if actor.has_permission(Permission.WRITE_RESOURCES):
            kinds |= RESOURCE_KINDS
        if actor.has_permission(Permission.MANAGE_INGREDIENTS) and actor.has_permission(
            Permission.WRITE_INGREDIENTS
        ):
            kinds.add("ingredient")
        return kinds

    @staticmethod
    def _assert_exporter(actor: User) -> None:
        if not (
            actor.has_permission(Permission.MANAGE_INGREDIENTS)
            or actor.has_permission(Permission.WRITE_RESOURCES)
        ):
            raise PermissionDeniedError(
                "Exporting the catalogue needs manage:ingredients or write:resources."
            )

    def _assert_importer(self, actor: User) -> set[str]:
        allowed = self.allowed_kinds(actor)
        if not allowed:
            raise PermissionDeniedError(
                "Importing a catalogue needs write:resources, or manage:ingredients "
                "with write:ingredients."
            )
        return allowed

    # ── Export ───────────────────────────────────────────────────────

    async def export(self, actor: User) -> bytes:
        """The whole catalogue as a `cuisine-catalogue` JSON document: every
        unit, tag, category and family, and the active ingredients and
        equipment. Drafts wait for review and archived ingredients are gone
        from the catalogue, so neither travels."""
        self._assert_exporter(actor)
        document = catalogue_document(
            exported_at=now_utc().isoformat(),
            instance_id=str(await self._settings.instance_id()),
            units=await self._units.list_all(),
            tags=await self._tags.list_all(),
            categories=await self._categories.list_all(),
            families=await self._families.list_all(),
            ingredients=await self._ingredients.find(
                IngredientQuery(status=IngredientStatus.ACTIVE)
            ),
            equipment=await self._equipment.find(EquipmentQuery(status=EquipmentStatus.ACTIVE)),
        )
        return json.dumps(to_json(document), ensure_ascii=False, indent=2).encode()

    # ── Reading and matching ─────────────────────────────────────────

    @staticmethod
    def _read(data: bytes) -> CatalogueDocumentV1:
        if len(data) > MAX_FILE_BYTES:
            raise CatalogueFileError("The catalogue file is too large.")
        try:
            raw = json.loads(data)
        except (UnicodeDecodeError, ValueError) as exc:
            raise CatalogueFileError("This is not a catalogue file (no JSON).") from exc
        if isinstance(raw, dict):
            count = sum(
                len(raw[k])
                for k in ("units", "tags", "categories", "families", "ingredients", "equipment")
                if isinstance(raw.get(k), dict)
            )
            if count > MAX_ENTRIES:
                raise CatalogueFileError(f"A catalogue file holds at most {MAX_ENTRIES} entries.")
        try:
            return CATALOGUE.read(raw)
        except FormatError as exc:
            raise CatalogueFileError(str(exc)) from exc

    async def _start(self, actor: User, data: bytes) -> _Run:
        allowed = self._assert_importer(actor)
        document = self._read(data)
        matcher = CatalogueMatcher(
            unit_repo=self._units,
            tag_repo=self._tags,
            category_repo=self._categories,
            family_repo=self._families,
            ingredient_repo=self._ingredients,
            equipment_repo=self._equipment,
        )
        run = _Run(
            actor=actor,
            document=document,
            matcher=matcher,
            allowed=allowed,
            locale=ui_locale(actor.language.value),
            categories={c.id: c for c in await self._categories.list_all()},
            families={f.id: f for f in await self._families.list_all()},
            units={u.id: u for u in await self._units.list_all()},
        )
        await matcher.prime(
            ingredient_keys=[e.seed_key for e in document.ingredients.values() if e.seed_key],
            equipment_keys=[e.seed_key for e in document.equipment.values() if e.seed_key],
        )
        for kind in KINDS:
            matches: dict[str, Any] = {}
            seen: dict[int, str] = {}
            for source_id, entry in run.entries(kind).items():
                local = await self._match(run, kind, entry)
                if local is not None and local.id in seen:
                    run.conflict(
                        kind,
                        run.name(kind, entry),
                        f"It matches the same entry here as {seen[local.id]!r}; "
                        "accepted differences of both are written one after the other.",
                    )
                if local is not None:
                    seen.setdefault(local.id, run.name(kind, entry))
                matches[source_id] = local
            run.matches[kind] = matches
            run.resolved[kind] = {
                source_id: str(local.public_id)
                for source_id, local in matches.items()
                if local is not None
            }
        return run

    async def _match(self, run: _Run, kind: str, entry: Any) -> Local | None:
        match kind:
            case "category" | "family":
                finder = run.matcher.category if kind == "category" else run.matcher.family
                return await finder(entry.seed_key, entry.names)
            case "unit":
                return await run.matcher.unit(entry)
            case "tag":
                return await run.matcher.tag(entry)
            case "ingredient":
                return await run.matcher.ingredient(entry)
            case _:
                return await run.matcher.equipment(entry)

    async def _ref(self, run: _Run, kind: str, ref: NamedRefV1 | None) -> Ref | None:
        """The category or family an incoming ingredient names: the entry of
        the file its source id points at, matched or to be created, or else
        a record here with its seed key or one of its names."""
        if ref is None:
            return None
        section = run.entries(kind)
        if ref.id and ref.id in section:
            local = run.matches[kind].get(ref.id)
            if local is not None:
                return local_ref(local, run.locale)
            return Ref(f"new:{kind}:{ref.id}", first_name(section[ref.id].names, run.locale))
        finder = run.matcher.category if kind == "category" else run.matcher.family
        found = await finder(ref.seed_key, ref.names)
        return local_ref(found, run.locale) if found is not None else None

    def _incoming_conversions(
        self, run: _Run, entry: IngredientEntryV1
    ) -> tuple[tuple[Ref, float], ...]:
        found: list[tuple[Ref, float]] = []
        for conversion in entry.conversions:
            unit = run.document.units.get(conversion.unit_id)
            if unit is None:
                continue
            local = run.matches["unit"].get(conversion.unit_id)
            ref = (
                local_ref(local, run.locale)
                if local is not None
                else Ref(f"new:unit:{conversion.unit_id}", unit.code)
            )
            found.append((ref, float(conversion.grams)))
        return sorted_conversions(found)

    async def _incoming(self, run: _Run, kind: str, entry: Any) -> Fields:
        match kind:
            case "category" | "family":
                return named_fields(entry.names)
            case "unit":
                return unit_fields(entry)
            case "tag":
                return tag_fields(entry)
            case "ingredient":
                return ingredient_fields(
                    entry,
                    await self._ref(run, "category", entry.category),
                    await self._ref(run, "family", entry.family),
                    self._incoming_conversions(run, entry),
                )
            case _:
                return equipment_fields(entry)

    async def _differences(
        self, run: _Run, kind: str, entry: Any, local: Any
    ) -> tuple[Fields, list[FieldDifference]]:
        incoming = await self._incoming(run, kind, entry)
        current = current_fields(kind, local, run.lookups, run.locale)
        return incoming, find_differences(incoming, current)

    def _report_unknown(self, run: _Run, kind: str, entry: Any) -> None:
        """Values this instance does not know, which the import leaves out."""
        unknown: list[str] = []
        if kind == "ingredient":
            unknown += [a for a in entry.allergens if a not in Allergen]
            unknown += [m for m in entry.diet_markers if m not in DietMarker]
            unknown += [k for k in entry.extended_nutrition if k not in EXTENDED_KEYS]
        enums: dict[str, Any] = {"unit": UnitKind, "tag": TagKind, "equipment": EquipmentKind}
        if kind in enums and entry.kind is not None and entry.kind not in enums[kind]:
            unknown.append(entry.kind)
        if unknown:
            run.conflict(
                kind, run.name(kind, entry), f"Unknown values left out: {', '.join(unknown)}."
            )

    # ── Preview ──────────────────────────────────────────────────────

    async def preview(self, actor: User, data: bytes) -> CataloguePreview:
        """What an import of the file would do, without writing anything."""
        run = await self._start(actor, data)
        kinds: list[KindSummary] = []
        entries: list[PreviewEntry] = []
        for kind in KINDS:
            skipped = kind not in run.allowed
            new = matched = different = 0
            for source_id, entry in run.entries(kind).items():
                local = run.matches[kind][source_id]
                if local is None:
                    new += 1
                else:
                    matched += 1
                if skipped:
                    continue
                self._report_unknown(run, kind, entry)
                if local is None:
                    entries.append(PreviewEntry(kind, source_id, run.name(kind, entry), None, []))
                    continue
                _, found = await self._differences(run, kind, entry, local)
                if found:
                    different += 1
                    entries.append(
                        PreviewEntry(
                            kind,
                            source_id,
                            run.name(kind, entry, local),
                            str(local.public_id),
                            [
                                FieldDifference(d.field, plain(d.current), plain(d.incoming))
                                for d in found
                            ],
                        )
                    )
            kinds.append(
                KindSummary(
                    kind=kind,
                    total=new + matched,
                    new=new,
                    matched=matched,
                    different=different,
                    skipped=skipped,
                )
            )
        order = {kind: i for i, kind in enumerate(KINDS)}
        entries.sort(
            key=lambda e: (not _has_safety(e), e.local_id is None, order[e.kind], e.name.casefold())
        )
        return CataloguePreview(
            source_instance_id=run.document.instance_id,
            exported_at=run.document.exported_at,
            kinds=kinds,
            entries=entries,
            conflicts=run.conflicts,
        )

    # ── Apply ────────────────────────────────────────────────────────

    async def apply(
        self, actor: User, data: bytes, accepted: list[AcceptedField]
    ) -> CatalogueImportReport:
        """Creates every new entry of the kinds the actor may write and
        writes the accepted differences of matched entries, in one
        transaction. An accepted field that is no difference (any more) is
        ignored."""
        run = await self._start(actor, data)
        wanted: dict[tuple[str, str], set[str]] = {}
        for a in accepted:
            wanted.setdefault((a.kind, a.source_id), set()).add(a.field)
        for kind in KINDS:
            if kind not in run.allowed:
                continue
            for source_id, entry in run.entries(kind).items():
                self._report_unknown(run, kind, entry)
                local = run.matches[kind][source_id]
                if local is None:
                    await self._create(run, kind, source_id, entry)
                elif fields := wanted.get((kind, source_id)):
                    await self._update(run, kind, source_id, entry, local, fields)
        await self._uow.commit()
        return CatalogueImportReport(
            created=run.created,
            updated=run.updated,
            skipped=[k for k in KINDS if k not in run.allowed and run.entries(k)],
            conflicts=run.conflicts,
        )

    def _resolve(self, run: _Run, ref: Ref | None) -> str | None:
        """The public id here of a referenced record, once the entry of the
        file it may stand for was created."""
        if ref is None or ref.key.startswith("local:"):
            return resolve_local(ref)
        _, kind, source_id = ref.key.split(":", 2)
        return run.resolved.get(kind, {}).get(source_id)

    async def _create(self, run: _Run, kind: str, source_id: str, entry: Any) -> None:
        name = run.name(kind, entry)
        try:
            created = await self._create_entry(run, kind, entry)
        except DuplicateNameError as exc:
            run.conflict(kind, name, f"Not created, its name is taken here: {exc}")
            return
        except (InvalidInputError, NotFoundError, ValueError) as exc:
            run.conflict(kind, name, f"Not created: {exc}")
            return
        run.resolved[kind][source_id] = str(created.public_id)
        run.created.append(CreatedEntry(kind, source_id, name, str(created.public_id)))

    async def _create_entry(self, run: _Run, kind: str, entry: Any) -> Local:
        match kind:
            case "category":
                return await self._manage_resources.create_category(
                    CategoryCommand(
                        translations={k: NameText(v) for k, v in in_locales(entry.names).items()},
                        sort_order=entry.sort_order,
                    ),
                    commit=False,
                )
            case "family":
                return await self._manage_resources.create_family(
                    {k: NameText(v) for k, v in in_locales(entry.names).items()}, commit=False
                )
            case "unit":
                unit: UnitEntryV1 = entry
                return await self._manage_resources.create_unit(
                    UnitCommand(
                        code=unit.code,
                        kind=UnitKind(unit.kind or UnitKind.OTHER.value),
                        to_base=unit.to_base,
                        translations={
                            k: UnitText(
                                v, unit.plural_names.get(k) or v, unit.abbreviations.get(k) or ""
                            )
                            for k, v in in_locales(unit.names).items()
                        },
                    ),
                    commit=False,
                )
            case "tag":
                return await self._manage_resources.create_tag(
                    TagCommand(
                        kind=TagKind(entry.kind or TagKind.OTHER.value),
                        translations={k: NameText(v) for k, v in in_locales(entry.names).items()},
                        color=entry.color,
                    ),
                    commit=False,
                )
            case "ingredient":
                return await self._create_ingredient(run, entry)
            case _:
                item: EquipmentEntryV1 = entry
                return await self._manage_equipment.create(
                    run.actor,
                    EquipmentCommand(
                        kind=EquipmentKind(item.kind or EquipmentKind.UTENSIL.value),
                        translations={k: NameText(v) for k, v in in_locales(item.names).items()},
                        aliases=in_locales(item.aliases),
                        icon=item.icon,
                        basic=item.basic,
                    ),
                    commit=False,
                )

    async def _create_ingredient(self, run: _Run, entry: IngredientEntryV1) -> Ingredient:
        texts = {
            k: IngredientText(name=v.name, plural_name=v.plural_name or v.name)
            for k, v in in_locales(entry.names).items()
            if v.name
        }
        original = entry.original_locale
        if original not in texts:
            original = next(iter(sorted(texts)), None)
        if original is None:
            raise ValueError("The ingredient has no name.")
        n = entry.nutrition
        command = IngredientCommand(
            original_locale=original,
            translations=texts,
            category_id=self._resolve(run, await self._ref(run, "category", entry.category)),
            family_id=self._resolve(run, await self._ref(run, "family", entry.family)),
            aliases=in_locales(entry.aliases),
            nutrition=Nutrition(**{name: getattr(n, name) for name in NUTRIENTS}),
            extended_nutrition={
                k: v for k, v in entry.extended_nutrition.items() if k in EXTENDED_KEYS
            },
            season_months=list(entry.season_months),
            density_g_per_ml=entry.density_g_per_ml,
            conversions=CatalogueWriter.conversions(
                self._incoming_conversions(run, entry), lambda ref: self._resolve(run, ref)
            ),
            allergens=[Allergen(a) for a in entry.allergens if a in Allergen],
            diet_markers=[DietMarker(m) for m in entry.diet_markers if m in DietMarker],
        )
        try:
            return await self._manage_ingredients.create(
                run.actor, command, status=IngredientStatus.ACTIVE, commit=False
            )
        except DuplicateNameError:
            if not command.aliases:
                raise
        created = await self._manage_ingredients.create(
            run.actor,
            replace(command, aliases={}),
            status=IngredientStatus.ACTIVE,
            commit=False,
        )
        run.conflict(
            "ingredient",
            run.name("ingredient", entry),
            "Created without its other names, since one of them is taken here.",
        )
        return created

    async def _update(
        self, run: _Run, kind: str, source_id: str, entry: Any, local: Any, accepted: set[str]
    ) -> None:
        """Writes the accepted differences through the checks of a normal
        edit. When a name or alias is taken, the entry's other accepted
        fields are written without the names, and the names are reported."""
        name = run.name(kind, entry, local)
        incoming, found = await self._differences(run, kind, entry, local)
        fields = [d.field for d in found if d.field in accepted]
        if not fields:
            return
        without_names = [f for f in fields if not f.startswith(("names.", "aliases."))]
        for attempt in (fields, without_names):
            if not attempt:
                return
            try:
                await self._write(run, kind, local, {f: incoming[f] for f in attempt})
            except DuplicateNameError as exc:
                if attempt is without_names or without_names == fields:
                    run.conflict(kind, name, f"Not changed, a name is taken here: {exc}")
                    return
                run.conflict(kind, name, f"Names and other names left as they are: {exc}")
                continue
            except (InvalidInputError, NotFoundError, ValueError) as exc:
                run.conflict(kind, name, f"Not changed: {exc}")
                return
            run.updated.append(UpdatedEntry(kind, source_id, name, str(local.public_id), attempt))
            return

    async def _write(self, run: _Run, kind: str, local: Any, values: Fields) -> None:
        await self._writer.write(
            run.actor, kind, local, values, run.lookups, lambda ref: self._resolve(run, ref)
        )
