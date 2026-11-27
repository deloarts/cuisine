"""
The lockout gate of the password and TOTP steps. Failures count per
normalised login e-mail and per client IP; either reaching the limit locks
that key. A wrong password counts whether or not the account exists, so an
unknown e-mail is not measurably cheaper than a wrong password.
"""

from src.platform.domain.entities.settings import SecuritySettings
from src.platform.domain.exceptions import LoginLockedError
from src.platform.ports.outbound.login_attempts import ILoginAttemptTracker

LOCKED_MESSAGE = "Too many failed attempts. Try again later."


def user_key(login: str) -> str:
    return f"user:{login.strip().lower()}"


def ip_key(client_ip: str | None) -> str | None:
    return f"ip:{client_ip}" if client_ip else None


class LoginThrottle:
    def __init__(self, attempts: ILoginAttemptTracker) -> None:
        self._attempts = attempts

    def _keys(self, login: str, client_ip: str | None) -> list[str]:
        keys = [user_key(login)]
        address = ip_key(client_ip)
        if address is not None:
            keys.append(address)
        return keys

    async def assert_allowed(self, login: str, client_ip: str | None) -> None:
        for key in self._keys(login, client_ip):
            locked_for = await self._attempts.lock_ttl(key)
            if locked_for > 0:
                raise LoginLockedError(LOCKED_MESSAGE, retry_after_seconds=locked_for)

    async def record_failure(
        self, login: str, client_ip: str | None, settings: SecuritySettings
    ) -> list[str]:
        """Counts the failure and returns the keys it locked."""
        locked: list[str] = []
        for key in self._keys(login, client_ip):
            locked_now = await self._attempts.record_failure(
                key,
                limit=settings.max_login_attempts,
                lockout_seconds=settings.lockout_duration_minutes * 60,
            )
            if locked_now:
                locked.append(key)
        return locked

    async def record_success(self, login: str) -> None:
        """Forgets the login's earlier failures. The client IP keeps its count,
        so one valid account cannot be used to reset a guessing run."""
        await self._attempts.reset(user_key(login))
