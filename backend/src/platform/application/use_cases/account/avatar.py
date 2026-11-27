"""Avatars. The image goes through the file storage like any other,
re-encoded as WebP with its metadata dropped, and the file it replaces is
deleted in the same transaction, so a user holds at most one avatar file.
The signed-in user changes their own here; an administrator changes
someone else's through `ManageUsers`, which uses the same helpers."""

from src.platform.application.use_cases.files.manage_files import store_image
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import FileTypeNotAcceptedError
from src.platform.domain.services.content_types import IMAGE_CONTENT_TYPES
from src.platform.domain.services.content_types import normalise_content_type
from src.platform.domain.services.content_types import safe_file_name
from src.platform.ports.outbound.image_processor import IImageProcessor
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork


async def _delete_file(files: IStoredFileRepository, file_id: int | None) -> None:
    if file_id is None:
        return
    stored = await files.get(file_id)
    if stored is not None:
        await files.delete(stored)


async def replace_avatar_of(
    files: IStoredFileRepository,
    images: IImageProcessor,
    users: IUserRepository,
    user: User,
    *,
    data: bytes,
    file_name: str,
    content_type: str,
) -> User:
    """Stores the image as the user's avatar, owned by the user, and deletes
    the previous one. Does not commit."""
    if normalise_content_type(content_type) not in IMAGE_CONTENT_TYPES:
        raise FileTypeNotAcceptedError("Only images (JPEG, PNG, WebP, GIF).")
    stored = await store_image(files, images, user, data, safe_file_name(file_name))
    previous = user.avatar_file_id
    user.avatar_file_id = stored.id
    saved = await users.save(user)
    await _delete_file(files, previous)
    return saved


async def remove_avatar_of(
    files: IStoredFileRepository, users: IUserRepository, user: User
) -> User:
    """Clears the user's avatar and deletes its file. Does not commit."""
    previous = user.avatar_file_id
    user.avatar_file_id = None
    saved = await users.save(user)
    await _delete_file(files, previous)
    return saved


class ManageOwnAvatar:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        file_repo: IStoredFileRepository,
        images: IImageProcessor,
        uow: IUnitOfWork,
    ) -> None:
        self._users = user_repo
        self._files = file_repo
        self._images = images
        self._uow = uow

    async def replace(self, user: User, *, data: bytes, file_name: str, content_type: str) -> User:
        saved = await replace_avatar_of(
            self._files,
            self._images,
            self._users,
            user,
            data=data,
            file_name=file_name,
            content_type=content_type,
        )
        await self._uow.commit()
        return saved

    async def remove(self, user: User) -> User:
        saved = await remove_avatar_of(self._files, self._users, user)
        await self._uow.commit()
        return saved


async def delete_avatar_of(files: IStoredFileRepository, user: User) -> None:
    """Deletes the user's avatar file, for account deletion, which leaves
    nothing of the person behind. Does not commit."""
    await _delete_file(files, user.avatar_file_id)
