"""
Finds what a public id names without knowing its kind beforehand, for links
in mails, QR codes and agent references. The adapter only finds the row;
whether the user may open it is decided per kind by an `IPublicIdAccess`
that the package owning the kind registers from the composition root.
"""

from dataclasses import dataclass
from typing import Protocol
from typing import runtime_checkable
from uuid import UUID

from src.platform.domain.entities.user import User


@dataclass(frozen=True)
class ResolvedPublicId:
    """The row a public id named, already lifted to the page it opens: a
    step of a recipe is reported as its recipe."""

    # The kind of the page, such as "recipe".
    kind: str
    # The public id of the page's row, which for a child row is its parent's.
    public_id: UUID
    # For a personal record, which only its owner may resolve: the owner.
    personal: bool = False
    owner_id: int | None = None


@runtime_checkable
class IPublicIdResolver(Protocol):
    async def resolve(self, public_id: UUID) -> ResolvedPublicId | None: ...


@runtime_checkable
class IPublicIdAccess(Protocol):
    """The read rule and the page of one kind."""

    async def route(self, actor: User, public_id: UUID) -> str | None:
        """The frontend path of the row when `actor` may open it, None when
        the actor may not, which the caller answers like an unknown id."""
        ...
