"""
An admin-issued credential for a non-interactive client. Each key has its
own service account user, which holds the key's permissions, so whatever
the client does is attributed to that account and never to a person.
"""

from dataclasses import dataclass
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity
from src.shared_kernel.domain.services.clock import as_utc
from src.shared_kernel.domain.services.clock import now_utc


@dataclass(kw_only=True)
class ApiKey(Entity):
    name: str
    token_hash: str
    token_prefix: str
    service_user_id: int
    created: datetime
    # None once the creating account was deleted.
    creator_id: int | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    @property
    def is_usable(self) -> bool:
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or as_utc(self.expires_at) > now_utc()
