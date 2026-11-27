"""
An in-app notice: a dialog every active user sees once after signing in,
until they acknowledge it. The administrator sees who acknowledged it.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity


@dataclass(frozen=True)
class NoticeText:
    title: str
    # The Markdown subset the recipe text uses.
    body: str


@dataclass(kw_only=True)
class Notice(Entity):
    # Per content locale (en-GB, de-AT); a reader gets their own, else
    # en-GB, else any.
    texts: dict[str, NoticeText] = field(default_factory=dict)
    # Only active notices are shown; switching one off keeps its
    # acknowledgements.
    active: bool = True
    created: datetime
    changed: datetime
    created_by_id: int | None = None


@dataclass(frozen=True)
class NoticeAcknowledgement:
    user_id: int
    acknowledged_at: datetime
