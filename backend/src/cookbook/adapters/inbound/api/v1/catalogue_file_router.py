"""The catalogue file: exporting the whole catalogue as one
`cuisine-catalogue` JSON file, and importing such a file in two steps, a
preview that writes nothing and the apply that creates the new entries and
writes the differences the administrator accepted. The permissions are
checked per kind in the use case (`CatalogueFile`): ingredients need
manage:ingredients with write:ingredients, every other kind write:resources."""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import Response
from fastapi import UploadFile

from src.cookbook.adapters.inbound.api.deps import get_catalogue_file
from src.cookbook.adapters.inbound.api.schemas.catalogue_file_schema import CatalogueImportResponse
from src.cookbook.adapters.inbound.api.schemas.catalogue_file_schema import CataloguePreviewResponse
from src.cookbook.application.use_cases.resources.catalogue_file import KINDS
from src.cookbook.application.use_cases.resources.catalogue_file import MAX_FILE_BYTES
from src.cookbook.application.use_cases.resources.catalogue_file import AcceptedField
from src.cookbook.application.use_cases.resources.catalogue_file import CatalogueFile
from src.cookbook.domain.exceptions import CatalogueFileError
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.domain.entities.user import User
from src.platform.domain.services.content_types import content_disposition
from src.shared_kernel.domain.services.clock import now_utc

router = APIRouter(tags=["catalogue-file"])

_DOWNLOAD_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"}
_FILE = File(..., description="A `cuisine-catalogue` JSON file.")


async def _read(file: UploadFile) -> bytes:
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise CatalogueFileError("The catalogue file is too large.")
    return data


def _accepted(values: list[str]) -> list[AcceptedField]:
    found: list[AcceptedField] = []
    for value in values:
        kind, _, rest = value.partition(":")
        source_id, _, field = rest.partition(":")
        if kind not in KINDS or not source_id or not field:
            raise CatalogueFileError(f"{value[:200]!r} names no field of the catalogue file.")
        found.append(AcceptedField(kind=kind, source_id=source_id, field=field))
    return found


@router.get(
    "/admin/catalogue/export",
    response_class=Response,
    responses={200: {"content": {"application/json": {}}, "description": "The catalogue file."}},
)
async def export_catalogue(
    actor: User = Depends(get_current_user),
    catalogue: CatalogueFile = Depends(get_catalogue_file),
) -> Response:
    """Every unit, tag, category and family and the active ingredients and
    equipment as `cuisine-catalogue-<date>.json`. Needs manage:ingredients or
    write:resources."""
    data = await catalogue.export(actor)
    name = f"cuisine-catalogue-{now_utc().date().isoformat()}.json"
    return Response(
        content=data,
        media_type="application/json",
        headers={
            "Content-Disposition": content_disposition(name, inline=False),
            **_DOWNLOAD_HEADERS,
        },
    )


@router.post("/admin/catalogue/import/preview", response_model=CataloguePreviewResponse)
async def preview_catalogue_import(
    file: UploadFile = _FILE,
    actor: User = Depends(get_current_user),
    catalogue: CatalogueFile = Depends(get_catalogue_file),
) -> CataloguePreviewResponse:
    """Per kind and entry of the file, whether it matches an entry here or
    is new, and for a matched entry the fields whose values differ, with the
    value here and the file's. Writes nothing."""
    preview = await catalogue.preview(actor, await _read(file))
    return CataloguePreviewResponse.model_validate(preview)


@router.post("/admin/catalogue/import", response_model=CatalogueImportResponse)
async def import_catalogue(
    file: UploadFile = _FILE,
    accept: list[str] = Form(
        default_factory=list,
        description=(
            "The differences to write, each as `<kind>:<source id>:<field>`; every other "
            "difference changes nothing."
        ),
    ),
    actor: User = Depends(get_current_user),
    catalogue: CatalogueFile = Depends(get_catalogue_file),
) -> CatalogueImportResponse:
    """Creates every new entry of the kinds the caller may write, active,
    and writes the accepted differences, all in one transaction, reporting
    what was created, what was changed, the kinds left out and what could
    not be written."""
    report = await catalogue.apply(actor, await _read(file), _accepted(accept))
    return CatalogueImportResponse.model_validate(report)
