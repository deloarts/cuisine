"""The fixed vocabularies of the cookbook. The values are stored and sent
as they are; the UI translates them through its locale files."""

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class ContentLocale(StrValueEnum):
    """The languages recipe and resource text is written in, as BCP 47
    tags. The UI languages are the same two."""

    DE_AT = "de-AT"
    EN_GB = "en-GB"


class Allergen(StrValueEnum):
    """The 14 allergens EU food law requires to be declared."""

    GLUTEN = "gluten"
    CRUSTACEANS = "crustaceans"
    EGGS = "eggs"
    FISH = "fish"
    PEANUTS = "peanuts"
    SOYBEANS = "soybeans"
    MILK = "milk"
    NUTS = "nuts"
    CELERY = "celery"
    MUSTARD = "mustard"
    SESAME = "sesame"
    SULPHITES = "sulphites"
    LUPIN = "lupin"
    MOLLUSCS = "molluscs"


class UnitKind(StrValueEnum):
    # Converted to grams by the unit's factor.
    MASS = "mass"
    # Converted to millilitres by the unit's factor, then to grams by the
    # ingredient's density.
    VOLUME = "volume"
    # Pieces, cloves, slices: converted to grams only through a conversion
    # the ingredient defines.
    COUNT = "count"
    OTHER = "other"


class TagKind(StrValueEnum):
    """Diets are no tag kind: they are derived from the ingredients' diet
    markers."""

    MEAL = "meal"
    CUISINE = "cuisine"
    OCCASION = "occasion"
    OTHER = "other"


class Difficulty(StrValueEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RecipeVisibility(StrValueEnum):
    """Who may read a published recipe besides its owner, narrowest first. A
    draft is always its owner's alone."""

    PRIVATE = "private"
    # The members of the owner's household.
    HOUSEHOLD = "household"
    # The users and groups the owner chose.
    SHARED = "shared"
    # Every signed-in user of this instance.
    INSTANCE = "instance"
    # Every signed-in user of this instance and every paired instance that
    # users may share with, but only while peering is on; otherwise it reads
    # as INSTANCE (`recipe_rules.effective_visibility`).
    PEERS = "peers"
    # Anyone, signed in or not, and every paired instance, but only while the
    # instance allows public recipes; otherwise it reads as INSTANCE
    # (`recipe_rules.effective_visibility`).
    PUBLIC = "public"


class RecipeStatus(StrValueEnum):
    # Visible to its owner and to manage:recipes only.
    DRAFT = "draft"
    PUBLISHED = "published"


class IngredientStatus(StrValueEnum):
    # Created by an agent and waiting for a person to review it. Usable in
    # recipes already, and listed with a marker.
    DRAFT = "draft"
    ACTIVE = "active"
    # Deleted while food restrictions still pointed at it: gone from the
    # catalogue, pickers and every response, still matched for the
    # warnings of those users. Indistinguishable from a deletion.
    ARCHIVED = "archived"


class CreatedVia(StrValueEnum):
    WEB = "web"
    MCP = "mcp"
    # A mirror built from a paired instance's recipe.
    PEER = "peer"


class NutritionSource(StrValueEnum):
    MANUAL = "manual"
    USDA = "usda"


class MealSlot(StrValueEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MealPlanScope(StrValueEnum):
    """Which plan a request means: the household's, which every member
    shares, or the caller's personal one, which only they see."""

    HOUSEHOLD = "household"
    PERSONAL = "personal"


class SuggestionReason(StrValueEnum):
    """Why the meal plan suggests a recipe: the signal that weighed most in
    its score (`meal_suggestions.score`)."""

    OFTEN_COOKED = "often_cooked"
    NOT_COOKED_LATELY = "not_cooked_lately"
    FAVOURITE = "favourite"
    IN_SEASON = "in_season"
    COOKED_THIS_TIME_LAST_YEAR = "cooked_this_time_last_year"
    FITS_SLOT = "fits_slot"
    NEW_RECIPE = "new_recipe"
    NOT_COOKED_YET = "not_cooked_yet"
    COOKED_BEFORE = "cooked_before"


class RestrictionKind(StrValueEnum):
    ALLERGY = "allergy"
    INTOLERANCE = "intolerance"
    DIET = "diet"


class Diet(StrValueEnum):
    """The diets a user may follow. Which ingredients break them is decided
    by the ingredients' diet markers (services/diet_rules.py)."""

    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    PESCETARIAN = "pescetarian"
    HALAL = "halal"
    NO_PORK = "no_pork"
    NO_BEEF = "no_beef"
    NO_ALCOHOL = "no_alcohol"


class DietMarker(StrValueEnum):
    """What an ingredient is or contains, as far as diets care."""

    MEAT = "meat"
    POULTRY = "poultry"
    PORK = "pork"
    BEEF = "beef"
    FISH = "fish"
    SEAFOOD = "seafood"
    GELATIN = "gelatin"
    DAIRY = "dairy"
    EGGS = "eggs"
    HONEY = "honey"
    ALCOHOL = "alcohol"


class EquipmentKind(StrValueEnum):
    COOKWARE = "cookware"
    BAKEWARE = "bakeware"
    APPLIANCE = "appliance"
    UTENSIL = "utensil"


class EquipmentStatus(StrValueEnum):
    # Created by an agent for a recipe draft and waiting for a person with
    # write:resources to review it; usable in recipes already.
    DRAFT = "draft"
    ACTIVE = "active"


class RevisionKind(StrValueEnum):
    """What a recipe revision recorded."""

    CREATED = "created"
    UPDATED = "updated"
    TRANSLATED = "translated"
    IMAGE_ATTACHED = "image_attached"
    RESTORED = "restored"
    # An editor took over changes of a variation; the revision credits the
    # variation's author.
    ADOPTED = "adopted"


class VariationChangeKind(StrValueEnum):
    """One difference a recipe variation makes to the original."""

    # Another ingredient instead of one, in one step or in the whole recipe.
    SWAP = "swap"
    # An extra line in a step.
    ADD_LINE = "add_line"
    # A line of a step left out.
    REMOVE_LINE = "remove_line"
    # Another text for a step.
    STEP_TEXT = "step_text"
    # A new step after a given step, with its own lines and equipment.
    EXTRA_STEP = "extra_step"


class ShoppingListMode(StrValueEnum):
    """How a shopping list treats what was bought and how long it lives."""

    # Kept for good: ticked items stay under "Recently bought" for a window
    # the administrator sets, then they are deleted.
    CONTINUOUS = "continuous"
    # Kept with every item until nobody has used it for the idle days the
    # administrator sets; then the list deletes itself unless kept.
    NORMAL = "normal"
