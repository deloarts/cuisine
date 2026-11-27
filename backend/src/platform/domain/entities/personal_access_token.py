"""
A user's own scoped bearer token. It acts as its owner, limited to the
permissions chosen at creation. Only the SHA-256 hash of the secret is
stored; the plain token is shown once.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.services.clock import as_utc
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(kw_only=True)
class PersonalAccessToken(Entity):
    user_id: int
    name: str
    token_hash: str
    token_prefix: str
    created: datetime
    permissions: list[str] = field(default_factory=list)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    @property
    def is_usable(self) -> bool:
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or as_utc(self.expires_at) > now_utc()
