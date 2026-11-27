"""
Reading recipes: the browse list with what a card needs, and one recipe with
everything derived for the viewer: the ingredient list for the wanted
servings, nutrition, allergens, the diets it fits, the viewer's own food
restriction warnings, favourite, own rating and note, when it was last
cooked, the months it is in season (`in_season` is for the current month)
and, once the viewer's kitchen is set up, the equipment it lacks. The
kitchen never enters the dinner guest check.

Variations count for the guests and diets filters: a recipe that conflicts
with a guest, or misses a wanted diet, is still listed (and flagged
`variation_fits_guests` or `variation_fits_diets`) when a variation the
viewer may see fits.

Dinner guests: the viewer may name users who are coming. Each recipe then
says whether it conflicts with a restriction of at least one guest who opted
in to sharing with hosts. Nothing else about the guests leaves this use
case: not which guest, not which restriction, not
whether a guest opted in (a guest who did not counts as having no
restrictions), and nothing is logged.
"""

from collections.abc import Mapping
from dataclasses import replace

from src.cookbook.application.dto.views import Lookups
from src.cookbook.application.dto.views import RecipeSummary
from src.cookbook.application.dto.views import RecipeView
from src.cookbook.application.dto.views import StepImage
from src.cookbook.application.services.lookups import LookupLoader
from src.cookbook.application.services.mirror_facts import MirrorFacts
from src.cookbook.application.services.mirror_facts import SourceFacts
from src.cookbook.application.services.mirror_facts import merge_warnings
from src.cookbook.application.services.variation_resolver import VariationResolver
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.application.use_cases.equipment.kitchen import ManageKitchen
from src.cookbook.domain.entities.ingredient import Ingredient
from src.cookbook.domain.entities.personal import FoodRestriction
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import FeatureDisabledError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.services.diet_rules import diets_of
from src.cookbook.domain.services.equipment_rules import missing_equipment
from src.cookbook.domain.services.recipe_derivation import derive
from src.cookbook.domain.services.recipe_rules import can_edit_recipe
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.restriction_rules import RestrictionWarning
from src.cookbook.domain.services.restriction_rules import warnings_for
from src.cookbook.domain.services.seasons import recipe_season
from src.cookbook.domain.services.sub_recipes import all_ingredient_ids
from src.cookbook.domain.services.variations import apply_variation
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.viewer import Viewer
from src.cookbook.ports.outbound.repositories.cooking_repositories import ICookEventRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import ICookNoteRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import IFavouriteRepository
from src.cookbook.ports.outbound.repositories.personal_repositories import (
    IFoodRestrictionRepository,
)
from src.cookbook.ports.outbound.repositories.personal_repositories import IRatingRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery
from src.cookbook.ports.outbound.repositories.recipe_repository import StepImageQuery
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidInputError
from src.platform.domain.exceptions import UserNotFoundError
from src.platform.ports.outbound.feature_switches import IFeatureSwitches
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.shared_kernel.domain.services.clock import now_utc

MAX_GUESTS = 30
# A filter on derived data (diets, guests) pages in memory over at most this
# many matches, which a household's cookbook never reaches.
MAX_FILTERED = 5000


