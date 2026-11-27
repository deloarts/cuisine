"""
Who may read and delete a stored file. A signed-in user reads a file they
uploaded themselves, any avatar (every signed-in user sees every other
user's name), the branding images (which the sign-in page shows anyway) and
whatever a registered feature rule lets them see, such as the images of
the recipes they may view. Anything else answers like an unknown file, so a
file id alone never opens a private recipe's photo.

The same parts decide whether a file is referenced. A live reference keeps
it from the uploader's delete; the nightly sweep of unused uploads also
spares a file that only the history (a revision snapshot) names, so a
restore can bring it back, while its uploader may still delete it.
"""

from collections.abc import Sequence

from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.file_access import IFileAccess
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository


class FileAccess:
    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        features: Sequence[IFileAccess] = (),
    ) -> None:
        self._users = user_repo
        self._settings = settings_repo
        self._features = features

    async def _branding(self, file: StoredFile) -> bool:
        general = await self._settings.get_general()
        return general.login_background_file_id == str(file.public_id)

    async def platform_use(self, file: StoredFile) -> bool:
        """Whether the file is an avatar or a branding image."""
        return await self._users.avatar_in_use(file.id) or await self._branding(file)

    async def may_read(self, actor: User, file: StoredFile) -> bool:
        if file.creator_id is not None and file.creator_id == actor.id:
            return True
        if await self.platform_use(file):
            return True
        for feature in self._features:
            if await feature.may_read(actor, file):
                return True
        return False

    async def in_use(self, file: StoredFile) -> bool:
        return file.id in await self.referenced([file], history=False)

    async def referenced(self, files: Sequence[StoredFile], *, history: bool) -> set[int]:
        """The ids of those files that an avatar, a branding image or a
        feature's record refers to, with `history` including the records
        kept for the past."""
        general = await self._settings.get_general()
        background = general.login_background_file_id
        branding = {background.lower()} if background else set()
        found = {f.id for f in files if str(f.public_id).lower() in branding}
        found |= await self._users.avatar_file_ids([f.id for f in files])
        for feature in self._features:
            left = [f for f in files if f.id not in found]
            if not left:
                break
            found |= await feature.referenced(left, history=history)
        return found
