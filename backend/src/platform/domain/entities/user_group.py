"""
A named bundle of permissions with its members. Every member holds the
group's permissions on top of their own direct grants. Groups are freely
named; "viewer" or "chef" are conventions of an instance, not of the code.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime

from src.shared_kernel.domain.entities.base import Entity


@dataclass(kw_only=True)
class UserGroup(Entity):
    name: str
    description: str
    permissions: list[str]
    created: datetime
    member_ids: list[int] = field(default_factory=list)
