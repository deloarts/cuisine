"""
Suggestions for the meal plan: published recipes the viewer may see, ranked
for one range of one plan by `meal_suggestions.rank`. The cooking history
behind the ranking is the plan's: every household member's cook events for
the household's plan, the viewer's own for the personal one. Cook events are
visible to every signed-in user anyway; still nothing about them leaves this
use case but the recipe and the label of the signal that carried it.
Recipes already planned in the range are left out.
"""

from dataclasses import dataclass
from datetime import date

from src.cookbook.application.dto.views import Lookups
from src.cookbook.application.dto.views import RecipeSummary
from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.application.use_cases.planning.meal_plan import ManageMealPlan
from src.cookbook.application.use_cases.recipes.read_recipes import MAX_FILTERED
from src.cookbook.application.use_cases.recipes.read_recipes import ReadRecipes
from src.cookbook.domain.services.meal_suggestions import CookHistory
from src.cookbook.domain.services.meal_suggestions import SuggestionCandidate
from src.cookbook.domain.services.meal_suggestions import anniversary_windows
from src.cookbook.domain.services.meal_suggestions import rank
from src.cookbook.domain.services.sub_recipes import all_ingredient_ids
from src.cookbook.domain.value_objects.enums import MealPlanScope
from src.cookbook.domain.value_objects.enums import MealSlot
from src.cookbook.domain.value_objects.enums import SuggestionReason
from src.cookbook.domain.value_objects.enums import TagKind
from src.cookbook.ports.outbound.repositories.cooking_repositories import ICookEventRepository
from src.platform.domain.entities.user import User
from src.shared_kernel.domain.services.clock import now_utc

MAX_SUGGESTIONS = 24


@dataclass(frozen=True)
class MealSuggestion:
    summary: RecipeSummary
    reason: SuggestionReason


class SuggestMeals:
    def __init__(
        self,
        *,
        meal_plan: ManageMealPlan,
        read_recipes: ReadRecipes,
        cook_event_repo: ICookEventRepository,
        viewers: ViewerResolver,
    ) -> None:
        self._plan = meal_plan
        self._recipes = read_recipes
        self._events = cook_event_repo
        self._viewers = viewers

    async def suggest(
        self,
        actor: User,
        date_from: date,
        date_to: date,
        *,
        scope: MealPlanScope | None = None,
        slot: MealSlot | None = None,
        limit: int = 12,
    ) -> tuple[list[MealSuggestion], Lookups]:
        # Checks the range and the scope like reading the plan does.
        planned = await self._plan.between(actor, date_from, date_to, scope)
        household_id = await self._plan.household_of(actor, scope)
        viewer = await self._viewers.of(actor)
        cooks = sorted(viewer.household_member_ids) if household_id is not None else [actor.id]
        history = await self._events.history(cooks, anniversary_windows(date_from, date_to))
        summaries, _, lookups = await self._recipes.list(
            actor,
            await self._recipes.query_for(actor, status="published", limit=MAX_FILTERED),
        )
        month = (date_from + (date_to - date_from) / 2).month
        candidates = [self._candidate(s, history, lookups, month) for s in summaries]
        ranked = rank(
            candidates,
            today=now_utc().date(),
            limit=min(max(limit, 0), MAX_SUGGESTIONS),
            slot=slot,
            excluded=[e.recipe_id for e in planned if e.recipe_id is not None],
        )
        by_id = {s.recipe.id: s for s in summaries}
        return [MealSuggestion(by_id[s.recipe_id], s.reason) for s in ranked], lookups

    @staticmethod
    def _candidate(
        summary: RecipeSummary,
        history: dict[int, CookHistory],
        lookups: Lookups,
        month: int,
    ) -> SuggestionCandidate:
        recipe = summary.recipe
        tags = [lookups.tags[t] for t in recipe.tag_ids if t in lookups.tags]
        ingredients = all_ingredient_ids(recipe, lookups.recipes)
        return SuggestionCandidate(
            recipe_id=recipe.id,
            published_on=(recipe.published_at or recipe.created).date(),
            history=history.get(recipe.id, CookHistory()),
            is_favourite=summary.is_favourite,
            in_season=month in summary.season_months,
            has_warning=summary.has_warning,
            meal_tag_keys=frozenset(
                t.seed_key for t in tags if t.kind is TagKind.MEAL and t.seed_key
            ),
            features=frozenset(
                [f"tag:{t.id}" for t in tags] + [f"ingredient:{i}" for i in ingredients]
            ),
        )
