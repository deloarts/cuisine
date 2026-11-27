"""
Reading public recipes without signing in: the list and search of the
recipes an anonymous visitor may see, one recipe with what is derived from
it (ingredient list for the wanted servings, nutrition, allergens, diets,
seasons) and the check that an image belongs to such a recipe.

The visitor is `Viewer.visitor`, so the rule of what it sees is the one of
`can_view_recipe` and of the repository's SQL filter: a published recipe
whose effective visibility is public, and nothing while the instance does
not allow public recipes. Nothing of the personal layer is read here: no
favourites, ratings, notes, cook events, restrictions or guests. The author
is named only when the owner switched `show_name_on_public_recipes` on,
and then only by display name; their avatar shows under the same rule.
"""

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace

from src.cookbook.application.dto.views import Lookups
from src.cookbook.application.services.lookups import LookupLoader
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.entities.resources import Tag
from src.cookbook.domain.exceptions import RecipeNotFoundError
from src.cookbook.domain.services.diet_rules import diets_of
from src.cookbook.domain.services.recipe_derivation import DerivedRecipe
from src.cookbook.domain.services.recipe_derivation import derive
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.domain.services.seasons import recipe_season
from src.cookbook.domain.services.sub_recipes import all_ingredient_ids
from src.cookbook.domain.value_objects.enums import Allergen
from src.cookbook.domain.value_objects.enums import Diet
from src.cookbook.domain.value_objects.enums import Difficulty
from src.cookbook.domain.value_objects.viewer import Viewer
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeQuery
from src.cookbook.ports.outbound.repositories.recipe_repository import RecipeSort
from src.cookbook.ports.outbound.repositories.resource_repositories import ITagRepository
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import StoredFileNotFoundError
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.shared_kernel.domain.services.clock import now_utc

# A filter on derived data (diets) pages in memory over at most this many
# matches, as in the signed-in list.
MAX_FILTERED = 5000


@dataclass
class PublicRecipeSummary:
    recipe: Recipe
    allergens: list[Allergen]
    diets: list[Diet]
    season_months: list[int]
    in_season: bool
    # The owner's display name, only when the owner shows it on public recipes.
    author: str | None = None
    # Whether the owner shows their name and has an avatar to go with it.
    author_avatar: bool = False


@dataclass
class PublicRecipeView:
    recipe: Recipe
    derived: DerivedRecipe
    lookups: Lookups
    season_months: list[int]
    in_season: bool
    author: str | None
    author_avatar: bool
    # The visitor, for the presenter's sub-recipe and mention rules.
    viewer: Viewer
    # The images the page may load, by internal file id.
    image_ids: list[int] = field(default_factory=list)


def _name(authors: dict[int, User], recipe: Recipe) -> str | None:
    owner = authors.get(recipe.owner_id) if recipe.owner_id else None
    return owner.display_name if owner else None


def _has_avatar(authors: dict[int, User], recipe: Recipe) -> bool:
    owner = authors.get(recipe.owner_id) if recipe.owner_id else None
    return owner is not None and owner.avatar_file_id is not None


def recipe_image_ids(recipe: Recipe) -> set[int]:
    """The images that belong to a recipe: its cover and its step images."""
    ids = {s.image_file_id for s in recipe.steps if s.image_file_id is not None}
    if recipe.cover_file_id is not None:
        ids.add(recipe.cover_file_id)
    return ids


