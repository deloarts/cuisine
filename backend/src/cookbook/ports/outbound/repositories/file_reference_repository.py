from collections.abc import Mapping
from typing import Protocol


class IFileReferenceRepository(Protocol):
    """Which stored files the cookbook's records refer to."""

    async def referenced(self, files: Mapping[int, str], *, history: bool) -> set[int]:
        """Of the files given as internal id to public id, the ids that a
        recipe cover, a step image or a mirror (its images and the author
        avatars a peer sent) refers to, and with `history` also a revision
        snapshot."""
        ...
