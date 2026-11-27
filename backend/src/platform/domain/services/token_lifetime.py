"""The lifetime cap of new personal access tokens and API keys."""

from datetime import datetime
from datetime import timedelta

from src.platform.domain.exceptions import InvalidInputError
from src.shared_kernel.domain.services.clock import as_utc


def assert_token_lifetime(expires_at: datetime | None, max_days: int, now: datetime) -> None:
    """With a cap above 0 every token needs an expiry within it; an expiry
    must always lie in the future."""
    if expires_at is not None and as_utc(expires_at) <= now:
        raise InvalidInputError("The expiry must lie in the future.")
    if max_days <= 0:
        return
    if expires_at is None:
        raise InvalidInputError(f"Tokens must expire within {max_days} days.")
    if as_utc(expires_at) > now + timedelta(days=max_days):
        raise InvalidInputError(f"Tokens must expire within {max_days} days.")
