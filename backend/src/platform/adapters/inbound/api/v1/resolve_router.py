"""
/api/v1/web/resolve/{public_id}: what a public id opens, for links in mails,
QR codes and agent references. Anything the user may not open answers 404
like an unknown id.
"""

from fastapi import APIRouter
from fastapi import Depends

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.deps import get_resolve_public_id
from src.platform.adapters.inbound.api.schemas.misc_schema import ResolvedPublicIdResponse
from src.platform.application.use_cases.resolve.resolve_public_id import ResolvePublicId
from src.platform.domain.entities.user import User

router = APIRouter(tags=["resolve"])


@router.get("/resolve/{public_id}", response_model=ResolvedPublicIdResponse)
async def resolve_public_id(
    public_id: str,
    user: User = Depends(get_current_user),
    use_case: ResolvePublicId = Depends(get_resolve_public_id),
) -> ResolvedPublicIdResponse:
    page = await use_case.execute(user, public_id)
    return ResolvedPublicIdResponse(kind=page.kind, id=page.public_id, route=page.route)
