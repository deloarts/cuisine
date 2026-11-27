"""
/api/v1/web/admin/webhooks and /admin/notices: the administrator's side of
notifications; /notices: each user's pending in-app notices. Reading the
admin side needs read:settings, changing it write:settings.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import get_manage_notices
from src.platform.adapters.inbound.api.deps import get_manage_webhooks
from src.platform.adapters.inbound.api.deps import get_own_notices
from src.platform.adapters.inbound.api.schemas.base import Page
from src.platform.adapters.inbound.api.schemas.notification_schema import (
    AcknowledgementOverviewResponse,
)
from src.platform.adapters.inbound.api.schemas.notification_schema import AcknowledgementResponse
from src.platform.adapters.inbound.api.schemas.notification_schema import NoticeAdminResponse
from src.platform.adapters.inbound.api.schemas.notification_schema import NoticeRequest
from src.platform.adapters.inbound.api.schemas.notification_schema import NoticeResponse
from src.platform.adapters.inbound.api.schemas.notification_schema import NoticeTextResponse
from src.platform.adapters.inbound.api.schemas.notification_schema import WebhookDeliveryResponse
from src.platform.adapters.inbound.api.schemas.notification_schema import WebhookEventResponse
from src.platform.adapters.inbound.api.schemas.notification_schema import WebhookSecretResponse
from src.platform.adapters.inbound.api.schemas.notification_schema import WebhookSubscriptionRequest
from src.platform.adapters.inbound.api.schemas.notification_schema import (
    WebhookSubscriptionResponse,
)
from src.platform.adapters.inbound.api.schemas.user_schema import UserSummaryResponse
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.admin.notices import ManageNotices
from src.platform.application.use_cases.admin.notices import NoticeSummary
from src.platform.application.use_cases.admin.notices import OwnNotices
from src.platform.application.use_cases.admin.webhooks import ManageWebhooks
from src.platform.application.use_cases.admin.webhooks import SubscriptionInput
from src.platform.domain.entities.notice import NoticeText
from src.platform.domain.entities.user import User
from src.platform.domain.entities.webhook import WebhookDelivery
from src.platform.domain.entities.webhook import WebhookSubscription
from src.platform.domain.services.notice_rules import notice_text
from src.platform.domain.value_objects.permission import Permission
from src.platform.domain.value_objects.webhook_event import webhook_events

router = APIRouter(tags=["notifications"])

_read = require_permission(Permission.READ_SETTINGS)
_write = require_permission(Permission.WRITE_SETTINGS)


def _subscription(sub: WebhookSubscription) -> WebhookSubscriptionResponse:
    return WebhookSubscriptionResponse(
        id=sub.public_id,
        name=sub.name,
        url=sub.url,
        events=sub.events,
        enabled=sub.enabled,
        created=sub.created,
        changed=sub.changed,
    )


def _with_secret(sub: WebhookSubscription) -> WebhookSecretResponse:
    return WebhookSecretResponse(**_subscription(sub).model_dump(), secret=sub.secret)


def _delivery(d: WebhookDelivery) -> WebhookDeliveryResponse:
    return WebhookDeliveryResponse(
        id=d.public_id,
        event=d.event,
        status=d.status.value,
        attempts=d.attempts,
        next_attempt_at=d.next_attempt_at,
        last_attempt_at=d.last_attempt_at,
        http_status=d.http_status,
        duration_ms=d.duration_ms,
        error=d.error,
        created=d.created,
        payload=d.payload,
    )


def _input(body: WebhookSubscriptionRequest) -> SubscriptionInput:
    return SubscriptionInput(name=body.name, url=body.url, events=body.events, enabled=body.enabled)


def _person(user: User) -> UserSummaryResponse:
    return UserSummaryResponse(id=user.public_id, display_name=user.display_name)


# ── Webhooks ──────────────────────────────────────────────────────────


@router.get("/admin/webhooks/events", response_model=list[WebhookEventResponse])
async def list_webhook_events(_user: User = Depends(_read)) -> list[WebhookEventResponse]:
    return [WebhookEventResponse(key=e.key, description=e.description) for e in webhook_events()]


@router.get("/admin/webhooks", response_model=list[WebhookSubscriptionResponse])
async def list_webhooks(
    _user: User = Depends(_read), use_case: ManageWebhooks = Depends(get_manage_webhooks)
) -> list[WebhookSubscriptionResponse]:
    return [_subscription(s) for s in await use_case.list_all()]


@router.post(
    "/admin/webhooks", response_model=WebhookSecretResponse, status_code=status.HTTP_201_CREATED
)
async def create_webhook(
    body: WebhookSubscriptionRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> WebhookSecretResponse:
    return _with_secret(await use_case.create(actor, _input(body), context=context))


@router.get("/admin/webhooks/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def read_webhook(
    webhook_id: str,
    _user: User = Depends(_read),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> WebhookSubscriptionResponse:
    return _subscription(await use_case.get(webhook_id))


@router.put("/admin/webhooks/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook(
    webhook_id: str,
    body: WebhookSubscriptionRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> WebhookSubscriptionResponse:
    return _subscription(await use_case.update(actor, webhook_id, _input(body), context=context))


@router.delete("/admin/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> None:
    await use_case.delete(actor, webhook_id, context=context)


@router.post("/admin/webhooks/{webhook_id}/rotate-secret", response_model=WebhookSecretResponse)
async def rotate_webhook_secret(
    webhook_id: str,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> WebhookSecretResponse:
    return _with_secret(await use_case.rotate_secret(actor, webhook_id, context=context))


@router.post("/admin/webhooks/{webhook_id}/test", response_model=WebhookDeliveryResponse)
async def test_webhook(
    webhook_id: str,
    _actor: User = Depends(_write),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> WebhookDeliveryResponse:
    """Sends a `ping` now and answers its logged delivery."""
    return _delivery(await use_case.send_test(webhook_id))


@router.get("/admin/webhooks/{webhook_id}/deliveries", response_model=Page[WebhookDeliveryResponse])
async def list_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: User = Depends(_read),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> Page[WebhookDeliveryResponse]:
    items, total = await use_case.deliveries(webhook_id, limit=limit, offset=offset)
    return Page(items=[_delivery(d) for d in items], total=total)


@router.post(
    "/admin/webhooks/{webhook_id}/deliveries/{delivery_id}/retry",
    response_model=WebhookDeliveryResponse,
)
async def retry_webhook_delivery(
    webhook_id: str,
    delivery_id: str,
    _actor: User = Depends(_write),
    use_case: ManageWebhooks = Depends(get_manage_webhooks),
) -> WebhookDeliveryResponse:
    return _delivery(await use_case.retry(webhook_id, delivery_id))


# ── Notices: admin ────────────────────────────────────────────────────


def _notice_admin(summary: NoticeSummary) -> NoticeAdminResponse:
    n = summary.notice
    return NoticeAdminResponse(
        id=n.public_id,
        texts={k: NoticeTextResponse(title=t.title, body=t.body) for k, t in n.texts.items()},
        active=n.active,
        created=n.created,
        changed=n.changed,
        acknowledged=summary.acknowledged,
        audience=summary.audience,
    )


def _texts(body: NoticeRequest) -> dict[str, NoticeText]:
    return {k: NoticeText(title=t.title, body=t.body) for k, t in body.texts.items()}


async def _summary(use_case: ManageNotices, public_id: str) -> NoticeAdminResponse:
    for summary in await use_case.list_all():
        if str(summary.notice.public_id) == public_id:
            return _notice_admin(summary)
    raise AssertionError("A saved notice is listed.")


@router.get("/admin/notices", response_model=list[NoticeAdminResponse])
async def list_notices(
    _user: User = Depends(_read), use_case: ManageNotices = Depends(get_manage_notices)
) -> list[NoticeAdminResponse]:
    return [_notice_admin(s) for s in await use_case.list_all()]


@router.post(
    "/admin/notices", response_model=NoticeAdminResponse, status_code=status.HTTP_201_CREATED
)
async def create_notice(
    body: NoticeRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageNotices = Depends(get_manage_notices),
) -> NoticeAdminResponse:
    saved = await use_case.create(actor, _texts(body), body.active, context=context)
    return await _summary(use_case, str(saved.public_id))


@router.put("/admin/notices/{notice_id}", response_model=NoticeAdminResponse)
async def update_notice(
    notice_id: str,
    body: NoticeRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageNotices = Depends(get_manage_notices),
) -> NoticeAdminResponse:
    saved = await use_case.update(actor, notice_id, _texts(body), body.active, context=context)
    return await _summary(use_case, str(saved.public_id))


@router.delete("/admin/notices/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notice(
    notice_id: str,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageNotices = Depends(get_manage_notices),
) -> None:
    await use_case.delete(actor, notice_id, context=context)


@router.get(
    "/admin/notices/{notice_id}/acknowledgements",
    response_model=AcknowledgementOverviewResponse,
)
async def notice_acknowledgements(
    notice_id: str,
    _user: User = Depends(_read),
    use_case: ManageNotices = Depends(get_manage_notices),
) -> AcknowledgementOverviewResponse:
    overview = await use_case.overview(notice_id)
    return AcknowledgementOverviewResponse(
        notice_id=overview.notice.public_id,
        acknowledged=[
            AcknowledgementResponse(user=_person(u), acknowledged_at=at)
            for u, at in overview.acknowledged
        ],
        pending=[_person(u) for u in overview.pending],
    )


# ── Notices: the signed-in user ───────────────────────────────────────


@router.get("/notices/pending", response_model=list[NoticeResponse])
async def pending_notices(
    locale: str | None = Query(None, pattern="^(en-GB|de-AT)$"),
    user: User = Depends(get_current_user),
    use_case: OwnNotices = Depends(get_own_notices),
) -> list[NoticeResponse]:
    """Active notices the user has not acknowledged, oldest first, in the
    requested locale (default: the user's own language)."""
    wanted = locale or ("de-AT" if user.language.value == "deAT" else "en-GB")
    answer: list[NoticeResponse] = []
    for notice in await use_case.pending(user):
        served, text = notice_text(notice, wanted)
        answer.append(
            NoticeResponse(
                id=notice.public_id,
                locale=served,
                title=text.title,
                body=text.body,
                created=notice.created,
            )
        )
    return answer


@router.post("/notices/{notice_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
async def acknowledge_notice(
    notice_id: str,
    user: User = Depends(get_current_user),
    use_case: OwnNotices = Depends(get_own_notices),
) -> None:
    await use_case.acknowledge(user, notice_id)
