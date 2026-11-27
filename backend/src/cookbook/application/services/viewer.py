"""Builds the viewer of a request: the user with their groups and their
household's members, which decide the recipes they see. One resolver serves
one request and remembers what it built."""

from src.cookbook.domain.value_objects.viewer import Viewer
from src.cookbook.ports.outbound.repositories.household_repository import IHouseholdRepository
from src.platform.domain.entities.user import User


class ViewerResolver:
    def __init__(self, *, household_repo: IHouseholdRepository) -> None:
        self._households = household_repo
        self._cache: dict[int, Viewer] = {}

    async def of(self, user: User) -> Viewer:
        cached = self._cache.get(user.id)
        if cached is not None and cached.user is user:
            return cached
        household = await self._households.of_user(user.id) if user.id else None
        viewer = Viewer(
            user=user,
            group_ids=frozenset(user.group_ids),
            household_id=household.id if household else None,
            household_member_ids=frozenset(household.member_ids) if household else frozenset(),
        )
        self._cache[user.id] = viewer
        return viewer
