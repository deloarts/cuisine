"""Every cookbook ORM model, imported here so Alembic's metadata sees them
through src/bootstrap/models.py."""

from src.cookbook.adapters.outbound.persistence.models.cooking_models import CookEventModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import MealPlanEntryModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingItemModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingListMemberModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingListModel
from src.cookbook.adapters.outbound.persistence.models.cooking_models import ShoppingListNoteModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import EquipmentAliasModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import EquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import (
    EquipmentTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.equipment_models import KitchenEquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import KitchenModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import StepEquipmentModel
from src.cookbook.adapters.outbound.persistence.models.equipment_models import (
    StepEquipmentTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.household_models import (
    HouseholdInvitationModel,
)
from src.cookbook.adapters.outbound.persistence.models.household_models import HouseholdMemberModel
from src.cookbook.adapters.outbound.persistence.models.household_models import HouseholdModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientAliasModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import (
    IngredientConversionModel,
)
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import IngredientModel
from src.cookbook.adapters.outbound.persistence.models.ingredient_models import (
    IngredientTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.mirror_models import IncomingRecipeModel
from src.cookbook.adapters.outbound.persistence.models.mirror_models import (
    PeerCatalogueMappingModel,
)
from src.cookbook.adapters.outbound.persistence.models.mirror_models import (
    PeerSuggestionDismissalModel,
)
from src.cookbook.adapters.outbound.persistence.models.mirror_models import RecipeMirrorModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import FoodRestrictionModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeFavouriteModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeNoteModel
from src.cookbook.adapters.outbound.persistence.models.personal_models import RecipeRatingModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeCoEditorModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeGroupShareModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import (
    RecipeIngredientTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipePeerShareModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeStepModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import (
    RecipeStepTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeTagModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeTranslationModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import RecipeUserShareModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import StepIngredientModel
from src.cookbook.adapters.outbound.persistence.models.recipe_models import (
    StepIngredientTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientCategoryModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientCategoryTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import IngredientFamilyModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import (
    IngredientFamilyTranslationModel,
)
from src.cookbook.adapters.outbound.persistence.models.resource_models import SeededKeyModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import TagModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import TagTranslationModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import UnitModel
from src.cookbook.adapters.outbound.persistence.models.resource_models import UnitTranslationModel
from src.cookbook.adapters.outbound.persistence.models.revision_models import RecipeRevisionModel
from src.cookbook.adapters.outbound.persistence.models.variation_models import RecipeVariationModel

__all__ = [
    "CookEventModel",
    "EquipmentAliasModel",
    "EquipmentModel",
    "EquipmentTranslationModel",
    "FoodRestrictionModel",
    "HouseholdInvitationModel",
    "HouseholdMemberModel",
    "HouseholdModel",
    "IncomingRecipeModel",
    "IngredientAliasModel",
    "IngredientCategoryModel",
    "IngredientCategoryTranslationModel",
    "IngredientConversionModel",
    "IngredientFamilyModel",
    "IngredientFamilyTranslationModel",
    "IngredientModel",
    "IngredientTranslationModel",
    "KitchenEquipmentModel",
    "KitchenModel",
    "MealPlanEntryModel",
    "PeerCatalogueMappingModel",
    "PeerSuggestionDismissalModel",
    "RecipeCoEditorModel",
    "RecipeFavouriteModel",
    "RecipeGroupShareModel",
    "RecipeIngredientModel",
    "RecipeIngredientTranslationModel",
    "RecipeMirrorModel",
    "RecipeModel",
    "RecipeNoteModel",
    "RecipePeerShareModel",
    "RecipeRatingModel",
    "RecipeRevisionModel",
    "RecipeStepModel",
    "RecipeStepTranslationModel",
    "RecipeTagModel",
    "RecipeTranslationModel",
    "RecipeUserShareModel",
    "RecipeVariationModel",
    "SeededKeyModel",
    "ShoppingItemModel",
    "ShoppingListMemberModel",
    "ShoppingListModel",
    "ShoppingListNoteModel",
    "StepEquipmentModel",
    "StepEquipmentTranslationModel",
    "StepIngredientModel",
    "StepIngredientTranslationModel",
    "TagModel",
    "TagTranslationModel",
    "UnitModel",
    "UnitTranslationModel",
]
