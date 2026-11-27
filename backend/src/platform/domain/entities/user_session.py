"""
A signed-in browser. The session token carries this row's public_id, so a
session ends the moment its row is revoked, and the account page can list
and revoke every device that is signed in.
"""

from dataclasses import dataclass
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class UserSession(Entity):
    user_id: int
    created: datetime
    last_seen_at: datetime
    user_agent: str | None = None
    client_ip: str | None = None
    revoked_at: datetime | None = None