class ReadPublicRecipes:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        tag_repo: ITagRepository,
        user_repo: IUserRepository,
        settings_repo: ISettingsRepository,
        file_repo: IStoredFileRepository,
        lookups: LookupLoader,
    ) -> None:
        self._recipes = recipe_repo
        self._tags = tag_repo
        self._users = user_repo
        self._settings = settings_repo
        self._files = file_repo
        self._lookups = lookups
        self._viewer: Viewer | None = None

    async def viewer(self) -> Viewer:
        """The anonymous visitor, with the instance's public switch read
        once per request."""
        if self._viewer is None:
            privacy = await self._settings.get_privacy()
            self._viewer = Viewer.visitor(public_allowed=privacy.allow_public_recipes)
        return self._viewer

    async def _query(self, **filters: object) -> RecipeQuery:
        viewer = await self.viewer()
        return RecipeQuery(
            viewer_id=0,
            anonymous=True,
            public_allowed=viewer.public_allowed,
            status="published",
            **filters,  # type: ignore[arg-type]
        )

    async def _authors(self, recipes: list[Recipe]) -> dict[int, User]:
        """The owners who show their name on public recipes."""
        shown: dict[int, User] = {}
        for owner_id in {r.owner_id for r in recipes if r.owner_id is not None}:
            user = await self._users.get(owner_id)
            if user is not None and user.show_name_on_public_recipes and user.display_name.strip():
                shown[owner_id] = user
        return shown

    async def tag_ids_in_use(self) -> list[int]:
        """The tags of the recipes the visitor may see, for the tag filter."""
        query = await self._query(limit=MAX_FILTERED, offset=0)
        recipes, _ = await self._recipes.find(query)
        return sorted({t for r in recipes for t in r.tag_ids})

    async def tags(self) -> list[Tag]:
        wanted = set(await self.tag_ids_in_use())
        return [t for t in await self._tags.list_all() if t.id in wanted]

    async def summaries(self, recipes: list[Recipe]) -> tuple[list[PublicRecipeSummary], Lookups]:
        lookups = await self._lookups.load_for(recipes)
        authors = await self._authors(recipes)
        month = now_utc().month
        result: list[PublicRecipeSummary] = []
        for recipe in recipes:
            used = all_ingredient_ids(recipe, lookups.recipes)
            known = [lookups.ingredients[i] for i in used if i in lookups.ingredients]
            season = recipe_season(used, lookups.ingredients)
            result.append(
                PublicRecipeSummary(
                    recipe=recipe,
                    allergens=sorted(
                        {a for i in known for a in i.allergens}, key=lambda a: a.value
                    ),
                    diets=diets_of(known),
                    season_months=season,
                    in_season=month in season,
                    author=_name(authors, recipe),
                    author_avatar=_has_avatar(authors, recipe),
                )
            )
        return result, lookups

    async def list(
        self,
        *,
        search: str | None = None,
        tag_ids: list[int] | None = None,
        diets: list[Diet] | None = None,
        max_total_minutes: int | None = None,
        difficulty: Difficulty | None = None,
        sort: RecipeSort = "newest",
        limit: int = 24,
        offset: int = 0,
    ) -> tuple[list[PublicRecipeSummary], int, Lookups]:
        query = await self._query(
            search=search,
            tag_ids=tag_ids or [],
            max_total_minutes=max_total_minutes,
            difficulty=difficulty,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        wanted = set(diets or [])
        if not wanted:
            recipes, total = await self._recipes.find(query)
            summaries, lookups = await self.summaries(recipes)
            return summaries, total, lookups
        # Diets are derived, so that filter runs in memory.
        recipes, _ = await self._recipes.find(replace(query, limit=MAX_FILTERED, offset=0))
        summaries, lookups = await self.summaries(recipes)
        kept = [s for s in summaries if wanted.issubset(s.diets)]
        return kept[offset : offset + limit], len(kept), lookups

    async def _visible(self, public_id: str) -> Recipe:
        recipe = await self._recipes.get_by_public_id(public_id)
        if recipe is None or not can_view_recipe(await self.viewer(), recipe):
            raise RecipeNotFoundError("No such recipe.")
        return recipe

    async def view(self, public_id: str, *, servings: int | None = None) -> PublicRecipeView:
        recipe = await self._visible(public_id)
        lookups = await self._lookups.load_for([recipe])
        derived = derive(recipe, lookups.ingredients, lookups.units, servings, lookups.recipes)
        season = recipe_season(all_ingredient_ids(recipe, lookups.recipes), lookups.ingredients)
        authors = await self._authors([recipe])
        return PublicRecipeView(
            recipe=recipe,
            derived=derived,
            lookups=lookups,
            season_months=season,
            in_season=now_utc().month in season,
            author=_name(authors, recipe),
            author_avatar=_has_avatar(authors, recipe),
            viewer=await self.viewer(),
            image_ids=sorted(recipe_image_ids(recipe)),
        )

    async def author_avatar(self, recipe_public_id: str) -> str:
        """The public id of the avatar of the recipe's owner, while the recipe
        is public in effect and the owner shows their name on it; anything
        else answers like an unknown file."""
        try:
            recipe = await self._visible(recipe_public_id)
        except RecipeNotFoundError:
            raise StoredFileNotFoundError("No such file.") from None
        owner = (await self._authors([recipe])).get(recipe.owner_id or 0)
        stored = (
            await self._files.get(owner.avatar_file_id) if owner and owner.avatar_file_id else None
        )
        if stored is None or stored.thumbnail_hash is None:
            raise StoredFileNotFoundError("No such file.")
        return str(stored.public_id)

    async def assert_image(self, recipe_public_id: str, file_public_id: str) -> None:
        """Passes when the file is an image of a recipe the visitor may see
        and has a thumbnail; anything else answers like an unknown file, so
        nothing tells a hidden recipe or a foreign file apart from none."""
        try:
            recipe = await self._visible(recipe_public_id)
        except RecipeNotFoundError:
            raise StoredFileNotFoundError("No such file.") from None
        stored = await self._files.get_by_public_id(file_public_id)
        if (
            stored is None
            or stored.id not in recipe_image_ids(recipe)
            or stored.thumbnail_hash is None
        ):
            raise StoredFileNotFoundError("No such file.")
