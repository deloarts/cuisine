from typing import Any
from typing import Literal

from src.platform.adapters.inbound.api.schemas.base import ResponseSchema

CatalogueKind = Literal["category", "family", "unit", "tag", "ingredient", "equipment"]


class CatalogueFieldDifferenceResponse(ResponseSchema):
    """A field whose value here differs from the file's. Field names and
    values follow the reference data updates (`names.de-AT`, `allergens`,
    `nutrition.kcal`, ...); references are shown by name and conversions as
    unit code to grams."""

    field: str
    current: Any
    incoming: Any


class CataloguePreviewEntryResponse(ResponseSchema):
    kind: CatalogueKind
    # The entry's public id in the file.
    source_id: str
    name: str
    # The matched entry here, or null for an entry the import creates.
    local_id: str | None
    # Allergens and diet markers first; empty for a new entry.
    differences: list[CatalogueFieldDifferenceResponse]


class CatalogueKindSummaryResponse(ResponseSchema):
    kind: CatalogueKind
    total: int
    new: int
    matched: int
    # Matched entries with at least one differing field.
    different: int
    # True when the caller may not write this kind, so the import leaves it out.
    skipped: bool


class CatalogueConflictResponse(ResponseSchema):
    """Something of the file that is or was not written as it is."""

    kind: CatalogueKind
    name: str
    detail: str


class CataloguePreviewResponse(ResponseSchema):
    source_instance_id: str | None
    exported_at: str
    kinds: list[CatalogueKindSummaryResponse]
    # Every new entry and every matched entry with differences, those with
    # allergen or diet marker differences first.
    entries: list[CataloguePreviewEntryResponse]
    conflicts: list[CatalogueConflictResponse]


class CatalogueCreatedResponse(ResponseSchema):
    kind: CatalogueKind
    source_id: str
    name: str
    id: str


class CatalogueUpdatedResponse(ResponseSchema):
    kind: CatalogueKind
    source_id: str
    name: str
    id: str
    fields: list[str]


class CatalogueImportResponse(ResponseSchema):
    created: list[CatalogueCreatedResponse]
    updated: list[CatalogueUpdatedResponse]
    # Kinds the caller may not write, left out of the import.
    skipped: list[CatalogueKind]
    conflicts: list[CatalogueConflictResponse]
