"""
The cookbook's rule for stored files, registered with Platform's
`FileAccess` from the composition root: a recipe image opens for whoever may
see one of the recipes that use it (`can_view_recipe`), and an avatar a
paired instance sent with an author's name opens for whoever may see the
mirror that shows it. The same rule
decides which existing images an editor may put on a recipe, so attaching
a file id never makes a photo visible to more people than it already was.
A file counts as referenced while a recipe, a revision or a mirror names
it, which keeps it from the uploader's delete and the nightly sweep.
"""

from collections.abc import Sequence

from src.cookbook.application.services.viewer import ViewerResolver
from src.cookbook.domain.entities.recipe import Recipe
from src.cookbook.domain.services.recipe_rules import can_view_recipe
from src.cookbook.ports.outbound.repositories.file_reference_repository import (
    IFileReferenceRepository,
)
from src.cookbook.ports.outbound.repositories.mirror_repository import IMirrorRepository
from src.cookbook.ports.outbound.repositories.recipe_repository import IRecipeRepository
from src.platform.domain.entities.stored_file import StoredFile
from src.platform.domain.entities.user import User


class RecipeFileAccess:
    def __init__(
        self,
        *,
        recipe_repo: IRecipeRepository,
        mirror_repo: IMirrorRepository,
        viewers: ViewerResolver,
        references: IFileReferenceRepository,
    ) -> None:
        self._references = references
        self._recipes = recipe_repo
        self._mirrors = mirror_repo
        self._viewers = viewers

    async def _recipes_showing(self, file: StoredFile) -> list[Recipe]:
        recipes = await self._recipes.using_file(file.id)
        if recipes or file.creator_id is not None:
            return recipes
        # A file without an uploader may be an avatar a peer sent.
        return await self._recipes.get_many(
            await self._mirrors.with_author_avatar(str(file.public_id))
        )

    async def may_read(self, actor: User, file: StoredFile) -> bool:
        recipes = await self._recipes_showing(file)
        if not recipes:
            return False
        viewer = await self._viewers.of(actor)
        return any(can_view_recipe(viewer, r) for r in recipes)

    async def referenced(self, files: Sequence[StoredFile], *, history: bool) -> set[int]:
        return await self._references.referenced(
            {f.id: str(f.public_id) for f in files}, history=history
        )
