"""Who is reading: a signed-in user with what decides which recipes they
see, or an anonymous visitor of the public pages."""

from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime

from src.platform.domain.entities.user import User


def _nobody() -> User:
    """The stand-in account of an anonymous visitor: id 0, which no saved
    row has, inactive and without a single permission, so every owner,
    share and permission check fails for it."""
    return User(
        full_name="",
        email="",
        created=datetime(1970, 1, 1, tzinfo=UTC),
        hashed_password="",
        is_active=False,
    )


@dataclass(frozen=True)
class Viewer:
    user: User
    # The groups the user belongs to, for recipes shared with a group.
    group_ids: frozenset[int] = field(default_factory=frozenset)
    household_id: int | None = None
    # Every member of the user's household, the user included; empty
    # without a household.
    household_member_ids: frozenset[int] = field(default_factory=frozenset)
    # A visitor who is not signed in. It reads published public recipes
    # only, and only while the instance allows public recipes
    # (`public_allowed`, which matters for nobody else).
    anonymous: bool = False
    public_allowed: bool = False

    @property
    def id(self) -> int:
        return self.user.id

    @classmethod
    def visitor(cls, *, public_allowed: bool) -> "Viewer":
        """The anonymous visitor of the public pages."""
        return cls(user=_nobody(), anonymous=True, public_allowed=public_allowed)
