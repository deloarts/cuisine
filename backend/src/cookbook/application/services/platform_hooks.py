"""
The cookbook's parts of two Platform duties, registered from the
composition root: deleting a user's food restrictions when they withdraw
the health data consent, and the nightly purge of old recipe revisions.
"""

from datetime import timedelta

from src.cookbook.ports.outbound.repositories.personal_repositories import (
    IFoodRestrictionRepository,
)
from src.cookbook.ports.outbound.repositories.revision_repository import IRecipeRevisionRepository
from src.platform.domain.entities.settings import RetentionSettings
from src.shared_kernel.domain.services.clock import now_utc


class HealthDataEraser:
    """Fulfils Platform's IHealthDataEraser: the allergies, intolerances and
    diets go in the transaction of the withdrawal, which Platform commits."""

    def __init__(self, restrictions: IFoodRestrictionRepository) -> None:
        self._restrictions = restrictions

    async def erase(self, user_id: int) -> int:
        return await self._restrictions.delete_for_user(user_id)


class RevisionPurger:
    """A retention purge step: deletes revisions older than the configured
    days, keeping each recipe's newest, and nothing when the setting is 0.
    The nightly purge commits."""

    def __init__(self, revisions: IRecipeRevisionRepository) -> None:
        self._revisions = revisions

    async def __call__(self, retention: RetentionSettings) -> int:
        if not retention.recipe_revisions_days:
            return 0
        cutoff = now_utc() - timedelta(days=retention.recipe_revisions_days)
        return await self._revisions.delete_older_than(cutoff)
