"""
/api/v1/web/files: the file storage. Uploading needs a session. Reading
follows `FileAccess`: an own upload, an avatar, a branding image or an
image of a recipe the user may see; anything else answers 404 like an
unknown id. Only the uploader deletes a file, and only while nothing uses
it. Content answers 304 when the browser's ETag still matches, so an
unchanged image is never sent twice.
"""

from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Header
from fastapi import Query
from fastapi import Response
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import RedirectResponse

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.deps import get_manage_files
from src.platform.adapters.inbound.api.download_headers import build_download_headers
from src.platform.adapters.inbound.api.download_headers import etag_matches
from src.platform.adapters.inbound.api.download_headers import file_download_response
from src.platform.adapters.inbound.api.schemas.file_schema import StoredFileResponse
from src.platform.application.use_cases.files.manage_files import ManageFiles
from src.platform.const import MAX_DOCUMENT_UPLOAD_BYTES
from src.platform.const import MAX_IMAGE_UPLOAD_BYTES
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import FileTooLargeError

# The largest upload of any kind; the use case applies the limit per kind.
MAX_UPLOAD_BYTES = max(MAX_IMAGE_UPLOAD_BYTES, MAX_DOCUMENT_UPLOAD_BYTES)

router = APIRouter(prefix="/files", tags=["files"])


def _file(stored: StoredFile) -> StoredFileResponse:
    return StoredFileResponse(
        id=stored.public_id,
        file_name=stored.file_name,
        content_type=stored.content_type,
        size=stored.size,
        width=stored.width,
        height=stored.height,
        has_thumbnail=stored.thumbnail_hash is not None,
        created=stored.created,
    )


@router.post("", response_model=StoredFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    actor: User = Depends(get_current_user),
    use_case: ManageFiles = Depends(get_manage_files),
) -> StoredFileResponse:
    # Reads at most one byte past the largest limit, so an oversized body
    # is never pulled into memory as a whole.
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise FileTooLargeError("The file is too large.")
    stored = await use_case.upload(
        actor,
        data=data,
        file_name=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
    )
    return _file(stored)


@router.get("/{file_id}", response_model=StoredFileResponse)
async def read_file(
    file_id: str,
    user: User = Depends(get_current_user),
    use_case: ManageFiles = Depends(get_manage_files),
) -> StoredFileResponse:
    return _file(await use_case.get_for(user, file_id))


@router.get(
    "/{file_id}/content",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}, 304: {}, 307: {}},
)
async def read_file_content(
    file_id: str,
    variant: Literal["original", "thumbnail"] = Query("original"),
    disposition: Literal["inline", "attachment"] = Query("inline"),
    if_none_match: str | None = Header(default=None),
    user: User = Depends(get_current_user),
    use_case: ManageFiles = Depends(get_manage_files),
) -> Response:
    thumbnail = variant == "thumbnail"
    stored = await use_case.get_for(user, file_id)
    etag = use_case.etag_of(stored, thumbnail=thumbnail)
    if etag_matches(if_none_match, etag):
        headers = build_download_headers(
            stored.file_name, content_type=stored.content_type, etag=etag, disposition=disposition
        )
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    # With an object store the browser loads the bytes from it directly,
    # through a presigned URL that repeats the type and disposition rules.
    presigned = await use_case.content_url(
        stored, thumbnail=thumbnail, inline=disposition == "inline"
    )
    if presigned is not None:
        return RedirectResponse(
            presigned.url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Cache-Control": "private, no-store"},
        )
    content = await use_case.content(file_id, thumbnail=thumbnail)
    return file_download_response(
        content.data,
        content.file_name,
        content_type=content.content_type,
        etag=content.etag,
        disposition=disposition,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    actor: User = Depends(get_current_user),
    use_case: ManageFiles = Depends(get_manage_files),
) -> None:
    await use_case.delete(actor, file_id)
