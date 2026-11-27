"""
A feature's rule for the stored files its records refer to. Platform knows
avatars and the branding images; the cookbook knows recipe images and
registers its rule from the composition root (src/bootstrap), so Platform
never imports the cookbook.
"""

from collections.abc import Sequence
from typing import Protocol

from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.entities.user import User


class IFileAccess(Protocol):
    async def may_read(self, actor: User, file: StoredFile) -> bool:
        """Whether one of the feature's records that `actor` may see refers
        to the file."""
        ...

    async def referenced(self, files: Sequence[StoredFile], *, history: bool) -> set[int]:
        """The ids of those files that any of the feature's live records
        refers to, and with `history` also a record kept for the past, such
        as a revision snapshot."""
        ...
