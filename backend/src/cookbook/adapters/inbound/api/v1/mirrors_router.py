"""
Sharing recipes with paired instances and the recipes they share with this
one. `GET /peers/share-targets` names the paired instances users may share
with (for the share dialog; empty while peering is off). Under
`/admin/incoming-recipes` the administrator decides on recipes from paired
instances (read:settings to list, write:settings to accept, reject and
reopen; `POST /admin/peers/{id}/incoming-recipes/accept` accepts every
pending recipe of one peer with the automatic decisions), and under
`/admin/peers/{id}/mappings` reads and corrects the catalogue mappings of a
peer. Under `/admin/peer-suggestions` the catalogue
values paired instances offer for mapped local entries are listed
(read:settings) and accepted or dismissed (read:settings plus the rights of
the catalogue file for the kind, checked in `PeerSuggestions`). The admin
routes answer 404 while the peering feature switch is off.
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status as http_status

from src.cookbook.adapters.inbound.api.deps import get_manage_incoming_recipes
from src.cookbook.adapters.inbound.api.deps import get_manage_recipes
from src.cookbook.adapters.inbound.api.deps import get_peer_suggestions
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import AcceptedRecipeResponse
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import AcceptedWaitingResponse
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import AcceptIncomingRecipeRequest
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import CatalogueSuggestion
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import IncomingRecipeResponse
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import IncomingSubRecipe
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import MappingCorrectionRequest
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import MappingKindValue
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import NeededEntryResponse
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import PeerMappingResponse
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import PeerSuggestionGroupResponse
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import PeerSuggestionRequest
from src.cookbook.adapters.inbound.api.schemas.mirror_schema import PeerSuggestionResponse
from src.cookbook.adapters.inbound.api.schemas.recipe_schema import PeerRef
from src.cookbook.application.services.mirror_builder import MappingDecision
from src.cookbook.application.services.mirror_builder import Suggestion
from src.cookbook.application.use_cases.mirrors.incoming_recipes import IncomingView
from src.cookbook.application.use_cases.mirrors.incoming_recipes import ManageIncomingRecipes
from src.cookbook.application.use_cases.mirrors.incoming_recipes import MappingView
from src.cookbook.application.use_cases.mirrors.peer_suggestions import PeerSuggestions
from src.cookbook.application.use_cases.mirrors.peer_suggestions import SuggestionGroup
from src.cookbook.application.use_cases.recipes.manage_recipes import ManageRecipes
from src.cookbook.domain.entities.mirror import IncomingStatus
from src.cookbook.domain.entities.mirror import MappingKind
from src.cookbook.domain.services.translations import resolve
from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.peer_auth import require_peering_enabled
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(tags=["peering"])
admin_router = APIRouter(tags=["peering"], dependencies=[Depends(require_peering_enabled)])

_read = require_permission(Permission.READ_SETTINGS)
_write = require_permission(Permission.WRITE_SETTINGS)


def _suggestion(found: Suggestion | None) -> CatalogueSuggestion | None:
    return CatalogueSuggestion(id=UUID(found.id), name=found.name) if found else None


def _incoming(view: IncomingView) -> IncomingRecipeResponse:
    item = view.item
    return IncomingRecipeResponse(
        id=item.public_id,
        peer=PeerRef(id=view.peer.public_id, name=view.peer.name),
        source_id=item.origin_public_id,
        title=item.title,
        description=view.description,
        author_name=item.author_name,
        status=item.status.value,
        kind=item.kind.value,
        mirror_id=UUID(view.mirror_id) if view.mirror_id else None,
        received_at=item.received_at,
        decided_at=item.decided_at,
        entries=[
            NeededEntryResponse(
                kind=e.kind.value,
                source_id=e.remote_id,
                name=e.name,
                names=e.names,
                suggestion=_suggestion(e.suggestion),
                category_suggestion=_suggestion(e.category_suggestion),
                allergens=e.allergens,
                diet_markers=e.diet_markers,
            )
            for e in view.entries
        ],
        sub_recipes=[
            IncomingSubRecipe(
                source_id=s.source_id, title=s.title, mirrored=s.mirrored, waiting=s.waiting
            )
            for s in view.sub_recipes
        ],
    )


def _mapping(view: MappingView) -> PeerMappingResponse:
    mapping = view.mapping
    return PeerMappingResponse(
        kind=mapping.kind.value,
        source_id=mapping.remote_id,
        name=mapping.remote_name,
        action=mapping.action.value if mapping.action else None,
        target_id=UUID(view.target_id) if view.target_id else None,
        target_name=view.target_name,
        created_here=mapping.created_here,
        matched_by=mapping.matched_by,
        used_by=view.used_by,
        updated=mapping.updated,
    )


@router.get("/peers/share-targets", response_model=list[PeerRef])
async def list_peer_share_targets(
    user: User = Depends(get_current_user),
    use_case: ManageRecipes = Depends(get_manage_recipes),
) -> list[PeerRef]:
    return [PeerRef(id=p.public_id, name=p.name) for p in await use_case.peer_targets()]


@admin_router.get(
    "/admin/incoming-recipes",
    response_model=list[IncomingRecipeResponse],
    dependencies=[Depends(_read)],
)
async def list_incoming_recipes(
    status: Literal["pending", "rejected"] | None = Query("pending"),
    use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes),
) -> list[IncomingRecipeResponse]:
    wanted = IncomingStatus(status) if status else None
    return [_incoming(v) for v in await use_case.waiting(wanted)]


@admin_router.get(
    "/admin/incoming-recipes/{item_id}",
    response_model=IncomingRecipeResponse,
    dependencies=[Depends(_read)],
)
async def read_incoming_recipe(
    item_id: str, use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes)
) -> IncomingRecipeResponse:
    return _incoming(await use_case.get(item_id))


@admin_router.post(
    "/admin/incoming-recipes/{item_id}/accept",
    response_model=AcceptedRecipeResponse,
    dependencies=[Depends(_write)],
)
async def accept_incoming_recipe(
    item_id: str,
    body: AcceptIncomingRecipeRequest,
    use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes),
) -> AcceptedRecipeResponse:
    recipe = await use_case.accept(
        item_id,
        [
            MappingDecision(
                kind=MappingKind(d.kind),
                remote_id=d.source_id,
                action=d.action,
                target_id=str(d.target_id) if d.target_id else None,
                category_id=str(d.category_id) if d.category_id else None,
            )
            for d in body.decisions
        ],
    )
    title = resolve(recipe.translations, None, recipe.original_locale)[1].title
    return AcceptedRecipeResponse(id=recipe.public_id, title=title)


@admin_router.post(
    "/admin/incoming-recipes/{item_id}/reject",
    response_model=IncomingRecipeResponse,
    dependencies=[Depends(_write)],
)
async def reject_incoming_recipe(
    item_id: str, use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes)
) -> IncomingRecipeResponse:
    return _incoming(await use_case.reject(item_id))


@admin_router.post(
    "/admin/incoming-recipes/{item_id}/reopen",
    response_model=IncomingRecipeResponse,
    dependencies=[Depends(_write)],
)
async def reopen_incoming_recipe(
    item_id: str, use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes)
) -> IncomingRecipeResponse:
    return _incoming(await use_case.reopen(item_id))


@admin_router.post(
    "/admin/peers/{peer_id}/incoming-recipes/accept",
    response_model=AcceptedWaitingResponse,
    dependencies=[Depends(_write)],
)
async def accept_waiting_recipes(
    peer_id: str, use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes)
) -> AcceptedWaitingResponse:
    return AcceptedWaitingResponse(accepted=await use_case.accept_waiting(peer_id))


@admin_router.get(
    "/admin/peers/{peer_id}/mappings",
    response_model=list[PeerMappingResponse],
    dependencies=[Depends(_read)],
)
async def list_peer_mappings(
    peer_id: str, use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes)
) -> list[PeerMappingResponse]:
    return [_mapping(v) for v in await use_case.mappings(peer_id)]


@admin_router.put(
    "/admin/peers/{peer_id}/mappings/{kind}/{source_id}",
    response_model=PeerMappingResponse,
    dependencies=[Depends(_write)],
)
async def correct_peer_mapping(
    peer_id: str,
    kind: MappingKindValue,
    source_id: str,
    body: MappingCorrectionRequest,
    use_case: ManageIncomingRecipes = Depends(get_manage_incoming_recipes),
) -> PeerMappingResponse:
    view = await use_case.correct(
        peer_id,
        MappingDecision(
            kind=MappingKind(kind),
            remote_id=source_id,
            action=body.action,
            target_id=str(body.target_id) if body.target_id else None,
            category_id=str(body.category_id) if body.category_id else None,
        ),
    )
    return _mapping(view)


def _suggestion_group(group: SuggestionGroup) -> PeerSuggestionGroupResponse:
    return PeerSuggestionGroupResponse(
        kind=group.kind,
        id=UUID(group.id),
        name=group.name,
        warning=group.warning,
        suggestions=[
            PeerSuggestionResponse(
                peer=PeerRef(id=s.peer.public_id, name=s.peer.name),
                source_id=s.source_id,
                field=s.field,
                current=s.current,
                suggested=s.suggested,
                unmapped_units=s.unmapped_units,
            )
            for s in group.suggestions
        ],
    )


@admin_router.get(
    "/admin/peer-suggestions",
    response_model=list[PeerSuggestionGroupResponse],
    dependencies=[Depends(_read)],
)
async def list_peer_suggestions(
    peer_id: UUID | None = Query(None),
    kind: MappingKindValue | None = Query(None),
    actor: User = Depends(get_current_user),
    use_case: PeerSuggestions = Depends(get_peer_suggestions),
) -> list[PeerSuggestionGroupResponse]:
    groups = await use_case.read(
        actor,
        peer_public_id=str(peer_id) if peer_id else None,
        kind=MappingKind(kind) if kind else None,
    )
    return [_suggestion_group(g) for g in groups]


@admin_router.post(
    "/admin/peer-suggestions/accept",
    status_code=http_status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_read)],
)
async def accept_peer_suggestion(
    body: PeerSuggestionRequest,
    actor: User = Depends(get_current_user),
    use_case: PeerSuggestions = Depends(get_peer_suggestions),
) -> None:
    await use_case.accept(
        actor, str(body.peer_id), MappingKind(body.kind), body.source_id, body.field
    )


@admin_router.post(
    "/admin/peer-suggestions/dismiss",
    status_code=http_status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_read)],
)
async def dismiss_peer_suggestion(
    body: PeerSuggestionRequest,
    actor: User = Depends(get_current_user),
    use_case: PeerSuggestions = Depends(get_peer_suggestions),
) -> None:
    await use_case.dismiss(
        actor, str(body.peer_id), MappingKind(body.kind), body.source_id, body.field
    )
