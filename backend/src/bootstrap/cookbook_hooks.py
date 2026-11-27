"""
Registers the cookbook's parts of Platform duties with Platform's dependency
providers, so Platform never imports the cookbook: the health data eraser
that withdrawing the health data consent runs, the recipe revision step of
the nightly retention purge, and the read and reference rule for recipe
images. It also hands the cookbook the food facts of the reference data.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.reference_data import load_reference_data
from src.cookbook.adapters.inbound.api import deps as cookbook_deps
from src.cookbook.adapters.outbound.persistence.repositories.file_reference_repository import (
    SqlAlchemyFileReferenceRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.household_repository import (
    SqlAlchemyHouseholdRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.mirror_repository import (
    SqlAlchemyMirrorRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.personal_repositories import (
    SqlAlchemyFoodRestrictionRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.recipe_repository import (
    SqlAlchemyRecipeRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.revision_repository import (
    SqlAlchemyRecipeRevisionRepository,
)
from src.cookbook.adapters.outbound.reference.static_food_facts import StaticFoodFactSource
from src.cookbook.application.services.platform_hooks import HealthDataEraser
from src.cookbook.application.services.platform_hooks import RevisionPurger
from src.cookbook.application.services.recipe_file_access import RecipeFileAccess
from src.cookbook.application.services.viewer import ViewerResolver
from src.platform.adapters.inbound.api import deps

_registered = False


def _eraser(db: AsyncSession) -> HealthDataEraser:
    return HealthDataEraser(SqlAlchemyFoodRestrictionRepository(db))


def _revision_purger(db: AsyncSession) -> RevisionPurger:
    return RevisionPurger(SqlAlchemyRecipeRevisionRepository(db))


def recipe_file_access(db: AsyncSession) -> RecipeFileAccess:
    return RecipeFileAccess(
        recipe_repo=SqlAlchemyRecipeRepository(db),
        mirror_repo=SqlAlchemyMirrorRepository(db),
        viewers=ViewerResolver(household_repo=SqlAlchemyHouseholdRepository(db)),
        references=SqlAlchemyFileReferenceRepository(db),
    )


def register_cookbook_hooks() -> None:
    """Idempotent, since tests build the app more than once."""
    global _registered
    if _registered:
        return
    deps.register_health_data_eraser(_eraser)
    deps.register_retention_purger(_revision_purger)
    deps.register_file_access(recipe_file_access)
    cookbook_deps.register_food_fact_source(
        StaticFoodFactSource(lambda: load_reference_data().food_facts)
    )
    _registered = True
