"""
A household: the people who cook and shop together. A user belongs to at
most one. It owns the meal plan of its members and one default shopping
list. Joining takes an invitation the invitee accepts; the last member
leaving dissolves the household with its plan and list.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class Household(Entity):
    name: str
    created: datetime
    member_ids: list[int] = field(default_factory=list)


@dataclass(kw_only=True)
class HouseholdInvitation(Entity):
    household_id: int
    inviter_id: int | None
    invitee_id: int
    created: datetime
