"""When a web session ends: after an idle period or after its absolute
lifetime, whichever comes first, or when it is revoked.

A session of the system user instead ends a fixed 15 minutes after sign-in,
whatever the user does in between. The limit is deliberately not a setting,
so the account holding every permission cannot have its lifetime configured
away."""

from datetime import datetime
from datetime import timedelta
from typing import Final

from src.platform.domain.entities.settings import SecuritySettings
from src.platform.domain.entities.user_session import UserSession
from src.shared_kernel.domain.services.clock import as_utc

SYSTEM_USER_SESSION_LIFETIME: Final = timedelta(minutes=15)


def session_hard_expiry(
    session: UserSession, settings: SecuritySettings, *, is_systemuser: bool
) -> datetime | None:
    """When the absolute lifetime ends: 15 minutes after sign-in for the
    system user, the configured lifetime for everyone else, or None when no
    lifetime is configured."""
    created = as_utc(session.created)
    if is_systemuser:
        return created + SYSTEM_USER_SESSION_LIFETIME
    if settings.session_max_lifetime_days > 0:
        return created + timedelta(days=settings.session_max_lifetime_days)
    return None


def session_expired(
    session: UserSession, settings: SecuritySettings, now: datetime, *, is_systemuser: bool = False
) -> bool:
    """Whether the session is revoked, past its idle timeout or past its
    absolute lifetime."""
    if session.revoked_at is not None:
        return True
    if settings.session_timeout_minutes > 0:
        idle_limit = as_utc(session.last_seen_at) + timedelta(
            minutes=settings.session_timeout_minutes
        )
        if now >= idle_limit:
            return True
    expiry = session_hard_expiry(session, settings, is_systemuser=is_systemuser)
    return expiry is not None and now >= expiry


def session_cookie_max_age(settings: SecuritySettings, *, is_systemuser: bool) -> int:
    """Seconds the browser keeps the session cookie: the system user's 15
    minutes, the absolute lifetime, or a day when there is none. The
    server-side row decides the rest."""
    if is_systemuser:
        return int(SYSTEM_USER_SESSION_LIFETIME.total_seconds())
    days = settings.session_max_lifetime_days or 1
    return days * 24 * 60 * 60


# Activity stamps closer together than this are not written, so a busy
# page does not turn every request into a database write.
LAST_SEEN_WRITE_INTERVAL = timedelta(minutes=1)
