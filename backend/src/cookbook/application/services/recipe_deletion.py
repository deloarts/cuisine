"""
Deleting a recipe, terminally. Its translations, steps, step ingredients,
shares, favourites, ratings, everyone's notes and its cook events go with it
(ON DELETE CASCADE); its images go too, each stored file only when no other
recipe uses it. Planned meals of it become free text with its title, and
shopping items keep their text without the link. A recipe another recipe
uses as a sub-recipe is not deleted.

A recipe that was ever published is announced as `recipe.deleted` with its
id only, and withdrawn from every paired instance that holds it. The service
stages the changes; the calling use case commits.
"""

from src.cookbook.application.services.peer_sharing import PeerRecipeSharing
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.exceptions import RecipeInUseError
from src.cookbook.domain.services.translations import resolve
from src.cookbook.ports.outbound.event_publisher import RECIPE_DELETED
from src.cookbook.ports.outbound.event_publisher import IEventPublisher
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository


class RecipeDeletion:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        file_repo: IStoredFileRepository,
        events: IEventPublisher | None = None,
        sharing: PeerRecipeSharing | None = None,
    ) -> None:
        self._sharing = sharing
        self._recipes = recipe_repo
        self._files = file_repo
        self._events = events

    async def parents(self, recipe: Recipe) -> list[Recipe]:
        ids = (await self._recipes.parent_ids([recipe.id])).get(recipe.id, [])
        return await self._recipes.get_many(ids)

    async def stage(self, recipe: Recipe, *, unlink_parents: bool = False) -> None:
        if await self.parents(recipe):
            if not unlink_parents:
                raise RecipeInUseError("Another recipe uses this one as a sub-recipe.")
            await self._recipes.unlink_sub_recipe(recipe.id)
        title = resolve(recipe.translations, None, recipe.original_locale)[1].title
        await self._recipes.detach_from_meal_plans(recipe.id, title)
        files = [
            f
            for f in await self._recipes.file_ids(recipe)
            if not await self._recipes.file_in_use_elsewhere(f, recipe.id)
        ]
        await self._recipes.delete(recipe)
        if self._events is not None and recipe.published_at is not None:
            await self._events.publish(RECIPE_DELETED, {"recipe": {"id": str(recipe.public_id)}})
        if self._sharing is not None:
            await self._sharing.withdraw([str(recipe.public_id)])
        for public_id in (await self._files.public_ids(files)).values():
            stored = await self._files.get_by_public_id(str(public_id))
            if stored is not None:
                await self._files.delete(stored)
