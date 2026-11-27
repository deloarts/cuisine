"""
The personal layer of a signed-in user: favourites, ratings, private cook
notes and food restrictions. Every action works on the actor's own records
only. Food restrictions are health data: they are read and written only
here, for the actor, and never appear in another user's response, a log
line or the security log.
"""

from dataclasses import dataclass

from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.personal import CookNote
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.entities.personal import Rating
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import FoodRestrictionNotFoundError
from src.cookbook.domain.exceptions import IngredientFamilyNotFoundError
from src.cookbook.domain.exceptions import IngredientNotFoundError
from src.cookbook.domain.exceptions import InvalidPlanError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.exceptions import VariationNotFoundError
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.translations import ui_locale
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import IngredientStatus
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.domain.value_objects.enums import RestrictionKind
from src.cookbook.domain.value_objects.texts import IngredientText
from src.cookbook.ports.outbound.repositories.ingredient_repository import IIngredientRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import ICookNoteRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import IFavouriteRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import (
    IFoodRestrictionRepository,
)
from src.cookbook.ports.outbound.repositories.personal_repositories import IRatingRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.resource_repositories import (
    IIngredientFamilyRepository,
)
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import ConsentRequiredError
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

MAX_NOTE_LENGTH = 10_000
MAX_COMMENT_LENGTH = 2_000


@dataclass(frozen=True)
class RestrictionCommand:
    kind: RestrictionKind
    allergen: Allergen | None = None
    ingredient_id: str | None = None
    # An ingredient by name instead of id; an unknown name becomes a draft
    # ingredient, so anyone can mark an intolerance to "apples".
    ingredient_name: str | None = None
    diet: Diet | None = None
    family_id: str | None = None
    note: str = ""


