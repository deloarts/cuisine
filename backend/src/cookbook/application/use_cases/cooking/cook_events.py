"""
The cooking history: who cooked what on which day. Everyone sees everyone's
cook events of the recipes they may see; an event of a recipe hidden from the
viewer is left out, and stays with its cook. Each user adds, edits and
deletes their own, and logs a recipe at most once a day, whichever variation
was cooked.
"""

from datetime import date
from datetime import timedelta

from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.entities.cooking import CookEvent
from src.cookbook.domain.exceptions import CookEventExistsError
from src.cookbook.domain.exceptions import CookEventNotFoundError
from src.cookbook.domain.exceptions import InvalidPlanError
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.exceptions import VariationNotFoundError
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.variations import can_view_variation
from src.cookbook.domain.value_objects.enums import RecipeStatus
from src.cookbook.ports.outbound.repositories.cooking_repositories import ICookEventRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.variation_repository import IRecipeVariationRepository
from src.platform.domain.entities.user import User
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

MAX_RANGE_DAYS = 400
# "On this day" looks this many days to either side in earlier years.
ON_THIS_DAY_WINDOW = 3
ON_THIS_DAY_YEARS = 5


class ManageCookEvents:
    def __init__(
        self,
        *,
        cook_event_repo: ICookEventRepository,
        recipe_repo: IRecipeRepository,
        variation_repo: IRecipeVariationRepository,
        viewers: ViewerResolver,
        uow: IUnitOfWork,
    ) -> None:
        self._variations = variation_repo
        self._events = cook_event_repo
        self._recipes = recipe_repo
        self._viewers = viewers
        self._uow = uow

    async def _visible(self, actor: User, events: list[CookEvent]) -> list[CookEvent]:
        viewer = await self._viewers.of(actor)
        recipes = {
            r.id: r for r in await self._recipes.get_many(sorted({e.recipe_id for e in events}))
        }
        return [
            e
            for e in events
            if e.recipe_id in recipes and can_view_recipe(viewer, recipes[e.recipe_id])
        ]

    async def calendar(
        self,
        actor: User,
        date_from: date,
        date_to: date,
        *,
        user_id: int | None = None,
        recipe_id: int | None = None,
    ) -> list[CookEvent]:
        if date_to < date_from:
            raise InvalidPlanError("The end of the range lies before its start.")
        if (date_to - date_from).days > MAX_RANGE_DAYS:
            raise InvalidPlanError(f"Ask for at most {MAX_RANGE_DAYS} days at once.")
        return await self._visible(
            actor,
            await self._events.find(
                date_from=date_from, date_to=date_to, user_id=user_id, recipe_id=recipe_id
            ),
        )

    async def for_recipe(
        self, recipe_id: int, *, user_id: int | None = None, limit: int = 100
    ) -> list[CookEvent]:
        return await self._events.find(recipe_id=recipe_id, user_id=user_id, limit=limit)

    async def recent(
        self, actor: User, *, limit: int = 20, user_id: int | None = None
    ) -> list[CookEvent]:
        # Hidden events are dropped after the query, so it reads ahead.
        found = await self._events.find(user_id=user_id, limit=limit * 5)
        return (await self._visible(actor, found))[:limit]

    async def on_this_day(
        self, actor: User, day: date, *, user_id: int | None = None
    ) -> list[CookEvent]:
        """Cook events around the same day in earlier years, newest first."""
        found: list[CookEvent] = []
        for years_back in range(1, ON_THIS_DAY_YEARS + 1):
            try:
                anchor = day.replace(year=day.year - years_back)
            except ValueError:  # 29 February
                anchor = day.replace(year=day.year - years_back, day=28)
            found.extend(
                await self._events.find(
                    date_from=anchor - timedelta(days=ON_THIS_DAY_WINDOW),
                    date_to=anchor + timedelta(days=ON_THIS_DAY_WINDOW),
                    user_id=user_id,
                )
            )
        return await self._visible(actor, found)

    async def _own(self, actor: User, public_id: str) -> CookEvent:
        event = await self._events.get_by_public_id(public_id)
        if event is None or event.user_id != actor.id:
            raise CookEventNotFoundError("No such cook event of yours.")
        return event

    @staticmethod
    def _check(cooked_on: date, servings: int, note: str) -> None:
        if cooked_on > now_utc().date() + timedelta(days=1):
            raise InvalidPlanError("A cook event cannot lie in the future.")
        if not 1 <= servings <= 100:
            raise InvalidPlanError("The servings must be between 1 and 100.")
        if len(note) > 2000:
            raise InvalidPlanError("The note is too long.")

    async def _logged_on(self, user_id: int, recipe_id: int, day: date) -> CookEvent | None:
        found = await self._events.find(
            user_id=user_id, recipe_id=recipe_id, date_from=day, date_to=day, limit=1
        )
        return found[0] if found else None

    async def create(
        self,
        actor: User,
        recipe_public_id: str,
        cooked_on: date,
        servings: int,
        note: str = "",
        variation_public_id: str | None = None,
    ) -> CookEvent:
        """Records a cook event of the recipe, or of one of its variations
        the actor may see. A second one on the same day is refused, so a
        note typed for it is never dropped without the cook knowing."""
        event, created = await self._log(
            actor, recipe_public_id, cooked_on, servings, note, variation_public_id
        )
        if not created:
            raise CookEventExistsError("You already logged this recipe on that day.")
        return event

    async def log_once(
        self,
        actor: User,
        recipe_public_id: str,
        cooked_on: date,
        servings: int,
        variation_public_id: str | None = None,
    ) -> tuple[CookEvent, bool]:
        """Logs the recipe as cooked on the day unless the actor already did,
        and says whether it created the event. Cook mode calls it when the
        cook finishes, so finishing twice in a day leaves one event."""
        return await self._log(
            actor, recipe_public_id, cooked_on, servings, "", variation_public_id
        )

    async def _log(
        self,
        actor: User,
        recipe_public_id: str,
        cooked_on: date,
        servings: int,
        note: str,
        variation_public_id: str | None,
    ) -> tuple[CookEvent, bool]:
        recipe = await self._recipes.get_by_public_id(recipe_public_id)
        viewer = await self._viewers.of(actor)
        if recipe is None or not can_view_recipe(viewer, recipe):
            raise RecipeNotFoundError("No such recipe.")
        variation_id: int | None = None
        if variation_public_id:
            variation = await self._variations.get_by_public_id(variation_public_id)
            if (
                variation is None
                or variation.recipe_id != recipe.id
                or not can_view_variation(viewer, recipe, variation)
            ):
                raise VariationNotFoundError("No such variation of this recipe.")
            variation_id = variation.id
        if recipe.status is not RecipeStatus.PUBLISHED:
            raise InvalidPlanError("Only published recipes go into the cooking history.")
        self._check(cooked_on, servings, note)
        existing = await self._logged_on(actor.id, recipe.id, cooked_on)
        if existing is not None:
            return existing, False
        event = await self._events.save(
            CookEvent(
                user_id=actor.id,
                recipe_id=recipe.id,
                cooked_on=cooked_on,
                servings=servings,
                created=now_utc(),
                note=note.strip(),
                variation_id=variation_id,
            )
        )
        await self._uow.commit()
        return event, True

    async def update(
        self, actor: User, public_id: str, cooked_on: date, servings: int, note: str
    ) -> CookEvent:
        event = await self._own(actor, public_id)
        self._check(cooked_on, servings, note)
        if cooked_on != event.cooked_on and await self._logged_on(
            actor.id, event.recipe_id, cooked_on
        ):
            raise CookEventExistsError("You already logged this recipe on that day.")
        event.cooked_on = cooked_on
        event.servings = servings
        event.note = note.strip()
        saved = await self._events.save(event)
        await self._uow.commit()
        return saved

    async def delete(self, actor: User, public_id: str) -> None:
        await self._events.delete(await self._own(actor, public_id))
        await self._uow.commit()
