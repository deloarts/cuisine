"""
Dependency providers of the cookbook: its repositories on the request's
session and the use cases built from them. The Redis live channel and the
USDA lookup are separate providers, so the tests swap them for in-process
fakes.
"""

from fastapi import Depends

from src.cookbook.adapters.outbound.external.live_updates import RedisLivePublisher
from src.cookbook.adapters.outbound.external.usda_nutrition_lookup import UsdaNutritionLookup
from src.cookbook.adapters.outbound.persistence.repositories.cooking_repositories import (
    SqlAlchemyCookEventRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.cooking_repositories import (
    SqlAlchemyMealPlanRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.cooking_repositories import (
    SqlAlchemyShoppingListNoteRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.cooking_repositories import (
    SqlAlchemyShoppingListRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.equipment_repository import (
    SqlAlchemyEquipmentRepository,
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
from src.cookbook.adapters.outbound.persistence.repositories.mirror_repository import (
    SqlAlchemyMirrorRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.personal_repositories import (
    SqlAlchemyCookNoteRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.personal_repositories import (
    SqlAlchemyFavouriteRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.personal_repositories import (
    SqlAlchemyFoodRestrictionRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.personal_repositories import (
    SqlAlchemyRatingRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.recipe_repository import (
    SqlAlchemyRecipeRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyIngredientCategoryRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyIngredientFamilyRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyTagRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.resource_repositories import (
    SqlAlchemyUnitRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.revision_repository import (
    SqlAlchemyRecipeRevisionRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.usage_repository import (
    SqlAlchemyUsageRepository,
)
from src.cookbook.adapters.outbound.persistence.repositories.variation_repository import (
    SqlAlchemyRecipeVariationRepository,
)
from src.cookbook.adapters.outbound.reference.static_food_facts import StaticFoodFactSource
from src.cookbook.application.services.catalogue_fields import CatalogueWriter
from src.cookbook.application.services.lookups import LookupLoader
from src.cookbook.application.services.mirror_builder import MirrorBuilder
from src.cookbook.application.services.mirror_facts import MirrorFacts
from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.application.services.recipe_deletion import RecipeDeletion
from src.cookbook.application.services.revisions import RevisionRecorder
from src.cookbook.application.services.variation_resolver import VariationResolver
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.application.use_cases.accounts.delete_account import DeleteAccountData
from src.cookbook.application.use_cases.accounts.delete_own_account import DeleteOwnAccount
from src.cookbook.application.use_cases.accounts.export_own_data import ExportOwnData
from src.cookbook.application.use_cases.cooking.cook_events import ManageCookEvents
from src.cookbook.application.use_cases.cooking.food_facts import ReadFoodFact
from src.cookbook.application.use_cases.equipment.kitchen import ManageKitchen
from src.cookbook.application.use_cases.equipment.manage_equipment import ManageEquipment
from src.cookbook.application.use_cases.households.manage_households import ManageHouseholds
from src.cookbook.application.use_cases.ingredients.manage_ingredients import ManageIngredients
from src.cookbook.application.use_cases.ingredients.nutrition_lookup import LookupNutrition
from src.cookbook.application.use_cases.mirrors.incoming_recipes import ManageIncomingRecipes
from src.cookbook.application.use_cases.mirrors.peer_suggestions import PeerSuggestions
from src.cookbook.application.use_cases.mirrors.receive_recipes import ReceivePeerRecipes
from src.cookbook.application.use_cases.personal.manage_personal import ManagePersonal
from src.cookbook.application.use_cases.planning.meal_plan import ManageMealPlan
from src.cookbook.application.use_cases.planning.meal_suggestions import SuggestMeals
from src.cookbook.application.use_cases.planning.shopping_lists import ManageShoppingLists
from src.cookbook.application.use_cases.planning.shopping_purge import PurgeShoppingLists
from src.cookbook.application.use_cases.recipes.manage_recipes import ManageRecipes
from src.cookbook.application.use_cases.recipes.manage_variations import ManageVariations
from src.cookbook.application.use_cases.recipes.read_public_recipes import ReadPublicRecipes
from src.cookbook.application.use_cases.recipes.read_recipes import ReadRecipes
from src.cookbook.application.use_cases.recipes.recipe_archive import RecipeArchive
from src.cookbook.application.use_cases.resources.catalogue_file import CatalogueFile
from src.cookbook.application.use_cases.resources.manage_resources import ManageResources
from src.cookbook.application.use_cases.resources.resource_usage import ReadResourceUsage
from src.cookbook.ports.outbound.food_fact_source import IFoodFactSource
from src.cookbook.ports.outbound.live_publisher import ILiveChannel
from src.cookbook.ports.outbound.live_publisher import ILivePublisher
from src.cookbook.ports.outbound.nutrition_lookup import INutritionLookup
from src.platform.adapters.inbound.api import deps as platform_deps
from src.platform.adapters.inbound.api.deps import Platform
from src.platform.adapters.inbound.api.deps import get_platform
from src.platform.infrastructure.redis_client import get_redis
from src.platform.ports.outbound.replay_guard import IReplayGuard


class Cookbook:
    """The cookbook repositories of one request, on the request's session,
    next to Platform's."""

    def __init__(self, p: Platform) -> None:
        db = p.db
        self.platform = p
        self.uow = p.uow
        self.units = SqlAlchemyUnitRepository(db)
        self.tags = SqlAlchemyTagRepository(db)
        self.categories = SqlAlchemyIngredientCategoryRepository(db)
        self.families = SqlAlchemyIngredientFamilyRepository(db)
        self.ingredients = SqlAlchemyIngredientRepository(db)
        self.recipes = SqlAlchemyRecipeRepository(db)
        self.favourites = SqlAlchemyFavouriteRepository(db)
        self.ratings = SqlAlchemyRatingRepository(db)
        self.notes = SqlAlchemyCookNoteRepository(db)
        self.restrictions = SqlAlchemyFoodRestrictionRepository(db)
        self.cook_events = SqlAlchemyCookEventRepository(db)
        self.meal_plan = SqlAlchemyMealPlanRepository(db)
        self.shopping_lists = SqlAlchemyShoppingListRepository(db)
        self.shopping_notes = SqlAlchemyShoppingListNoteRepository(db)
        self.households = SqlAlchemyHouseholdRepository(db)
        self.equipment = SqlAlchemyEquipmentRepository(db)
        self.kitchens = SqlAlchemyKitchenRepository(db)
        self.revisions = SqlAlchemyRecipeRevisionRepository(db)
        self.variations = SqlAlchemyRecipeVariationRepository(db)
        self.mirrors = SqlAlchemyMirrorRepository(db)
        self.usage = SqlAlchemyUsageRepository(db)
        # One resolver per request, so the viewer is built once.
        self.viewers = ViewerResolver(household_repo=self.households)

    def lookups(self) -> LookupLoader:
        return LookupLoader(
            unit_repo=self.units,
            tag_repo=self.tags,
            category_repo=self.categories,
            ingredient_repo=self.ingredients,
            recipe_repo=self.recipes,
            family_repo=self.families,
            equipment_repo=self.equipment,
        )

    def revision_recorder(self) -> RevisionRecorder:
        return RevisionRecorder(
            revision_repo=self.revisions,
            recipe_repo=self.recipes,
            ingredient_repo=self.ingredients,
            equipment_repo=self.equipment,
            unit_repo=self.units,
            tag_repo=self.tags,
            file_repo=self.platform.files,
        )

    def variation_resolver(self) -> VariationResolver:
        return VariationResolver(
            ingredient_repo=self.ingredients,
            unit_repo=self.units,
            equipment_repo=self.equipment,
            recipe_repo=self.recipes,
        )

    def sharing(self) -> PeerRecipeSharing:
        return PeerRecipeSharing(
            recipe_repo=self.recipes,
            variation_repo=self.variations,
            ingredient_repo=self.ingredients,
            equipment_repo=self.equipment,
            unit_repo=self.units,
            tag_repo=self.tags,
            category_repo=self.categories,
            family_repo=self.families,
            user_repo=self.platform.users,
            settings_repo=self.platform.settings,
            peer_repo=self.platform.peers,
            file_repo=self.platform.files,
            revisions=self.revision_recorder(),
            publisher=self.platform.peer_channel,
        )

    def facts(self) -> MirrorFacts:
        return MirrorFacts(mirror_repo=self.mirrors, peer_repo=self.platform.peers)

    def deletion(self) -> RecipeDeletion:
        return RecipeDeletion(
            recipe_repo=self.recipes,
            file_repo=self.platform.files,
            events=self.platform.webhooks,
            sharing=self.sharing(),
        )

    def kitchen(self) -> ManageKitchen:
        return ManageKitchen(
            kitchen_repo=self.kitchens,
            equipment_repo=self.equipment,
            viewers=self.viewers,
            uow=self.uow,
        )


def get_cookbook(p: Platform = Depends(get_platform)) -> Cookbook:
    return Cookbook(p)


# ── Swappable adapters ───────────────────────────────────────────────


def get_live() -> ILiveChannel:
    """Publishes and subscribes to live updates. The tests swap it for the
    in-memory variant, which has the same two methods."""
    return RedisLivePublisher(get_redis())


def get_nutrition_lookup() -> INutritionLookup:
    return UsdaNutritionLookup()


_food_facts: IFoodFactSource = StaticFoodFactSource(tuple)


def register_food_fact_source(source: IFoodFactSource) -> None:
    """The composition root hands over the facts of the reference data."""
    global _food_facts
    _food_facts = source


def get_food_fact_source() -> IFoodFactSource:
    return _food_facts


# ── Use cases ────────────────────────────────────────────────────────


def get_read_resource_usage(c: Cookbook = Depends(get_cookbook)) -> ReadResourceUsage:
    return ReadResourceUsage(usage_repo=c.usage, viewers=c.viewers)


def get_manage_resources(c: Cookbook = Depends(get_cookbook)) -> ManageResources:
    return manage_resources(c)


def manage_resources(c: Cookbook) -> ManageResources:
    return ManageResources(
        unit_repo=c.units,
        tag_repo=c.tags,
        category_repo=c.categories,
        family_repo=c.families,
        ingredient_repo=c.ingredients,
        uow=c.uow,
        mirror_repo=c.mirrors,
    )


def get_manage_ingredients(c: Cookbook = Depends(get_cookbook)) -> ManageIngredients:
    return manage_ingredients(c)


def manage_ingredients(c: Cookbook) -> ManageIngredients:
    return ManageIngredients(
        ingredient_repo=c.ingredients,
        unit_repo=c.units,
        category_repo=c.categories,
        family_repo=c.families,
        uow=c.uow,
        mirror_repo=c.mirrors,
    )


def get_lookup_nutrition(
    c: Cookbook = Depends(get_cookbook), lookup: INutritionLookup = Depends(get_nutrition_lookup)
) -> LookupNutrition:
    return LookupNutrition(settings_repo=c.platform.settings, lookup=lookup)


def get_manage_recipes(c: Cookbook = Depends(get_cookbook)) -> ManageRecipes:
    return manage_recipes(c)


def manage_recipes(c: Cookbook) -> ManageRecipes:
    return ManageRecipes(
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        unit_repo=c.units,
        tag_repo=c.tags,
        file_repo=c.platform.files,
        settings_repo=c.platform.settings,
        user_repo=c.platform.users,
        group_repo=c.platform.groups,
        viewers=c.viewers,
        revisions=c.revision_recorder(),
        revision_repo=c.revisions,
        uow=c.uow,
        events=c.platform.webhooks,
        sharing=c.sharing(),
        peer_repo=c.platform.peers,
        mirror_repo=c.mirrors,
        file_access=platform_deps.file_access(c.platform),
    )


def get_read_recipes(c: Cookbook = Depends(get_cookbook)) -> ReadRecipes:
    return ReadRecipes(
        recipe_repo=c.recipes,
        favourite_repo=c.favourites,
        rating_repo=c.ratings,
        note_repo=c.notes,
        restriction_repo=c.restrictions,
        cook_event_repo=c.cook_events,
        user_repo=c.platform.users,
        lookups=c.lookups(),
        viewers=c.viewers,
        kitchen=c.kitchen(),
        features=c.platform.settings,
        variation_repo=c.variations,
        variation_resolver=c.variation_resolver(),
        facts=c.facts(),
    )


def get_read_public_recipes(c: Cookbook = Depends(get_cookbook)) -> ReadPublicRecipes:
    return ReadPublicRecipes(
        recipe_repo=c.recipes,
        tag_repo=c.tags,
        user_repo=c.platform.users,
        settings_repo=c.platform.settings,
        file_repo=c.platform.files,
        lookups=c.lookups(),
    )


def get_manage_variations(c: Cookbook = Depends(get_cookbook)) -> ManageVariations:
    return manage_variations(c)


def manage_variations(c: Cookbook) -> ManageVariations:
    return ManageVariations(
        variation_repo=c.variations,
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        rating_repo=c.ratings,
        revision_repo=c.revisions,
        revisions=c.revision_recorder(),
        resolver=c.variation_resolver(),
        viewers=c.viewers,
        uow=c.uow,
        sharing=c.sharing(),
    )


def get_manage_equipment(c: Cookbook = Depends(get_cookbook)) -> ManageEquipment:
    return manage_equipment(c)


def manage_equipment(c: Cookbook) -> ManageEquipment:
    return ManageEquipment(
        equipment_repo=c.equipment,
        ingredient_repo=c.ingredients,
        recipe_repo=c.recipes,
        uow=c.uow,
        mirror_repo=c.mirrors,
    )


def get_manage_kitchen(c: Cookbook = Depends(get_cookbook)) -> ManageKitchen:
    return c.kitchen()


def get_manage_personal(c: Cookbook = Depends(get_cookbook)) -> ManagePersonal:
    return ManagePersonal(
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        favourite_repo=c.favourites,
        rating_repo=c.ratings,
        note_repo=c.notes,
        restriction_repo=c.restrictions,
        family_repo=c.families,
        variation_repo=c.variations,
        viewers=c.viewers,
        uow=c.uow,
    )


def get_manage_cook_events(c: Cookbook = Depends(get_cookbook)) -> ManageCookEvents:
    return ManageCookEvents(
        cook_event_repo=c.cook_events,
        recipe_repo=c.recipes,
        variation_repo=c.variations,
        viewers=c.viewers,
        uow=c.uow,
    )


def get_read_food_fact(
    c: Cookbook = Depends(get_cookbook), source: IFoodFactSource = Depends(get_food_fact_source)
) -> ReadFoodFact:
    return ReadFoodFact(source=source, ingredient_repo=c.ingredients)


def get_manage_shopping_lists(
    c: Cookbook = Depends(get_cookbook), live: ILiveChannel = Depends(get_live)
) -> ManageShoppingLists:
    return ManageShoppingLists(
        list_repo=c.shopping_lists,
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        unit_repo=c.units,
        user_repo=c.platform.users,
        restriction_repo=c.restrictions,
        note_repo=c.shopping_notes,
        settings_repo=c.platform.settings,
        lookups=c.lookups(),
        live=live,
        viewers=c.viewers,
        uow=c.uow,
        mirror_repo=c.mirrors,
    )


def shopping_purge(c: Cookbook, live: ILivePublisher) -> PurgeShoppingLists:
    """The purge the background job runs; built outside a request."""
    return PurgeShoppingLists(
        list_repo=c.shopping_lists,
        note_repo=c.shopping_notes,
        settings_repo=c.platform.settings,
        live=live,
        uow=c.uow,
    )


def get_manage_meal_plan(
    c: Cookbook = Depends(get_cookbook),
    shopping: ManageShoppingLists = Depends(get_manage_shopping_lists),
) -> ManageMealPlan:
    return ManageMealPlan(
        meal_plan_repo=c.meal_plan,
        recipe_repo=c.recipes,
        shopping=shopping,
        viewers=c.viewers,
        uow=c.uow,
    )


def get_suggest_meals(
    c: Cookbook = Depends(get_cookbook),
    meal_plan: ManageMealPlan = Depends(get_manage_meal_plan),
    read_recipes: ReadRecipes = Depends(get_read_recipes),
) -> SuggestMeals:
    return SuggestMeals(
        meal_plan=meal_plan,
        read_recipes=read_recipes,
        cook_event_repo=c.cook_events,
        viewers=c.viewers,
    )


def get_delete_account_data(c: Cookbook = Depends(get_cookbook)) -> DeleteAccountData:
    return _delete_account_data(c)


def _delete_account_data(c: Cookbook) -> DeleteAccountData:
    return DeleteAccountData(
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        household_repo=c.households,
        list_repo=c.shopping_lists,
        meal_plan_repo=c.meal_plan,
        user_repo=c.platform.users,
        deletion=c.deletion(),
        variation_repo=c.variations,
        sharing=c.sharing(),
    )


def get_manage_households(c: Cookbook = Depends(get_cookbook)) -> ManageHouseholds:
    return ManageHouseholds(
        household_repo=c.households,
        list_repo=c.shopping_lists,
        user_repo=c.platform.users,
        uow=c.uow,
        features=c.platform.settings,
    )


def get_delete_own_account(
    c: Cookbook = Depends(get_cookbook),
    replay: IReplayGuard = Depends(platform_deps.get_replay_guard),
) -> DeleteOwnAccount:
    return DeleteOwnAccount(
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        household_repo=c.households,
        account_data=_delete_account_data(c),
        deletion=c.deletion(),
        user_repo=c.platform.users,
        api_key_repo=c.platform.api_keys,
        security_event_repo=c.platform.security_events,
        passkey_repo=c.platform.passkeys,
        settings_repo=c.platform.settings,
        file_repo=c.platform.files,
        hasher=platform_deps.hasher(),
        verifier=platform_deps.passkey_verifier(),
        tokens=platform_deps.tokens(),
        replay=replay,
        facts=platform_deps.get_instance_facts(),
        uow=c.uow,
        events=c.platform.webhooks,
    )


def get_export_own_data(c: Cookbook = Depends(get_cookbook)) -> ExportOwnData:
    return ExportOwnData(
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        unit_repo=c.units,
        family_repo=c.families,
        favourite_repo=c.favourites,
        rating_repo=c.ratings,
        note_repo=c.notes,
        restriction_repo=c.restrictions,
        cook_event_repo=c.cook_events,
        meal_plan_repo=c.meal_plan,
        list_repo=c.shopping_lists,
        household_repo=c.households,
        user_repo=c.platform.users,
        revisions=c.revision_recorder(),
        kitchen=c.kitchen(),
        viewers=c.viewers,
        variation_repo=c.variations,
    )


def get_recipe_archive(
    c: Cookbook = Depends(get_cookbook),
    recipes: ManageRecipes = Depends(get_manage_recipes),
    ingredients: ManageIngredients = Depends(get_manage_ingredients),
    equipment: ManageEquipment = Depends(get_manage_equipment),
    variations: ManageVariations = Depends(get_manage_variations),
) -> RecipeArchive:
    return RecipeArchive(
        recipe_repo=c.recipes,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        unit_repo=c.units,
        tag_repo=c.tags,
        category_repo=c.categories,
        family_repo=c.families,
        variation_repo=c.variations,
        user_repo=c.platform.users,
        settings_repo=c.platform.settings,
        file_repo=c.platform.files,
        images=platform_deps.image_processor(),
        recipes=recipes,
        ingredients=ingredients,
        equipment=equipment,
        variations=variations,
        revisions=c.revision_recorder(),
        viewers=c.viewers,
        uow=c.uow,
    )


def get_catalogue_file(
    c: Cookbook = Depends(get_cookbook),
    resources: ManageResources = Depends(get_manage_resources),
    ingredients: ManageIngredients = Depends(get_manage_ingredients),
    equipment: ManageEquipment = Depends(get_manage_equipment),
) -> CatalogueFile:
    return CatalogueFile(
        unit_repo=c.units,
        tag_repo=c.tags,
        category_repo=c.categories,
        family_repo=c.families,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        settings_repo=c.platform.settings,
        resources=resources,
        ingredients=ingredients,
        equipment=equipment,
        uow=c.uow,
    )


# ── Mirrors of recipes from paired instances ─────────────────────────


def mirror_builder(c: Cookbook) -> MirrorBuilder:
    return MirrorBuilder(
        recipe_repo=c.recipes,
        mirror_repo=c.mirrors,
        variation_repo=c.variations,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        unit_repo=c.units,
        tag_repo=c.tags,
        category_repo=c.categories,
        family_repo=c.families,
        file_repo=c.platform.files,
        images=platform_deps.image_processor(),
        recipes=manage_recipes(c),
        variations=manage_variations(c),
        ingredients=manage_ingredients(c),
        equipment=manage_equipment(c),
        resources=manage_resources(c),
        peer_repo=c.platform.peers,
    )


def receive_peer_recipes(c: Cookbook) -> ReceivePeerRecipes:
    """The `recipe` consumer of the peer channel and the peer hooks, built
    on the session of the job or request that runs them."""
    return ReceivePeerRecipes(
        mirror_repo=c.mirrors,
        recipe_repo=c.recipes,
        builder=mirror_builder(c),
        sharing=c.sharing(),
    )


def get_manage_incoming_recipes(c: Cookbook = Depends(get_cookbook)) -> ManageIncomingRecipes:
    return ManageIncomingRecipes(
        mirror_repo=c.mirrors,
        recipe_repo=c.recipes,
        peer_repo=c.platform.peers,
        unit_repo=c.units,
        tag_repo=c.tags,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        builder=mirror_builder(c),
        uow=c.uow,
    )


def get_peer_suggestions(
    c: Cookbook = Depends(get_cookbook),
    resources: ManageResources = Depends(get_manage_resources),
    ingredients: ManageIngredients = Depends(get_manage_ingredients),
    equipment: ManageEquipment = Depends(get_manage_equipment),
) -> PeerSuggestions:
    return PeerSuggestions(
        peer_repo=c.platform.peers,
        mirror_repo=c.mirrors,
        unit_repo=c.units,
        tag_repo=c.tags,
        category_repo=c.categories,
        family_repo=c.families,
        ingredient_repo=c.ingredients,
        equipment_repo=c.equipment,
        writer=CatalogueWriter(resources=resources, ingredients=ingredients, equipment=equipment),
        uow=c.uow,
    )