class ManagePersonal:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        ingredient_repo: IIngredientRepository,
        favourite_repo: IFavouriteRepository,
        rating_repo: IRatingRepository,
        note_repo: ICookNoteRepository,
        restriction_repo: IFoodRestrictionRepository,
        family_repo: IIngredientFamilyRepository,
        variation_repo: IRecipeVariationRepository,
        viewers: ViewerResolver,
        uow: IUnitOfWork,
    ) -> None:
        self._variations = variation_repo
        self._recipes = recipe_repo
        self._ingredients = ingredient_repo
        self._favourites = favourite_repo
        self._ratings = rating_repo
        self._notes = note_repo
        self._restrictions = restriction_repo
        self._viewers = viewers
        self._families = family_repo
        self._uow = uow

    async def _recipe(self, actor: User, public_id: str) -> Recipe:
        recipe = await self._recipes.get_by_public_id(public_id)
        if recipe is None or not can_view_recipe(await self._viewers.of(actor), recipe):
            raise RecipeNotFoundError("No such recipe.")
        return recipe

    # ── Favourites ────────────────────────────────────────────────────

    async def set_favourite(self, actor: User, public_id: str, favourite: bool) -> None:
        recipe = await self._recipe(actor, public_id)
        if favourite:
            await self._favourites.add(actor.id, recipe.id)
        else:
            await self._favourites.remove(actor.id, recipe.id)
        await self._uow.commit()

    # ── Ratings ───────────────────────────────────────────────────────

    async def _variation_id(
        self, actor: User, recipe: Recipe, variation_public_id: str | None
    ) -> int | None:
        """A variation of the recipe the actor may see, or None for the
        recipe itself."""
        if not variation_public_id:
            return None
        variation = await self._variations.get_by_public_id(variation_public_id)
        if (
            variation is None
            or variation.recipe_id != recipe.id
            or not can_view_variation(await self._viewers.of(actor), recipe, variation)
        ):
            raise VariationNotFoundError("No such variation of this recipe.")
        return variation.id

    async def rate(
        self,
        actor: User,
        public_id: str,
        stars: int,
        comment: str = "",
        variation_public_id: str | None = None,
    ) -> Rating:
        """Rates the recipe itself or one of its variations; each user has
        one rating per recipe and one per variation."""
        recipe = await self._recipe(actor, public_id)
        variation_id = await self._variation_id(actor, recipe, variation_public_id)
        if recipe.status is not RecipeStatus.PUBLISHED:
            raise InvalidPlanError("Only published recipes can be rated.")
        if not 1 <= stars <= 5:
            raise InvalidPlanError("A rating has one to five stars.")
        if len(comment) > MAX_COMMENT_LENGTH:
            raise InvalidPlanError("The comment is too long.")
        now = now_utc()
        rating = await self._ratings.get_own(actor.id, recipe.id, variation_id) or Rating(
            user_id=actor.id,
            recipe_id=recipe.id,
            variation_id=variation_id,
            stars=stars,
            created=now,
            changed=now,
        )
        rating.stars = stars
        rating.comment = comment.strip()
        rating.changed = now
        saved = await self._ratings.save(rating)
        await self._uow.commit()
        return saved

    async def unrate(
        self, actor: User, public_id: str, variation_public_id: str | None = None
    ) -> None:
        recipe = await self._recipe(actor, public_id)
        variation_id = await self._variation_id(actor, recipe, variation_public_id)
        rating = await self._ratings.get_own(actor.id, recipe.id, variation_id)
        if rating is not None:
            await self._ratings.delete(rating)
            await self._uow.commit()

    # ── Cook notes ────────────────────────────────────────────────────

    async def save_note(self, actor: User, public_id: str, text: str) -> CookNote | None:
        """Saves the actor's note; an empty text deletes it."""
        recipe = await self._recipe(actor, public_id)
        if len(text) > MAX_NOTE_LENGTH:
            raise InvalidPlanError("The note is too long.")
        note = await self._notes.get_own(actor.id, recipe.id)
        if not text.strip():
            if note is not None:
                await self._notes.delete(note)
                await self._uow.commit()
            return None
        note = note or CookNote(user_id=actor.id, recipe_id=recipe.id, text="", changed=now_utc())
        note.text = text.strip()
        note.changed = now_utc()
        saved = await self._notes.save(note)
        await self._uow.commit()
        return saved

    # ── Food restrictions ─────────────────────────────────────────────

    async def restrictions(self, actor: User) -> list[FoodRestriction]:
        return await self._restrictions.list_for_user(actor.id)

    async def _ingredient_by_name(self, actor: User, name: str) -> Ingredient:
        """The catalogue ingredient called `name` in any language, ignoring
        case, or a new draft ingredient in the actor's language. Creating it
        needs no ingredient permission on this path only: the draft waits
        for review like an agent's and carries nothing but its name."""
        cleaned = name.strip()
        if not cleaned or len(cleaned) > 128:
            raise InvalidPlanError("The ingredient name must have 1 to 128 characters.")
        found = await self._ingredients.find_by_name(cleaned)
        if found is not None:
            return found
        locale = ui_locale(actor.language.value)
        now = now_utc()
        # Owned by nobody, like any ownerless draft, so nothing about it
        # tells that a food restriction made it.
        return await self._ingredients.save(
            Ingredient(
                owner_id=None,
                original_locale=locale,
                created=now,
                changed=now,
                translations={locale: IngredientText(name=cleaned, plural_name=cleaned)},
                status=IngredientStatus.DRAFT,
            )
        )

    async def add_restriction(self, actor: User, cmd: RestrictionCommand) -> FoodRestriction:
        # Restrictions are health data, entered only with the health data
        # consent; withdrawing it deletes them (HealthDataEraser).
        if actor.consent_health_data_at is None:
            raise ConsentRequiredError(
                "Allergies, intolerances and diets need the health data consent."
            )
        named = [
            v
            for v in (cmd.allergen, cmd.ingredient_id, cmd.ingredient_name, cmd.diet, cmd.family_id)
            if v is not None
        ]
        if len(named) != 1:
            raise InvalidPlanError("Name exactly one allergen, ingredient, family or diet.")
        family_id: int | None = None
        if cmd.family_id is not None:
            family = await self._families.get_by_public_id(cmd.family_id)
            if family is None:
                raise IngredientFamilyNotFoundError("No such ingredient family.")
            family_id = family.id
        if (cmd.kind is RestrictionKind.DIET) != (cmd.diet is not None):
            raise InvalidPlanError("A diet restriction names a diet, and only it does.")
        ingredient_id: int | None = None
        if cmd.ingredient_id is not None:
            ingredient = await self._ingredients.get_by_public_id(cmd.ingredient_id)
            if ingredient is None:
                raise IngredientNotFoundError("No such ingredient.")
            ingredient_id = ingredient.id
        elif cmd.ingredient_name is not None:
            ingredient_id = (await self._ingredient_by_name(actor, cmd.ingredient_name)).id
        if len(cmd.note) > 255:
            raise InvalidPlanError("The note is too long.")
        saved = await self._restrictions.save(
            FoodRestriction(
                user_id=actor.id,
                kind=cmd.kind,
                created=now_utc(),
                allergen=cmd.allergen,
                ingredient_id=ingredient_id,
                diet=cmd.diet,
                family_id=family_id,
                note=cmd.note.strip(),
            )
        )
        await self._uow.commit()
        return saved

    async def remove_restriction(self, actor: User, public_id: str) -> None:
        restriction = await self._restrictions.get_own(actor.id, public_id)
        if restriction is None:
            raise FoodRestrictionNotFoundError("No such food restriction.")
        await self._restrictions.delete(restriction)
        await self._uow.commit()
