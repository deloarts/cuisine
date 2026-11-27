"""The errors of the cookbook. Each inherits a semantic base from Platform,
which decides its HTTP status."""

from src.platform.domain.exceptions import ConflictError
from src.platform.domain.exceptions import ForbiddenError
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import NotFoundError
from src.platform.domain.exceptions import PermissionDeniedError
from src.platform.domain.exceptions import ServiceUnavailableError


class RecipeNotFoundError(NotFoundError):
    """No recipe with this id, or a draft the caller may not see."""


class IngredientNotFoundError(NotFoundError):
    """No ingredient with this id."""


class UnitNotFoundError(NotFoundError):
    """No unit with this id."""


class TagNotFoundError(NotFoundError):
    """No tag with this id."""


class IngredientCategoryNotFoundError(NotFoundError):
    """No ingredient category with this id."""


class CookEventNotFoundError(NotFoundError):
    """No cook event of the caller with this id."""


class MealPlanEntryNotFoundError(NotFoundError):
    """No meal plan entry of the caller with this id."""


class ShoppingListNotFoundError(NotFoundError):
    """No shopping list with this id that the caller may access."""


class ShoppingListNoteNotFoundError(NotFoundError):
    """No note about a deleted list with this id for the viewer."""


class ShoppingItemNotFoundError(NotFoundError):
    """No item with this id on the list."""


class FoodRestrictionNotFoundError(NotFoundError):
    """No food restriction of the caller with this id."""


class NotOwnerError(PermissionDeniedError):
    """Changing someone else's record needs the manage permission."""


class InvalidRecipeError(InvalidInputError):
    """The recipe breaks a rule, such as missing its original text."""


class InvalidIngredientError(InvalidInputError):
    """The ingredient breaks a rule, such as a negative nutrient."""


class InvalidResourceError(InvalidInputError):
    """A unit, tag or category breaks a rule."""


class DuplicateUnitCodeError(ConflictError):
    """The unit code is already taken."""


class ResourceInUseError(ConflictError):
    """The unit, tag or category is still used and cannot be deleted."""


class IngredientInUseError(ConflictError):
    """The ingredient is used by a recipe and cannot be deleted."""


class InvalidPlanError(InvalidInputError):
    """A meal plan entry, cook event or shopping item breaks a rule."""


class NutritionLookupUnavailableError(ServiceUnavailableError):
    """The USDA lookup is switched off or did not answer."""


class HouseholdNotFoundError(NotFoundError):
    """No household with this id, or the caller does not belong to it."""


class HouseholdInvitationNotFoundError(NotFoundError):
    """No invitation with this id for or from the caller."""


class AlreadyInHouseholdError(ConflictError):
    """The user already belongs to a household; one is the most."""


class NotInHouseholdError(InvalidInputError):
    """The action needs the caller to belong to a household."""


class SubRecipeCycleError(InvalidInputError):
    """A recipe would contain itself through its sub-recipes."""


class SubRecipeTooDeepError(InvalidInputError):
    """Sub-recipes would nest deeper than allowed."""


class RecipeInUseError(ConflictError):
    """Another recipe uses this recipe as a sub-recipe."""


class SeededResourceError(ConflictError):
    """Base ingredients and seeded units belong to the reference catalogue
    and cannot be deleted."""


class IngredientMergeError(InvalidInputError):
    """An ingredient cannot be merged into itself, or into nothing."""


class AccountDeletionChoiceError(InvalidInputError):
    """The owner handover of a deleted account needs another choice."""


class IngredientFamilyNotFoundError(NotFoundError):
    """No ingredient family with this id."""


class DuplicateNameError(ConflictError):
    """A catalogue name is taken in that language. Carries the existing
    entry and its kind (ingredient, family or equipment), so the answer can
    name it and a client knows which catalogue `existing_id` belongs to."""

    def __init__(
        self,
        message: str,
        *,
        existing_id: str,
        existing_name: str,
        existing_kind: str = "ingredient",
    ) -> None:
        super().__init__(message)
        self.extra = {
            "existing_id": existing_id,
            "existing_name": existing_name,
            "existing_kind": existing_kind,
        }


# Kept for readers of the earlier name; aliases follow the same rule.
DuplicateAliasError = DuplicateNameError


class EquipmentNotFoundError(NotFoundError):
    """No equipment with this id."""


class EquipmentInUseError(ConflictError):
    """A recipe step names the equipment, so it can only be merged away."""


class KitchenNotSetUpError(InvalidInputError):
    """The kitchen has to be set up before it can be changed."""


class InvalidMentionError(InvalidRecipeError):
    """A mention in a step's text names nothing among that step's lines or
    equipment. Carries where it is, so the editor can mark it."""

    def __init__(
        self, message: str, *, step: int, locale: str | None, kind: str, target_id: str
    ) -> None:
        super().__init__(message)
        self.extra = {
            "step": step,
            "locale": locale,
            "mention_kind": kind,
            "mention_id": target_id,
        }


class RecipeRevisionNotFoundError(NotFoundError):
    """The recipe has no revision with this number."""


class RevisionRestoreError(ConflictError):
    """A revision names an ingredient, unit, tag, equipment item or
    sub-recipe that no longer exists, so it cannot be restored. Carries
    which one, by kind and the name the revision recorded."""

    def __init__(self, message: str, *, kind: str, name: str) -> None:
        super().__init__(message)
        self.extra = {"missing_kind": kind, "missing_name": name}


class FeatureDisabledError(ForbiddenError):
    """An administrator switched the feature off (households, dinner guests)."""


class LastAdministratorError(ConflictError):
    """The only remaining administrator cannot delete their own account."""


class SelfDeletionConfirmationError(InvalidInputError):
    """Deleting the own account needs the own e-mail address typed and
    either the password or a passkey assertion."""


class RecipeArchiveError(InvalidInputError):
    """A recipe archive cannot be read: not a zip, no manifest, another
    format or version, or too large."""


class CatalogueFileError(InvalidInputError):
    """A catalogue file cannot be read: no JSON, another format, a newer
    version, a malformed document, or too large."""


class VariationNotFoundError(NotFoundError):
    """No variation with this id on this recipe, or a private variation of
    someone else."""


class InvalidVariationError(InvalidInputError):
    """A variation breaks a rule, such as a change naming a step the recipe
    does not have."""


class CoEditorError(InvalidInputError):
    """A co-editor cannot be added: the owner themselves, a service account,
    an inactive account or someone who cannot see the recipe."""


class MirrorReadOnlyError(ConflictError):
    """The recipe, or a variation that came with it, is a mirror of a
    recipe another instance shares with this one; it changes only at its
    source."""


class PeerShareNotAllowedError(InvalidInputError):
    """A recipe cannot go to a paired instance or be made public: it is a
    mirror or a copy of one, the instance does not let users share with that
    peer, or peering is switched off."""


class IncomingRecipeNotFoundError(NotFoundError):
    """No recipe from a paired instance waits for a decision under this id."""


class PeerMappingNotFoundError(NotFoundError):
    """No catalogue mapping of this paired instance for this entry."""


class PeerSuggestionNotFoundError(NotFoundError):
    """The paired instance offers no other value for this field of the
    entry (any more): it holds the same value here, or the peer's value is
    a gap."""


class PeerMappingError(InvalidInputError):
    """The decisions for a recipe from a paired instance are incomplete or
    name something that does not exist. Carries the entries still missing a
    decision."""

    def __init__(self, message: str, *, missing: list[str] | None = None) -> None:
        super().__init__(message)
        self.extra = {"missing": missing or []}
