"""
Which permissions may be granted, and by whom.

A grant is capped at what the granting user holds themselves, so nobody can
hand out more than they have; the system user holds everything. Managing an
account is capped the same way: an administrator may change, reset, sign
out or delete only an account whose effective permissions they all hold
themselves, so write:users never reaches an account with more rights. Tokens (PATs
and API keys) never carry write:settings, write:users or write:groups,
because a leaked token must not be able to take over the instance.
"""

from collections.abc import Iterable

from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidPermissionError
from src.platform.domain.exceptions import UserOutranksActorError
from src.platform.domain.value_objects.permission import Permission

NEVER_GRANTABLE_TO_TOKENS: frozenset[str] = frozenset(
    {
        Permission.WRITE_SETTINGS,
        Permission.WRITE_USERS,
        Permission.WRITE_GROUPS,
        Permission.MANAGE_API_KEYS,
        Permission.WRITE_PAT,
    }
)


def assert_known(permissions: Iterable[str]) -> None:
    unknown = sorted(set(permissions) - set(Permission.ALL))
    if unknown:
        raise InvalidPermissionError(f"Unknown permissions: {', '.join(unknown)}")


def assert_grantable_by(granter: User, permissions: Iterable[str]) -> None:
    """Every permission must exist and be held by the granter."""
    wanted = set(permissions)
    assert_known(wanted)
    if granter.is_systemuser:
        return
    missing = sorted(wanted - set(granter.effective_permissions))
    if missing:
        raise InvalidPermissionError(
            f"You cannot grant permissions you do not hold: {', '.join(missing)}"
        )


def assert_may_manage(actor: User, target: User) -> None:
    """The actor must hold every effective permission of the target, the
    target's group permissions included. The system user passes, and only
    the system user may manage the system user."""
    if actor.is_systemuser or actor.id == target.id:
        return
    if target.is_systemuser:
        raise UserOutranksActorError("Only the system user can manage the system user.")
    missing = sorted(set(target.effective_permissions) - set(actor.effective_permissions))
    if missing:
        raise UserOutranksActorError(
            "You cannot manage an account that holds permissions you do not hold: "
            f"{', '.join(missing)}"
        )


def assert_grantable_to_token(granter: User, permissions: Iterable[str]) -> None:
    """A token's permissions must be grantable by its creator and must not
    include any of the instance-control permissions."""
    wanted = set(permissions)
    assert_grantable_by(granter, wanted)
    blocked = sorted(wanted & NEVER_GRANTABLE_TO_TOKENS)
    if blocked:
        raise InvalidPermissionError(f"Tokens cannot carry: {', '.join(blocked)}")
