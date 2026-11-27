from dataclasses import dataclass
from dataclasses import field
from typing import Literal
from typing import Protocol
from uuid import UUID

from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.value_objects.enums import Difficulty

RecipeSort = Literal["newest", "title", "changed"]


@dataclass(frozen=True)
class RecipeQuery:
    # Who reads: their own recipes and drafts, and published recipes their
    # visibility opens to them through a share, a group or the household.
    viewer_id: int
    viewer_group_ids: list[int] = field(default_factory=list)
    viewer_household_member_ids: list[int] = field(default_factory=list)
    # An anonymous visitor (`Viewer.visitor`): only published public
    # recipes, and none while the instance does not allow public recipes.
    # The viewer fields above are ignored then.
    anonymous: bool = False
    public_allowed: bool = False
    # "published" lists published recipes only, "drafts" the viewer's own
    # drafts only, None both.
    status: Literal["published", "drafts"] | None = None
    search: str | None = None
    tag_ids: list[int] = field(default_factory=list)
    owner_id: int | None = None
    favourites_of: int | None = None
    max_total_minutes: int | None = None
    difficulty: Difficulty | None = None
    ingredient_id: int | None = None
    sort: RecipeSort = "newest"
    limit: int = 24
    offset: int = 0


@dataclass(frozen=True)
class StepImageHit:
    """A stored image some step of a visible recipe shows, for the step image
    library. `step_position` is the 0-based index of one step showing it, and
    `matches` counts the ingredients and equipment items that step shares
    with the step being edited (the best of the steps showing the image)."""

    file_id: int
    recipe_id: int
    step_position: int
    matches: int


@dataclass(frozen=True)
class StepImageQuery:
    """What the step image library looks for: the ingredients and equipment
    of the step being edited, which rank the images, and an optional search
    over step text, recipe title and the steps' ingredient names."""

    ingredient_ids: list[int] = field(default_factory=list)
    equipment_ids: list[int] = field(default_factory=list)
    search: str | None = None
    limit: int = 24
    offset: int = 0


class IRecipeRepository(Protocol):
    async def get(self, recipe_id: int) -> Recipe | None: ...
    async def get_by_public_id(self, public_id: str) -> Recipe | None: ...
    async def get_many(self, ids: list[int]) -> list[Recipe]: ...
    async def find(self, query: RecipeQuery) -> tuple[list[Recipe], int]: ...
    async def save(self, recipe: Recipe) -> Recipe: ...
    async def parent_ids(self, recipe_ids: list[int]) -> dict[int, list[int]]: ...
    async def copies_of(self, recipe_id: int) -> list[Recipe]: ...
    async def owned_by(self, owner_id: int) -> list[Recipe]: ...
    async def by_origin(
        self, owner_id: int, origin_instance_id: UUID, origin_public_id: UUID
    ) -> Recipe | None:
        """The owner's recipe imported from that source recipe, if any."""
        ...

    async def shared_with_peer(self, peer_id: int) -> list[Recipe]:
        """Published recipes whose owner picked the peer as a share target."""
        ...

    async def published_for_peers(self) -> list[Recipe]:
        """Published recipes stored as peers or public that may leave the
        instance."""
        ...

    async def mirrors_of(self, peer_id: int) -> list[Recipe]: ...
    async def detach_from_meal_plans(self, recipe_id: int, title: str) -> None: ...
    async def unlink_sub_recipe(self, recipe_id: int) -> None: ...
    async def file_ids(self, recipe: Recipe) -> list[int]: ...
    async def file_in_use_elsewhere(self, file_id: int, recipe_id: int) -> bool: ...
    async def step_images(
        self, visible: RecipeQuery, query: StepImageQuery
    ) -> tuple[list[StepImageHit], int]:
        """The images on steps of the recipes `visible` matches, mirrors left
        out, one hit per stored file, best matches first, then the viewer's
        own, then the most recently changed; with the number of such files."""
        ...

    async def using_file(self, file_id: int) -> list[Recipe]:
        """The recipes whose cover or one of whose step images the file is."""
        ...

    async def delete(self, recipe: Recipe) -> None: ...
