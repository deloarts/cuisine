"""
Registers the cookbook's tables and read rules with Platform's public id
resolver, so Platform never imports the cookbook. A step, an ingredient or
equipment line, a revision and a personal note or rating resolve to their
recipe; a shopping item resolves to its list. Notes and ratings are
personal records and resolve for their owner only. Units, tags, categories,
families, equipment, cook events, meal plan entries, food restrictions and
every Platform table are not registered, since they have no page of their
own or must never be reachable this way, and answer 404.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingItemModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingListModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import KitchenModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import StepEquipmentModel
from src.cookbook.adapters.outbound.persistence.models.household_models import HouseholdModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeNoteModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeRatingModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeStepModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import StepIngredientModel
from src.cookbook.adapters.outbound.persistence.models.revision_models import RecipeRevisionModel
from src.cookbook.adapters.outbound.persistence.models.variation_models import RecipeVariationModel
from src.cookbook.adapters.outbound.persistence.repositories.cooking_repositories import (
    SqlAlchemyShoppingListRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.equipment_repository import (
    SqlAlchemyKitchenRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.household_repository import (
    SqlAlchemyHouseholdRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.ingredient_repository import (
    SqlAlchemyIngredientRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.recipe_repository import (
    SqlAlchemyRecipeRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.variation_repository import (
    SqlAlchemyRecipeVariationRepository,
)
from src.cookbook.application.services.public_id_access import HouseholdAccess
from src.cookbook.application.services.public_id_access import IngredientAccess
from src.cookbook.application.services.public_id_access import KitchenAccess
from src.cookbook.application.services.public_id_access import RecipeAccess
from src.cookbook.application.services.public_id_access import ShoppingListAccess
from src.cookbook.application.services.public_id_access import VariationAccess
from src.cookbook.application.services.viewer import ViewerResolver
from src.platform.adapters.inbound.api import deps
from src.platform.adapters.outbound.persistence.public_id_lookup import PublicIdSource
from src.platform.adapters.outbound.persistence.public_id_lookup import register_public_id_sources

RECIPE, VARIATION, INGREDIENT = "recipe", "variation", "ingredient"
SHOPPING_LIST, KITCHEN, HOUSEHOLD = "shopping_list", "kitchen", "household"

_to_recipe_via_step = (
    (RecipeStepModel, RecipeStepModel.id == StepIngredientModel.step_id),
    (RecipeModel, RecipeModel.id == RecipeStepModel.recipe_id),
)

SOURCES = [
    PublicIdSource(RecipeModel, RECIPE),
    PublicIdSource(
        RecipeStepModel,
        RECIPE,
        target=RecipeModel.public_id,
        joins=((RecipeModel, RecipeModel.id == RecipeStepModel.recipe_id),),
    ),
    PublicIdSource(
        StepIngredientModel, RECIPE, target=RecipeModel.public_id, joins=_to_recipe_via_step
    ),
    PublicIdSource(
        RecipeIngredientModel,
        RECIPE,
        target=RecipeModel.public_id,
        joins=((RecipeModel, RecipeModel.id == RecipeIngredientModel.recipe_id),),
    ),
    PublicIdSource(
        StepEquipmentModel,
        RECIPE,
        target=RecipeModel.public_id,
        joins=(
            (RecipeStepModel, RecipeStepModel.id == StepEquipmentModel.step_id),
            (RecipeModel, RecipeModel.id == RecipeStepModel.recipe_id),
        ),
    ),
    PublicIdSource(
        RecipeRevisionModel,
        RECIPE,
        target=RecipeModel.public_id,
        joins=((RecipeModel, RecipeModel.id == RecipeRevisionModel.recipe_id),),
    ),
    PublicIdSource(
        RecipeNoteModel,
        RECIPE,
        target=RecipeModel.public_id,
        joins=((RecipeModel, RecipeModel.id == RecipeNoteModel.recipe_id),),
        owner=RecipeNoteModel.user_id,
    ),
    PublicIdSource(
        RecipeRatingModel,
        RECIPE,
        target=RecipeModel.public_id,
        joins=((RecipeModel, RecipeModel.id == RecipeRatingModel.recipe_id),),
        owner=RecipeRatingModel.user_id,
    ),
    PublicIdSource(RecipeVariationModel, VARIATION),
    PublicIdSource(IngredientModel, INGREDIENT),
    PublicIdSource(ShoppingListModel, SHOPPING_LIST),
    PublicIdSource(
        ShoppingItemModel,
        SHOPPING_LIST,
        target=ShoppingListModel.public_id,
        joins=((ShoppingListModel, ShoppingListModel.id == ShoppingItemModel.list_id),),
    ),
    PublicIdSource(KitchenModel, KITCHEN),
    PublicIdSource(HouseholdModel, HOUSEHOLD),
]


def _viewers(db: AsyncSession) -> ViewerResolver:
    return ViewerResolver(household_repo=SqlAlchemyHouseholdRepository(db))


def _recipe(db: AsyncSession) -> RecipeAccess:
    return RecipeAccess(recipe_repo=SqlAlchemyRecipeRepository(db), viewers=_viewers(db))


def _variation(db: AsyncSession) -> VariationAccess:
    return VariationAccess(
        variation_repo=SqlAlchemyRecipeVariationRepository(db),
        recipe_repo=SqlAlchemyRecipeRepository(db),
        viewers=_viewers(db),
    )


def _ingredient(db: AsyncSession) -> IngredientAccess:
    return IngredientAccess(ingredient_repo=SqlAlchemyIngredientRepository(db))


def _shopping_list(db: AsyncSession) -> ShoppingListAccess:
    return ShoppingListAccess(list_repo=SqlAlchemyShoppingListRepository(db), viewers=_viewers(db))


def _kitchen(db: AsyncSession) -> KitchenAccess:
    return KitchenAccess(kitchen_repo=SqlAlchemyKitchenRepository(db), viewers=_viewers(db))


def _household(db: AsyncSession) -> HouseholdAccess:
    return HouseholdAccess(household_repo=SqlAlchemyHouseholdRepository(db))


def register_cookbook_public_ids() -> None:
    """Idempotent, since tests build the app more than once."""
    register_public_id_sources(SOURCES)
    deps.register_public_id_access(RECIPE, _recipe)
    deps.register_public_id_access(VARIATION, _variation)
    deps.register_public_id_access(INGREDIENT, _ingredient)
    deps.register_public_id_access(SHOPPING_LIST, _shopping_list)
    deps.register_public_id_access(KITCHEN, _kitchen)
    deps.register_public_id_access(HOUSEHOLD, _household)
