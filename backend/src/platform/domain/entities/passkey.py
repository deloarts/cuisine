"""
A WebAuthn credential registered to a user. A passkey stands in for the
password and the second factor at once, because the authenticator verified
the user (PIN, fingerprint, face) before it signed.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class Passkey(Entity):
    user_id: int
    name: str
    credential_id: bytes
    public_key: bytes
    sign_count: int
    created: datetime
    backed_up: bool = False
    transports: list[str] = field(default_factory=list)
    last_used_at: datetime | None = None
