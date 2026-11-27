from typing import Protocol
from uuid import UUID

from src.cookbook.domain.entities.mirror import CatalogueMapping
from src.cookbook.domain.entities.mirror import IncomingRecipe
from src.cookbook.domain.entities.mirror import IncomingStatus
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.entities.mirror import RecipeMirror
from src.cookbook.domain.entities.mirror import SuggestionDismissal


class IMirrorRepository(Protocol):
    """Mirrors, recipes waiting for a decision and catalogue mappings of
    paired instances."""

    async def get(self, recipe_id: int) -> RecipeMirror | None: ...
    async def by_origin(self, peer_id: int, origin_public_id: UUID) -> RecipeMirror | None: ...
    async def for_peer(self, peer_id: int) -> list[RecipeMirror]: ...
    async def for_recipes(self, recipe_ids: list[int]) -> dict[int, RecipeMirror]: ...
    async def with_author_avatar(self, file_public_id: str) -> list[int]:
        """The recipe ids of the mirrors that show the file as the avatar of
        the recipe's author or of a variation's author."""
        ...

    async def save(self, mirror: RecipeMirror) -> RecipeMirror: ...

    async def incoming(self, public_id: str) -> IncomingRecipe | None: ...
    async def incoming_by_origin(
        self, peer_id: int, origin_public_id: UUID
    ) -> IncomingRecipe | None: ...

    async def incoming_list(
        self, status: IncomingStatus | None = None, peer_id: int | None = None
    ) -> list[IncomingRecipe]:
        """Oldest first."""
        ...

    async def save_incoming(self, item: IncomingRecipe) -> IncomingRecipe: ...
    async def delete_incoming(self, item_id: int) -> None: ...

    async def mappings(self, peer_id: int) -> list[CatalogueMapping]: ...
    async def mapping(
        self, peer_id: int, kind: MappingKind, remote_id: str
    ) -> CatalogueMapping | None: ...

    async def save_mapping(self, mapping: CatalogueMapping) -> None: ...

    async def repoint_mappings(self, kind: MappingKind, from_id: int, to_id: int) -> None:
        """Every mapping of every peer pointing at a local entry that is
        merged into another points at the other one."""
        ...

    async def dismissals(self, peer_id: int) -> list[SuggestionDismissal]: ...

    async def save_dismissal(self, dismissal: SuggestionDismissal) -> None:
        """Adds the dismissal, or replaces the one of the same peer, kind,
        entry and field."""
        ...

    async def purge_peer(self, peer_id: int) -> None:
        """Deletes the peer's waiting recipes, catalogue mappings and
        dismissed suggestions; its mirrors are deleted as recipes by the
        caller."""
        ...
