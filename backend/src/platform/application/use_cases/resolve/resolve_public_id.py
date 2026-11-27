"""
Resolves an opaque public id to the page it opens, for a client that holds
only the id (a link in a mail, a QR code on a printed recipe, an agent's
reference) and does not know its kind.

The answer applies the read rule of the kind it found. Whatever the user may
not open answers exactly like an unknown id, so resolving never reveals
that a private recipe or someone else's record exists. A personal record
resolves for its owner only, and a kind nobody registered a rule for never
resolves.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import PublicIdNotFoundError
from src.platform.ports.outbound.repositories.public_id_resolver import IPublicIdAccess
from src.platform.ports.outbound.repositories.public_id_resolver import IPublicIdResolver


@dataclass(frozen=True)
class ResolvedPage:
    kind: str
    # The public id of the page's row; never an internal id.
    public_id: UUID
    # The frontend path that opens it, such as "/recipes/<id>".
    route: str


def _parse(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


class ResolvePublicId:
    def __init__(
        self, *, resolver: IPublicIdResolver, access: Mapping[str, IPublicIdAccess]
    ) -> None:
        self._resolver = resolver
        self._access = access

    async def execute(self, actor: User, public_id: str) -> ResolvedPage:
        parsed = _parse(public_id)
        found = await self._resolver.resolve(parsed) if parsed is not None else None
        rule = self._access.get(found.kind) if found is not None else None
        if found is None or rule is None:
            raise PublicIdNotFoundError("Nothing you can open has this id.")
        if found.personal and (found.owner_id is None or found.owner_id != actor.id):
            raise PublicIdNotFoundError("Nothing you can open has this id.")
        route = await rule.route(actor, found.public_id)
        if route is None:
            raise PublicIdNotFoundError("Nothing you can open has this id.")
        return ResolvedPage(kind=found.kind, public_id=found.public_id, route=route)
