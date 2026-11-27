"""
A browser the user told to skip the TOTP step for a number of days. The
secret lives only in an httponly cookie; the row keeps its SHA-256 hash, so
a database leak yields nothing replayable. The password is still required.
"""

from dataclasses import dataclass
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.services.clock import as_utc
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(kw_only=True)
class TrustedDevice(Entity):
    user_id: int
    token_hash: str
    created: datetime
    expires_at: datetime
    user_agent: str | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    @property
    def is_usable(self) -> bool:
        return self.revoked_at is None and as_utc(self.expires_at) > now_utc()
