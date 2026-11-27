from collections.abc import Collection
from typing import Protocol

from src.platform.domain.entities.user import User


class IUserRepository(Protocol):
    async def get(self, user_id: int) -> User | None: ...
    async def get_by_public_id(self, public_id: str) -> User | None: ...
    async def avatar_in_use(self, file_id: int) -> bool:
        """Whether the file is any user's avatar."""
        ...

    async def avatar_file_ids(self, file_ids: Collection[int]) -> set[int]:
        """Those of the files that are a user's avatar."""
        ...

    async def get_by_login(self, login: str) -> User | None:
        """By what the user signs in with: `system` for the system user,
        otherwise the e-mail address, case-insensitive."""
        ...

    async def get_by_email(self, email: str) -> User | None:
        """By e-mail address, case-insensitive."""
        ...

    async def email_taken(self, email: str, exclude_id: int | None = None) -> bool: ...
    async def list_all(
        self,
        *,
        include_service_accounts: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[User]: ...
    async def save(self, user: User) -> User:
        """Inserts or updates, including group memberships, and returns the
        user as stored."""
        ...

    async def delete(self, user: User) -> None: ...