class ReadRecipes:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        favourite_repo: IFavouriteRepository,
        rating_repo: IRatingRepository,
        note_repo: ICookNoteRepository,
        restriction_repo: IFoodRestrictionRepository,
        cook_event_repo: ICookEventRepository,
        user_repo: IUserRepository,
        lookups: LookupLoader,
        viewers: ViewerResolver,
        kitchen: ManageKitchen,
        features: IFeatureSwitches,
        variation_repo: IRecipeVariationRepository,
        variation_resolver: VariationResolver,
        facts: MirrorFacts | None = None,
    ) -> None:
        self._facts = facts
        self._variations = variation_repo
        self._resolver = variation_resolver
        self._kitchen = kitchen
        self._features = features
        self._recipes = recipe_repo
        self._favourites = favourite_repo
        self._ratings = rating_repo
        self._notes = note_repo
        self._restrictions = restriction_repo
        self._events = cook_event_repo
        self._users = user_repo
        self._lookups = lookups
        self._viewers = viewers

    async def query_for(self, actor: User, **filters: object) -> RecipeQuery:
        """A query over the recipes the actor may see."""
        viewer = await self._viewers.of(actor)
        return RecipeQuery(
            viewer_id=actor.id,
            viewer_group_ids=sorted(viewer.group_ids),
            viewer_household_member_ids=sorted(viewer.household_member_ids),
            **filters,  # type: ignore[arg-type]
        )

    async def resolve_guests(self, public_ids: list[str]) -> list[int]:
        """The internal ids of the named guests. Every guest must be an
        active person; the answer is the same whether or not they opted in.
        With the dinner guests feature switched off, guests are refused."""
        if public_ids and not (await self._features.get_features()).dinner_guests:
            raise FeatureDisabledError("Dinner guests are switched off on this instance.")
        # The limit is checked before any lookup, so a long list costs no
        # queries.
        wanted = list(dict.fromkeys(public_ids))
        if len(wanted) > MAX_GUESTS:
            raise InvalidInputError(f"Choose at most {MAX_GUESTS} guests.")
        ids: list[int] = []
        for public_id in wanted:
            user = await self._users.get_by_public_id(public_id)
            if user is None or not user.is_active or user.is_service_account:
                raise UserNotFoundError("One of the guests does not exist.")
            ids.append(user.id)
        return ids

    async def _guest_restrictions(self, guest_ids: list[int]) -> list[FoodRestriction]:
        """The restrictions of the guests who opted in and hold the health
        data consent; the others count as having none."""
        opted_in = []
        for user_id in guest_ids:
            user = await self._users.get(user_id)
            if (
                user is not None
                and user.is_active
                and user.share_restrictions_with_hosts
                and user.consent_health_data_at is not None
            ):
                opted_in.append(user.id)
        return await self._restrictions.list_for_users(opted_in)

    async def summaries(
        self,
        actor: User,
        recipes: list[Recipe],
        guest_ids: list[int] | None = None,
        diets: list[Diet] | None = None,
    ) -> tuple[list[RecipeSummary], Lookups]:
        ids = [r.id for r in recipes]
        lookups = await self._lookups.load_for(recipes)
        stats = await self._ratings.stats(ids)
        favourites = await self._favourites.favourite_ids(actor.id, ids)
        restrictions = await self._restrictions.list_for_user(actor.id)
        guest_restrictions = await self._guest_restrictions(guest_ids or [])
        viewer = await self._viewers.of(actor)
        last = await self._events.last_cooked(ids)
        month = now_utc().month
        owned = await self._kitchen.owned(actor)
        variation_counts = await self._variations.visible_counts(ids, actor.id)
        facts_of = await self._facts_of(recipes, lookups)
        sources = await self._facts.instance_names(recipes) if self._facts else {}
        result: list[RecipeSummary] = []
        for recipe in recipes:
            # Through the sub-recipes too, whatever the viewer sees of them.
            used = all_ingredient_ids(recipe, lookups.recipes)
            facts = facts_of.get(recipe.id, SourceFacts())
            ingredients = facts.ingredients(lookups.ingredients)
            allergens = facts.allergens(
                a for i in used if i in ingredients for a in ingredients[i].allergens
            )
            average, count = stats.get(recipe.id, (None, 0))
            source = sources.get(recipe.id)
            result.append(
                RecipeSummary(
                    recipe=recipe,
                    allergens=list[Allergen](allergens),
                    rating_average=average,
                    rating_count=count,
                    is_favourite=recipe.id in favourites,
                    has_warning=bool(self._warnings(restrictions, used, ingredients, facts)),
                    can_edit=can_edit_recipe(viewer, recipe),
                    last_cooked=last.get(recipe.id),
                    diets=facts.diets(diets_of(ingredients[i] for i in used if i in ingredients)),
                    unsuitable_for_guests=bool(
                        guest_restrictions
                        and self._warnings(guest_restrictions, used, ingredients, facts)
                    ),
                    season_months=(season := recipe_season(used, lookups.ingredients)),
                    in_season=month in season,
                    missing_equipment_ids=(
                        missing_equipment(recipe, lookups.recipes, owned)
                        if owned is not None
                        else None
                    ),
                    variation_count=variation_counts.get(recipe.id, 0),
                    mirror_instance=source[0] if source else None,
                    mirror_author=source[1] if source else None,
                    mirror_author_avatar=source[2] if source else None,
                )
            )
        await self._mark_variations(viewer, result, lookups, guest_restrictions, set(diets or []))
        return result, lookups

    async def _facts_of(self, recipes: list[Recipe], lookups: Lookups) -> dict[int, SourceFacts]:
        if self._facts is None:
            return {}
        return await self._facts.for_recipes(recipes, lookups.recipes)

    @staticmethod
    def _warnings(
        restrictions: list[FoodRestriction],
        used: list[int],
        ingredients: Mapping[int, Ingredient],
        facts: SourceFacts,
    ) -> list[RestrictionWarning]:
        """The restrictions the ingredients break, and on a mirror those its
        source's plain-text lines or unknown values break or might break."""
        return merge_warnings(
            warnings_for(restrictions, used, ingredients), facts.warnings(restrictions)
        )

    async def _mark_variations(
        self,
        viewer: Viewer,
        summaries: list[RecipeSummary],
        lookups: Lookups,
        guest_restrictions: list[FoodRestriction],
        wanted: set[Diet],
    ) -> None:
        """Flags recipes that miss the guests or the diets while one of
        their visible variations fits."""
        candidates = [
            s
            for s in summaries
            if s.variation_count
            and (
                (guest_restrictions and s.unsuitable_for_guests)
                or (wanted and not wanted.issubset(s.diets))
            )
        ]
        if not candidates:
            return
        by_recipe = await self._variations.for_recipes([s.recipe.id for s in candidates])
        for summary in candidates:
            for variation in by_recipe.get(summary.recipe.id, []):
                if not can_view_variation(viewer, summary.recipe, variation):
                    continue
                resolved = await self._resolver.resolve(variation.changes, variation.locale)
                applied = apply_variation(summary.recipe, resolved.changes, variation.locale)
                lookups.ingredients.update(
                    {i.id: i for i in self._resolver.ingredients.values() if i is not None}
                )
                used = all_ingredient_ids(applied.recipe, lookups.recipes)
                facts = (await self._facts_of([applied.recipe], lookups)).get(
                    applied.recipe.id, SourceFacts()
                )
                ingredients = facts.ingredients(lookups.ingredients)
                if (
                    guest_restrictions
                    and summary.unsuitable_for_guests
                    and not self._warnings(guest_restrictions, used, ingredients, facts)
                ):
                    summary.variation_fits_guests = True
                if wanted and not wanted.issubset(summary.diets):
                    fits = facts.diets(diets_of(ingredients[i] for i in used if i in ingredients))
                    if wanted.issubset(fits):
                        summary.variation_fits_diets = True

    async def view(
        self,
        actor: User,
        public_id: str,
        *,
        servings: int | None = None,
        guest_ids: list[int] | None = None,
    ) -> RecipeView:
        recipe = await self._recipes.get_by_public_id(public_id)
        if recipe is None or not can_view_recipe(await self._viewers.of(actor), recipe):
            raise RecipeNotFoundError("No such recipe.")
        return await self.view_of(actor, recipe, servings=servings, guest_ids=guest_ids)

    async def view_of(
        self,
        actor: User,
        recipe: Recipe,
        *,
        servings: int | None = None,
        guest_ids: list[int] | None = None,
    ) -> RecipeView:
        lookups = await self._lookups.load_for([recipe])
        facts = (await self._facts_of([recipe], lookups)).get(recipe.id, SourceFacts())
        ingredients = facts.ingredients(lookups.ingredients)
        local = derive(recipe, lookups.ingredients, lookups.units, servings, lookups.recipes)
        derived = derive(recipe, ingredients, lookups.units, servings, lookups.recipes)
        derived = replace(
            derived,
            allergens=facts.allergens(derived.allergens),
            diets=facts.diets(derived.diets),
        )
        used = all_ingredient_ids(recipe, lookups.recipes)
        average, count = (await self._ratings.stats([recipe.id])).get(recipe.id, (None, 0))
        overall, overall_count = (await self._ratings.stats([recipe.id], overall=True)).get(
            recipe.id, (None, 0)
        )
        viewer = await self._viewers.of(actor)
        copies = [r for r in await self._recipes.copies_of(recipe.id) if can_view_recipe(viewer, r)]
        restrictions = await self._restrictions.list_for_user(actor.id)
        guest_restrictions = await self._guest_restrictions(guest_ids or [])
        season = recipe_season(used, lookups.ingredients)
        owned = await self._kitchen.owned(actor)
        return RecipeView(
            recipe=recipe,
            derived=derived,
            lookups=lookups,
            rating_average=average,
            rating_count=count,
            is_favourite=bool(await self._favourites.favourite_ids(actor.id, [recipe.id])),
            own_rating=await self._ratings.get_own(actor.id, recipe.id),
            own_note=await self._notes.get_own(actor.id, recipe.id),
            warnings=self._warnings(restrictions, used, ingredients, facts),
            can_edit=can_edit_recipe(await self._viewers.of(actor), recipe),
            last_cooked=(await self._events.last_cooked([recipe.id])).get(recipe.id),
            last_cooked_by_me=(await self._events.last_cooked([recipe.id], actor.id)).get(
                recipe.id
            ),
            unsuitable_for_guests=bool(
                guest_restrictions and self._warnings(guest_restrictions, used, ingredients, facts)
            ),
            season_months=season,
            in_season=now_utc().month in season,
            missing_equipment_ids=(
                missing_equipment(recipe, lookups.recipes, owned) if owned is not None else None
            ),
            variation_count=(await self._variations.visible_counts([recipe.id], actor.id)).get(
                recipe.id, 0
            ),
            based_on_count=len(copies),
            rating_overall_average=overall,
            rating_overall_count=overall_count,
            mirror=await self._facts.info(recipe) if self._facts else None,
            source_allergens_added=sorted(
                set(derived.allergens) - set(local.allergens), key=lambda a: a.value
            ),
            unknown_allergens=sorted(facts.unknown_allergens),
            unknown_diet_markers=sorted(facts.unknown_markers),
        )

    async def step_images(self, actor: User, query: StepImageQuery) -> tuple[list[StepImage], int]:
        """The step image library: the images on steps of every local recipe
        the actor may see, so a photo that fits many recipes, such as chopped
        onions, is taken once and picked again. Images that share the most
        ingredients and equipment with the edited step come first, then the
        actor's own. Mirrors are left out, since their photos belong to the
        cooks of another instance."""
        hits, total = await self._recipes.step_images(await self.query_for(actor), query)
        found = await self._recipes.get_many(sorted({h.recipe_id for h in hits}))
        recipes = {r.id: r for r in found}
        return [
            StepImage(h.file_id, recipes[h.recipe_id], h.step_position, h.matches)
            for h in hits
            if h.recipe_id in recipes
        ], total

    # Defined last: inside the class body the name `list` would shadow the
    # builtin in the annotations of the methods below it.
    async def list(
        self,
        actor: User,
        query: RecipeQuery,
        *,
        guest_ids: list[int] | None = None,
        diets: list[Diet] | None = None,
        hide_unsuitable_for_guests: bool = False,
        in_season: bool = False,
        only_kitchen_ready: bool = False,
    ) -> tuple[list[RecipeSummary], int, Lookups]:
        wanted = set(diets or [])
        hide = hide_unsuitable_for_guests and bool(guest_ids)
        # Before the kitchen is set up nothing is flagged, so nothing is hidden.
        kitchen = only_kitchen_ready and await self._kitchen.owned(actor) is not None
        if not wanted and not hide and not in_season and not kitchen:
            recipes, total = await self._recipes.find(query)
            summaries, lookups = await self.summaries(actor, recipes, guest_ids, diets)
            return summaries, total, lookups
        # Diets, guest conflicts, seasons and the kitchen are derived, so the
        # filter runs in memory.
        recipes, _ = await self._recipes.find(replace(query, limit=MAX_FILTERED, offset=0))
        summaries, lookups = await self.summaries(actor, recipes, guest_ids, diets)
        kept = [
            s
            for s in summaries
            if (wanted.issubset(s.diets) or s.variation_fits_diets)
            and not (hide and s.unsuitable_for_guests and not s.variation_fits_guests)
            and (s.in_season or not in_season)
            and not (kitchen and s.missing_equipment_ids)
        ]
        return kept[query.offset : query.offset + query.limit], len(kept), lookups
