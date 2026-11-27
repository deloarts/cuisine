"""/api/v1/web/settings: the admin settings, one section per route."""

from dataclasses import asdict

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import get_manage_settings
from src.platform.adapters.inbound.api.schemas.settings_schema import AgentSettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import BannerSettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import GeneralSettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import IntegrationSettingsRequest
from src.platform.adapters.inbound.api.schemas.settings_schema import IntegrationSettingsResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import MailSettingsRequest
from src.platform.adapters.inbound.api.schemas.settings_schema import MailSettingsResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import NotificationSettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import PrivacySettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import SecuritySettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import ShoppingSettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import TestMailRequest
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.admin.settings import ManageSettings
from src.platform.domain.entities.settings import AgentSettings
from src.platform.domain.entities.settings import BannerSettings
from src.platform.domain.entities.settings import GeneralSettings
from src.platform.domain.entities.settings import IntegrationSettings
from src.platform.domain.entities.settings import MailSettings
from src.platform.domain.entities.settings import NotificationSettings
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.settings import SecuritySettings
from src.platform.domain.entities.settings import ShoppingSettings
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.permission import Permission

router = APIRouter(prefix="/settings", tags=["settings"])

_read = require_permission(Permission.READ_SETTINGS)
_write = require_permission(Permission.WRITE_SETTINGS)


def _mail(settings: MailSettings) -> MailSettingsResponse:
    data = asdict(settings)
    data["password_set"] = bool(data.pop("password"))
    return MailSettingsResponse(**data)


@router.get("/general", response_model=GeneralSettingsSchema)
async def read_general(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> GeneralSettingsSchema:
    return GeneralSettingsSchema(**asdict(await use_case.general()))


@router.put("/general", response_model=GeneralSettingsSchema)
async def save_general(
    body: GeneralSettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> GeneralSettingsSchema:
    saved = await use_case.save_general(
        actor, GeneralSettings(**body.model_dump()), context=context
    )
    return GeneralSettingsSchema(**asdict(saved))


@router.get("/security", response_model=SecuritySettingsSchema)
async def read_security(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> SecuritySettingsSchema:
    return SecuritySettingsSchema(**asdict(await use_case.security()))


@router.put("/security", response_model=SecuritySettingsSchema)
async def save_security(
    body: SecuritySettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> SecuritySettingsSchema:
    saved = await use_case.save_security(
        actor, SecuritySettings(**body.model_dump()), context=context
    )
    return SecuritySettingsSchema(**asdict(saved))


@router.get("/mail", response_model=MailSettingsResponse)
async def read_mail(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> MailSettingsResponse:
    return _mail(await use_case.mail())


@router.put("/mail", response_model=MailSettingsResponse)
async def save_mail(
    body: MailSettingsRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> MailSettingsResponse:
    data = body.model_dump()
    keep_password = data["password"] is None
    data["password"] = data["password"] or ""
    saved = await use_case.save_mail(
        actor, MailSettings(**data), keep_password=keep_password, context=context
    )
    return _mail(saved)


@router.post("/mail/test", status_code=status.HTTP_204_NO_CONTENT)
async def send_test_mail(
    body: TestMailRequest | None = None,
    actor: User = Depends(_write),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> None:
    """Sends the test mail template, to `to` or the acting user's own address."""
    await use_case.send_test_mail(actor, to=body.to if body else None)


def _integrations(settings: IntegrationSettings) -> IntegrationSettingsResponse:
    return IntegrationSettingsResponse(
        usda_enabled=settings.usda_enabled,
        usda_api_key_set=bool(settings.usda_api_key),
        usda_uses_demo_key=settings.usda_api_key == "DEMO_KEY",
    )


@router.get("/integrations", response_model=IntegrationSettingsResponse)
async def read_integrations(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> IntegrationSettingsResponse:
    return _integrations(await use_case.integrations())


@router.put("/integrations", response_model=IntegrationSettingsResponse)
async def save_integrations(
    body: IntegrationSettingsRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> IntegrationSettingsResponse:
    keep_key = body.usda_api_key is None
    saved = await use_case.save_integrations(
        actor,
        IntegrationSettings(
            usda_enabled=body.usda_enabled, usda_api_key=(body.usda_api_key or "").strip()
        ),
        keep_key=keep_key,
        context=context,
    )
    return _integrations(saved)


@router.get("/agents", response_model=AgentSettingsSchema)
async def read_agents(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> AgentSettingsSchema:
    return AgentSettingsSchema(**asdict(await use_case.agents()))


@router.put("/agents", response_model=AgentSettingsSchema)
async def save_agents(
    body: AgentSettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> AgentSettingsSchema:
    saved = await use_case.save_agents(actor, AgentSettings(**body.model_dump()), context=context)
    return AgentSettingsSchema(**asdict(saved))


@router.get("/privacy", response_model=PrivacySettingsSchema)
async def read_privacy(
    _user: User = Depends(get_current_user),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> PrivacySettingsSchema:
    """Every signed-in user reads it, since the recipe editor needs to know
    whether visibility can be chosen."""
    return PrivacySettingsSchema(**asdict(await use_case.privacy()))


@router.put("/privacy", response_model=PrivacySettingsSchema)
async def save_privacy(
    body: PrivacySettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> PrivacySettingsSchema:
    saved = await use_case.save_privacy(
        actor, PrivacySettings(**body.model_dump()), context=context
    )
    return PrivacySettingsSchema(**asdict(saved))


@router.get("/shopping", response_model=ShoppingSettingsSchema)
async def read_shopping(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> ShoppingSettingsSchema:
    return ShoppingSettingsSchema(**asdict(await use_case.shopping()))


@router.put("/shopping", response_model=ShoppingSettingsSchema)
async def save_shopping(
    body: ShoppingSettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> ShoppingSettingsSchema:
    """The recently bought window of continuous lists and the idle days
    after which a normal list deletes itself."""
    saved = await use_case.save_shopping(
        actor, ShoppingSettings(**body.model_dump()), context=context
    )
    return ShoppingSettingsSchema(**asdict(saved))


@router.get("/notifications", response_model=NotificationSettingsSchema)
async def read_notifications(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> NotificationSettingsSchema:
    return NotificationSettingsSchema(**asdict(await use_case.notifications()))


@router.put("/notifications", response_model=NotificationSettingsSchema)
async def save_notifications(
    body: NotificationSettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> NotificationSettingsSchema:
    saved = await use_case.save_notifications(
        actor, NotificationSettings(**body.model_dump()), context=context
    )
    return NotificationSettingsSchema(**asdict(saved))


@router.get("/banner", response_model=BannerSettingsSchema)
async def read_banner(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> BannerSettingsSchema:
    return BannerSettingsSchema(**asdict(await use_case.banner()))


@router.put("/banner", response_model=BannerSettingsSchema)
async def save_banner(
    body: BannerSettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> BannerSettingsSchema:
    saved = await use_case.save_banner(actor, BannerSettings(**body.model_dump()), context=context)
    return BannerSettingsSchema(**asdict(saved))
