"""
The web app's side of OAuth: the consent page's two calls and the connected
apps on the account page. All of them use the normal session, so the person
signs in to Cuisine exactly as always before approving an app.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.deps import get_authorize_oauth_client
from src.platform.adapters.inbound.api.deps import get_manage_own_oauth_grants
from src.platform.adapters.inbound.api.schemas.oauth_schema import AuthorizationDecisionRequest
from src.platform.adapters.inbound.api.schemas.oauth_schema import AuthorizationDecisionResponse
from src.platform.adapters.inbound.api.schemas.oauth_schema import AuthorizationPromptResponse
from src.platform.adapters.inbound.api.schemas.oauth_schema import AuthorizationRequestSchema
from src.platform.adapters.inbound.api.schemas.oauth_schema import ConnectedAppResponse
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.oauth.authorize import AuthorizationRequest
from src.platform.application.use_cases.oauth.authorize import AuthorizeOAuthClient
from src.platform.application.use_cases.oauth.grants import ManageOwnOAuthGrants
from src.platform.domain.entities.user import User
from src.platform.domain.services.oauth_rules import redirect_host

router = APIRouter(tags=["oauth"])


def _request(body: AuthorizationRequestSchema) -> AuthorizationRequest:
    return AuthorizationRequest(**body.model_dump())


@router.post("/oauth/authorize/inspect", response_model=AuthorizationPromptResponse)
async def inspect_authorization(
    body: AuthorizationRequestSchema,
    user: User = Depends(get_current_user),
    use_case: AuthorizeOAuthClient = Depends(get_authorize_oauth_client),
) -> AuthorizationPromptResponse:
    prompt = await use_case.inspect(user, _request(body))
    return AuthorizationPromptResponse(
        client_name=prompt.client.name,
        client_uri=prompt.client.client_uri,
        redirect_host=prompt.redirect_host,
        offered=prompt.offered,
        requested=prompt.requested,
        error_redirect=prompt.error_redirect,
    )


@router.post("/oauth/authorize/decision", response_model=AuthorizationDecisionResponse)
async def decide_authorization(
    body: AuthorizationDecisionRequest,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: AuthorizeOAuthClient = Depends(get_authorize_oauth_client),
) -> AuthorizationDecisionResponse:
    target = await use_case.decide(
        user,
        _request(body.request),
        approve=body.approve,
        permissions=body.permissions,
        context=context,
    )
    return AuthorizationDecisionResponse(redirect_to=target)


@router.get("/users/me/connected-apps", response_model=list[ConnectedAppResponse])
async def list_connected_apps(
    user: User = Depends(get_current_user),
    use_case: ManageOwnOAuthGrants = Depends(get_manage_own_oauth_grants),
) -> list[ConnectedAppResponse]:
    return [
        ConnectedAppResponse(
            id=app.grant.public_id,
            client_name=app.client.name if app.client else "",
            client_uri=app.client.client_uri if app.client else None,
            redirect_host=redirect_host(app.grant.redirect_uri),
            permissions=app.grant.permissions,
            created=app.grant.created,
            expires_at=app.grant.expires_at,
            last_used_at=app.grant.last_used_at,
        )
        for app in await use_case.list_all(user)
    ]


@router.delete("/users/me/connected-apps/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_connected_app(
    app_id: str,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnOAuthGrants = Depends(get_manage_own_oauth_grants),
) -> None:
    await use_case.revoke(user, app_id, context=context)
