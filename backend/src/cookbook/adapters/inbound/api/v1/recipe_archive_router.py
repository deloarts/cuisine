"""Recipes as `.cui` files: exporting one recipe for anyone signed in who
can open it, importing a file for anyone with write:recipes, and the bulk
export of many recipes for administrators (manage:recipes). Every imported
recipe becomes a draft of the importer, or updates their earlier import of
it when they choose so after the preview."""

import re
import unicodedata

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import Query
from fastapi import Response
from fastapi import UploadFile

from src.cookbook.adapters.inbound.api.deps import get_recipe_archive
from src.cookbook.adapters.inbound.api.schemas.archive_schema import EarlierImportResponse
from src.cookbook.adapters.inbound.api.schemas.archive_schema import ImportConflictResponse
from src.cookbook.adapters.inbound.api.schemas.archive_schema import ImportedRecipeResponse
from src.cookbook.adapters.inbound.api.schemas.archive_schema import ImportPreviewRecipeResponse
from src.cookbook.adapters.inbound.api.schemas.archive_schema import RecipeImportPreviewResponse
from src.cookbook.adapters.inbound.api.schemas.archive_schema import RecipeImportResponse
from src.cookbook.application.use_cases.recipes.recipe_archive import RecipeArchive
from src.cookbook.domain.exceptions import RecipeArchiveError
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.domain.entities.user import User
from src.platform.domain.services.content_types import content_disposition
from src.platform.domain.value_objects.permission import Permission
from src.shared_kernel.domain.services.clock import now_utc

router = APIRouter(tags=["recipe-archive"])

_manage = require_permission(Permission.MANAGE_RECIPES)
_write = require_permission(Permission.WRITE_RECIPES)
# The largest archive an import reads.
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
# The media type of a `.cui` file: a zip archive in the cuisine-recipes format.
CUI_MEDIA_TYPE = "application/vnd.cuisine.recipe+zip"
_DOWNLOAD_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"}


def cui_file_name(title: str) -> str:
    """`<slug of the title>.cui`: lower case ASCII letters, digits and
    hyphens, at most 80 characters, or `recipe.cui` when nothing is left."""
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")[:80].rstrip("-")
    return f"{slug or 'recipe'}.cui"


async def _read(file: UploadFile) -> bytes:
    data = await file.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise RecipeArchiveError("The archive is too large.")
    return data


@router.get(
    "/recipes/{recipe_id}/export",
    response_class=Response,
    responses={200: {"content": {CUI_MEDIA_TYPE: {}}, "description": "The `.cui` file."}},
)
async def export_recipe(
    recipe_id: str,
    actor: User = Depends(get_current_user),
    archive: RecipeArchive = Depends(get_recipe_archive),
) -> Response:
    """The recipe with its visible sub-recipes and variations, the catalogue
    entries they use and their images, as a `.cui` file. Allowed for anyone
    who can open the recipe; 404 for a recipe the caller may not see."""
    exported = await archive.export_recipe(actor, recipe_id)
    return Response(
        content=exported.data,
        media_type=CUI_MEDIA_TYPE,
        headers={
            "Content-Disposition": content_disposition(cui_file_name(exported.title), inline=False),
            **_DOWNLOAD_HEADERS,
        },
    )


@router.get(
    "/admin/recipes/export",
    response_class=Response,
    responses={200: {"content": {CUI_MEDIA_TYPE: {}}, "description": "The `.cui` file."}},
)
async def export_recipes(
    recipe_id: list[str] | None = Query(
        None, description="The recipes to export; every recipe the caller may see without."
    ),
    actor: User = Depends(_manage),
    archive: RecipeArchive = Depends(get_recipe_archive),
) -> Response:
    """The recipes with their visible sub-recipes, the catalogue entries
    they use and their images, as one `.cui` file for another instance."""
    data = await archive.export(actor, recipe_id)
    name = f"cuisine-recipes-{now_utc().date().isoformat()}.cui"
    return Response(
        content=data,
        media_type=CUI_MEDIA_TYPE,
        headers={
            "Content-Disposition": content_disposition(name, inline=False),
            **_DOWNLOAD_HEADERS,
        },
    )


@router.post("/recipes/import/preview", response_model=RecipeImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(..., description="A `.cui` file or an older recipe archive."),
    actor: User = Depends(_write),
    archive: RecipeArchive = Depends(get_recipe_archive),
) -> RecipeImportPreviewResponse:
    """The recipes of the file, each with the caller's earlier import of it,
    so the caller can choose per recipe to update it or to import a new
    copy. Checks the file like the import and stores nothing."""
    preview = await archive.preview(actor, await _read(file))
    return RecipeImportPreviewResponse(
        recipes=[
            ImportPreviewRecipeResponse(
                source_id=r.source_id,
                title=r.title,
                earlier=EarlierImportResponse.model_validate(r.earlier)
                if r.earlier is not None
                else None,
            )
            for r in preview.recipes
        ]
    )


@router.post("/recipes/import", response_model=RecipeImportResponse)
async def import_recipes(
    file: UploadFile = File(..., description="A `.cui` file or an older recipe archive."),
    update: list[str] = Form(
        default_factory=list,
        description=(
            "Source ids of recipes whose earlier import the caller wants updated; every other "
            "recipe imported before becomes a new copy."
        ),
    ),
    actor: User = Depends(_write),
    archive: RecipeArchive = Depends(get_recipe_archive),
) -> RecipeImportResponse:
    """Imports every recipe of the file as a draft of the caller, or as an
    update of the caller's earlier import where asked, and reports what
    matched, what was created and what could not be placed."""
    report = await archive.import_archive(actor, await _read(file), set(update))
    return RecipeImportResponse(
        recipes=[
            ImportedRecipeResponse(source_id=r.source_id, id=r.id, title=r.title, updated=r.updated)
            for r in report.recipes
        ],
        created_ingredients=report.created_ingredients,
        created_equipment=report.created_equipment,
        matched_ingredients=report.matched_ingredients,
        matched_equipment=report.matched_equipment,
        conflicts=[
            ImportConflictResponse(kind=c.kind, name=c.name, detail=c.detail, recipe=c.recipe)
            for c in report.conflicts
        ],
    )
