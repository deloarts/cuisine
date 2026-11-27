"""
Storing and reading files. Images are re-encoded to WebP with a thumbnail,
which drops their metadata; PDFs are stored as uploaded after their
signature was checked, with the type `application/pdf` set by the server
rather than the client's declared string. The content hash of the stored bytes is the ETag.
Reads on behalf of a user go through `FileAccess`; the unchecked reads are
for routes that applied a rule of their own, such as the public recipe
images and the branding images.
"""

import hashlib
from dataclasses import dataclass

from src.platform.application.services.file_access import FileAccess
from src.platform.const import MAX_DOCUMENT_UPLOAD_BYTES
from src.platform.const import MAX_IMAGE_UPLOAD_BYTES
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import FileInUseError
from src.platform.domain.exceptions import FileTooLargeError
from src.platform.domain.exceptions import FileTypeNotAcceptedError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.exceptions import StoredFileNotFoundError
from src.platform.domain.services.content_types import DOCUMENT_CONTENT_TYPES
from src.platform.domain.services.content_types import IMAGE_CONTENT_TYPES
from src.platform.domain.services.content_types import normalise_content_type
from src.platform.domain.services.content_types import safe_file_name
from src.platform.ports.outbound.file_content_store import ContentUrl
from src.platform.ports.outbound.image_processor import IImageProcessor
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

PDF_SIGNATURE = b"%PDF-"
PDF_CONTENT_TYPE = "application/pdf"


@dataclass(frozen=True)
class FileContent:
    file: StoredFile
    data: bytes
    content_type: str
    etag: str
    file_name: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _webp_name(file_name: str) -> str:
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    return f"{stem or 'image'}.webp"


async def store_image(
    files: IStoredFileRepository, images: IImageProcessor, actor: User, data: bytes, name: str
) -> StoredFile:
    """Re-encodes an upload as WebP with a thumbnail and adds it, without
    committing. Shared by the file storage and the avatar upload."""
    if len(data) > MAX_IMAGE_UPLOAD_BYTES:
        raise FileTooLargeError("The image is too large.")
    processed = await images.process(data)
    return await files.add(
        StoredFile(
            file_name=_webp_name(name),
            content_type="image/webp",
            size=len(processed.data),
            content_hash=_sha256(processed.data),
            created=now_utc(),
            creator_id=actor.id or None,
            width=processed.width,
            height=processed.height,
            thumbnail_size=len(processed.thumbnail),
            thumbnail_hash=_sha256(processed.thumbnail),
        ),
        processed.data,
        processed.thumbnail,
    )


class ManageFiles:
    def __init__(
        self,
        *,
        file_repo: IStoredFileRepository,
        images: IImageProcessor,
        access: FileAccess,
        uow: IUnitOfWork,
    ) -> None:
        self._files = file_repo
        self._images = images
        self._access = access
        self._uow = uow

    async def upload(
        self, actor: User, *, data: bytes, file_name: str, content_type: str
    ) -> StoredFile:
        kind = normalise_content_type(content_type)
        name = safe_file_name(file_name)
        if kind in IMAGE_CONTENT_TYPES:
            stored = await store_image(self._files, self._images, actor, data, name)
        elif kind in DOCUMENT_CONTENT_TYPES:
            stored = await self._store_document(actor, data, name)
        else:
            raise FileTypeNotAcceptedError("Only images (JPEG, PNG, WebP, GIF) and PDFs.")
        await self._uow.commit()
        return stored

    async def _store_document(self, actor: User, data: bytes, name: str) -> StoredFile:
        if len(data) > MAX_DOCUMENT_UPLOAD_BYTES:
            raise FileTooLargeError("The document is too large.")
        if not data.startswith(PDF_SIGNATURE):
            raise FileTypeNotAcceptedError("The file is not a PDF.")
        return await self._files.add(
            StoredFile(
                file_name=name,
                content_type=PDF_CONTENT_TYPE,
                size=len(data),
                content_hash=_sha256(data),
                created=now_utc(),
                creator_id=actor.id or None,
            ),
            data,
            None,
        )

    async def get(self, public_id: str) -> StoredFile:
        stored = await self._files.get_by_public_id(public_id)
        if stored is None:
            raise StoredFileNotFoundError("No such file.")
        return stored

    async def get_for(self, actor: User, public_id: str) -> StoredFile:
        """The file when `actor` may read it; otherwise StoredFileNotFoundError,
        exactly as for an unknown id."""
        stored = await self.get(public_id)
        if not await self._access.may_read(actor, stored):
            raise StoredFileNotFoundError("No such file.")
        return stored

    def etag_of(self, stored: StoredFile, *, thumbnail: bool) -> str:
        if thumbnail and stored.thumbnail_hash:
            return f'"{stored.thumbnail_hash}"'
        return f'"{stored.content_hash}"'

    async def content(self, public_id: str, *, thumbnail: bool) -> FileContent:
        stored = await self.get(public_id)
        # A document has no thumbnail; asking for one serves the original.
        use_thumbnail = thumbnail and stored.thumbnail_hash is not None
        data = await self._files.read_content(stored, thumbnail=use_thumbnail)
        if data is None:
            raise StoredFileNotFoundError("No such file.")
        return FileContent(
            file=stored,
            data=data,
            content_type=stored.content_type,
            etag=self.etag_of(stored, thumbnail=use_thumbnail),
            file_name=stored.file_name,
        )

    async def content_url(
        self, stored: StoredFile, *, thumbnail: bool, inline: bool
    ) -> ContentUrl | None:
        """A presigned URL when the storage provider serves content itself,
        None when the backend streams it."""
        use_thumbnail = thumbnail and stored.thumbnail_hash is not None
        return self._files.content_url(stored, thumbnail=use_thumbnail, inline=inline)

    async def delete(self, actor: User, public_id: str) -> None:
        """Deletes an upload of the actor's own that nothing uses yet, such as
        an image picked in the editor and then dropped. A file in use goes
        with whatever uses it: the recipe, the avatar or the branding."""
        stored = await self.get_for(actor, public_id)
        if stored.creator_id is None or stored.creator_id != actor.id:
            raise PermissionDeniedError("Only who uploaded a file can delete it.")
        if await self._access.in_use(stored):
            raise FileInUseError("The file is still in use.")
        await self._files.delete(stored)
        await self._uow.commit()
