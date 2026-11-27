"""
/api/v1/web: the admin area's feature switches, retention, maintenance,
mail templates, "back up now", restore guidance and log viewer, the legal
pages, and each user's privacy statement acknowledgement and consents.
Reading admin sections needs read:settings, changing them write:settings.
"""

import logging

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import Query
from fastapi import Response
from fastapi import UploadFile
from fastapi import status

from src.platform.adapters.inbound.api.auth_deps import get_current_user
from src.platform.adapters.inbound.api.auth_deps import get_request_context
from src.platform.adapters.inbound.api.auth_deps import get_web_identity
from src.platform.adapters.inbound.api.auth_deps import require_permission
from src.platform.adapters.inbound.api.deps import get_instance_facts
from src.platform.adapters.inbound.api.deps import get_logout
from src.platform.adapters.inbound.api.deps import get_manage_legal
from src.platform.adapters.inbound.api.deps import get_manage_mail_templates
from src.platform.adapters.inbound.api.deps import get_manage_own_consents
from src.platform.adapters.inbound.api.deps import get_manage_settings
from src.platform.adapters.inbound.api.deps import get_own_privacy
from src.platform.adapters.inbound.api.deps import get_read_storage_status
from src.platform.adapters.inbound.api.deps import get_recent_logs
from src.platform.adapters.inbound.api.deps import get_request_backup_now
from src.platform.adapters.inbound.api.schemas.operations_schema import AlertResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import BackupRetentionResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import ConsentResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import ContentLocale
from src.platform.adapters.inbound.api.schemas.operations_schema import LegalDraftResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import LegalPageResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import LegalPublishRequest
from src.platform.adapters.inbound.api.schemas.operations_schema import LegalVersionResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import LogEntryResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import MailTemplateKindResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import MailTemplateLocaleResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import MailTemplatePreviewResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import MailTemplateTextSchema
from src.platform.adapters.inbound.api.schemas.operations_schema import PrivacyAcknowledgementEntry
from src.platform.adapters.inbound.api.schemas.operations_schema import (
    PrivacyAcknowledgementOverviewResponse,
)
from src.platform.adapters.inbound.api.schemas.operations_schema import PrivacyAcknowledgeRequest
from src.platform.adapters.inbound.api.schemas.operations_schema import PrivacyStatusResponse
from src.platform.adapters.inbound.api.schemas.operations_schema import RestoreStepResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import FeatureSettingsSchema
from src.platform.adapters.inbound.api.schemas.settings_schema import MaintenanceRequest
from src.platform.adapters.inbound.api.schemas.settings_schema import MaintenanceResponse
from src.platform.adapters.inbound.api.schemas.settings_schema import RetentionSettingsSchema
from src.platform.adapters.inbound.api.schemas.user_schema import UserSummaryResponse
from src.platform.application.dto.context import RequestContext
from src.platform.application.use_cases.account.legal_and_consents import ConsentState
from src.platform.application.use_cases.account.legal_and_consents import ManageLegal
from src.platform.application.use_cases.account.legal_and_consents import ManageOwnConsents
from src.platform.application.use_cases.account.legal_and_consents import OwnPrivacy
from src.platform.application.use_cases.account.legal_and_consents import PrivacyAcknowledgement
from src.platform.application.use_cases.account.legal_and_consents import RenderedLegal
from src.platform.application.use_cases.admin.mail_templates import ManageMailTemplates
from src.platform.application.use_cases.admin.operations import RequestBackupNow
from src.platform.application.use_cases.admin.operations import restore_guidance
from src.platform.application.use_cases.admin.settings import ManageSettings
from src.platform.application.use_cases.admin.system import ReadStorageStatus
from src.platform.application.use_cases.auth.logout import Logout
from src.platform.application.use_cases.auth.validate_web_token import WebIdentity
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.entities.settings import MailTemplateText
from src.platform.domain.entities.settings import RetentionSettings
from src.platform.domain.entities.user import User
from src.platform.domain.value_objects.mail import ALERTS
from src.platform.domain.value_objects.mail import MailTemplateKind
from src.platform.domain.value_objects.permission import Permission
from src.platform.infrastructure.logging.ring_buffer import RingBufferHandler
from src.platform.infrastructure.security.cookies import clear_session_cookie
from src.platform.ports.outbound.instance_facts import IInstanceFacts

router = APIRouter()
public_legal_router = APIRouter(tags=["public"])

_read = require_permission(Permission.READ_SETTINGS)
_write = require_permission(Permission.WRITE_SETTINGS)
_read_logs = require_permission(Permission.READ_SECURITY_LOG)


# ── Feature switches and retention ────────────────────────────────────


@router.get("/settings/features", response_model=FeatureSettingsSchema, tags=["settings"])
async def read_features(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> FeatureSettingsSchema:
    f = await use_case.features()
    return FeatureSettingsSchema(
        agents=f.agents,
        webhooks=f.webhooks,
        households=f.households,
        dinner_guests=f.dinner_guests,
        usda=f.usda,
        peering=f.peering,
    )


@router.put("/settings/features", response_model=FeatureSettingsSchema, tags=["settings"])
async def save_features(
    body: FeatureSettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> FeatureSettingsSchema:
    await use_case.save_features(actor, FeatureSettings(**body.model_dump()), context=context)
    return body


@router.get("/settings/retention", response_model=RetentionSettingsSchema, tags=["settings"])
async def read_retention(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> RetentionSettingsSchema:
    r = await use_case.retention()
    return RetentionSettingsSchema(
        security_log_days=r.security_log_days,
        agent_calls_days=r.agent_calls_days,
        webhook_deliveries_days=r.webhook_deliveries_days,
        recipe_revisions_days=r.recipe_revisions_days,
    )


@router.put("/settings/retention", response_model=RetentionSettingsSchema, tags=["settings"])
async def save_retention(
    body: RetentionSettingsSchema,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> RetentionSettingsSchema:
    await use_case.save_retention(actor, RetentionSettings(**body.model_dump()), context=context)
    return body


@router.get("/settings/backup-retention", response_model=BackupRetentionResponse, tags=["settings"])
async def read_backup_retention(
    _user: User = Depends(get_current_user), facts: IInstanceFacts = Depends(get_instance_facts)
) -> BackupRetentionResponse:
    """How long the nightly dumps keep deleted data, for every signed-in
    user, since the deletion dialogs name it."""
    retention = facts.backup_retention()
    return BackupRetentionResponse(
        keep_days=retention.keep_days, gone_by=retention.gone_by.isoformat()
    )


# ── Maintenance ───────────────────────────────────────────────────────


@router.get("/settings/maintenance", response_model=MaintenanceResponse, tags=["settings"])
async def read_maintenance(
    _user: User = Depends(_read), use_case: ManageSettings = Depends(get_manage_settings)
) -> MaintenanceResponse:
    m = await use_case.maintenance()
    return MaintenanceResponse(enabled=m.enabled, messages=m.messages, since=m.since)


@router.put("/settings/maintenance", response_model=MaintenanceResponse, tags=["settings"])
async def save_maintenance(
    body: MaintenanceRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageSettings = Depends(get_manage_settings),
) -> MaintenanceResponse:
    """Stays writable while maintenance is on, so it can be switched off."""
    m = await use_case.save_maintenance(
        actor, body.enabled, {str(k): v for k, v in body.messages.items()}, context=context
    )
    return MaintenanceResponse(enabled=m.enabled, messages=m.messages, since=m.since)


# ── Mail templates and alerts ─────────────────────────────────────────


@router.get("/settings/mail/alerts", response_model=list[AlertResponse], tags=["settings"])
async def list_alerts(_user: User = Depends(_read)) -> list[AlertResponse]:
    return [AlertResponse(kind=a.kind.value, description=a.description) for a in ALERTS.values()]


@router.get(
    "/settings/mail/templates", response_model=list[MailTemplateKindResponse], tags=["settings"]
)
async def list_mail_templates(
    _user: User = Depends(_read),
    use_case: ManageMailTemplates = Depends(get_manage_mail_templates),
) -> list[MailTemplateKindResponse]:
    return [
        MailTemplateKindResponse(
            kind=k.spec.kind.value,
            variables=list(k.spec.variables),
            sample_context=dict(k.spec.sample_context),
            templates=[
                MailTemplateLocaleResponse(
                    locale=t.locale, subject=t.subject, body=t.body, customized=t.customized
                )
                for t in k.templates
            ],
        )
        for k in await use_case.list_all()
    ]


@router.put(
    "/settings/mail/templates/{kind}", status_code=status.HTTP_204_NO_CONTENT, tags=["settings"]
)
async def save_mail_templates(
    kind: MailTemplateKind,
    body: dict[ContentLocale, MailTemplateTextSchema],
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageMailTemplates = Depends(get_manage_mail_templates),
) -> None:
    """Saves the given languages; a blank body returns to the default."""
    await use_case.save(
        actor,
        kind,
        {str(k): MailTemplateText(subject=v.subject, body=v.body) for k, v in body.items()},
        context=context,
    )


@router.post(
    "/settings/mail/templates/{kind}/preview",
    response_model=MailTemplatePreviewResponse,
    tags=["settings"],
)
async def preview_mail_template(
    kind: MailTemplateKind,
    body: MailTemplateTextSchema,
    _user: User = Depends(_read),
    use_case: ManageMailTemplates = Depends(get_manage_mail_templates),
) -> MailTemplatePreviewResponse:
    """Renders a draft with the kind's sample values, exactly as it is sent."""
    subject, html = await use_case.preview(
        kind, MailTemplateText(subject=body.subject, body=body.body)
    )
    return MailTemplatePreviewResponse(subject=subject, html=html)


@router.get(
    "/settings/mail/templates/{kind}/default",
    response_model=MailTemplateLocaleResponse,
    tags=["settings"],
)
async def default_mail_template(
    kind: MailTemplateKind,
    locale: ContentLocale = Query("en-GB"),
    _user: User = Depends(_read),
    use_case: ManageMailTemplates = Depends(get_manage_mail_templates),
) -> MailTemplateLocaleResponse:
    text = use_case.default(kind, locale)
    return MailTemplateLocaleResponse(
        locale=locale, subject=text.subject, body=text.body, customized=False
    )


@router.post(
    "/settings/mail/templates/{kind}/import",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["settings"],
)
async def import_mail_template(
    kind: MailTemplateKind,
    locale: ContentLocale = Form(...),
    file: UploadFile = File(...),
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageMailTemplates = Depends(get_manage_mail_templates),
) -> None:
    """Saves an HTML template file for one language; its <title> is the subject."""
    await use_case.import_file(actor, kind, locale, await file.read(), context=context)


@router.get(
    "/settings/mail/templates/{kind}/export",
    response_class=Response,
    responses={200: {"content": {"text/html": {}}}},
    tags=["settings"],
)
async def export_mail_template(
    kind: MailTemplateKind,
    locale: ContentLocale = Query("en-GB"),
    _user: User = Depends(_read),
    use_case: ManageMailTemplates = Depends(get_manage_mail_templates),
) -> Response:
    name, html = await use_case.export_file(kind, locale)
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ── Backups and logs ──────────────────────────────────────────────────


@router.post("/admin/backups/run", status_code=status.HTTP_202_ACCEPTED, tags=["admin-system"])
async def back_up_now(
    _actor: User = Depends(_write), use_case: RequestBackupNow = Depends(get_request_backup_now)
) -> None:
    """Asks the backup sidecar for a dump now; it starts within seconds.
    409 while a request is still waiting, 503 without the sidecar."""
    await use_case.run()


@router.get(
    "/admin/backups/restore-guidance",
    response_model=list[RestoreStepResponse],
    tags=["admin-system"],
)
async def read_restore_guidance(
    locale: ContentLocale = Query("en-GB"),
    _user: User = Depends(_read),
    storage: ReadStorageStatus = Depends(get_read_storage_status),
) -> list[RestoreStepResponse]:
    status_ = await storage.run()
    newest = status_.backups.files[0].name if status_.backups.files else None
    return [
        RestoreStepResponse(text=s.text, command=s.command)
        for s in restore_guidance(locale, newest)
    ]


@router.get("/admin/logs", response_model=list[LogEntryResponse], tags=["admin-system"])
async def read_logs(
    level: str = Query("WARNING", pattern="^(WARNING|ERROR|CRITICAL)$"),
    limit: int = Query(200, ge=1, le=500),
    _user: User = Depends(_read_logs),
    logs: RingBufferHandler = Depends(get_recent_logs),
) -> list[LogEntryResponse]:
    """The recent warnings and errors of the backend worker that answers,
    with secrets redacted."""
    return [
        LogEntryResponse(time=e.time, level=e.level, logger=e.logger, message=e.message)
        for e in logs.recent(min_level=logging.getLevelName(level), limit=limit)
    ]


# ── Legal pages ───────────────────────────────────────────────────────


def _page(page: RenderedLegal) -> LegalPageResponse:
    return LegalPageResponse(
        kind=page.kind.value,
        version=page.version,
        locale=page.locale,
        body=page.body,
        published_at=page.published_at,
    )


@public_legal_router.get("/legal/{kind}", response_model=LegalPageResponse)
async def read_legal_page(
    kind: LegalKind,
    locale: ContentLocale = Query("en-GB"),
    use_case: ManageLegal = Depends(get_manage_legal),
) -> LegalPageResponse:
    """The current imprint or privacy statement, without a session, since
    the login page links both."""
    return _page(await use_case.current(kind, locale))


@router.get(
    "/admin/legal/{kind}/versions", response_model=list[LegalVersionResponse], tags=["legal"]
)
async def list_legal_versions(
    kind: LegalKind,
    _user: User = Depends(_read),
    use_case: ManageLegal = Depends(get_manage_legal),
) -> list[LegalVersionResponse]:
    return [
        LegalVersionResponse(
            id=v.public_id,
            kind=v.kind.value,
            version=v.version,
            texts=v.texts,
            published_at=v.published_at,
            privacy_mode=v.privacy_mode.mode.value if v.privacy_mode else None,
            default_visibility=v.privacy_mode.default_visibility if v.privacy_mode else None,
            allow_public_recipes=v.privacy_mode.allow_public_recipes if v.privacy_mode else None,
            peering_enabled=v.privacy_mode.peering_enabled if v.privacy_mode else None,
        )
        for v in await use_case.history(kind)
    ]


@router.post(
    "/admin/legal/{kind}",
    response_model=LegalPageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["legal"],
)
async def publish_legal_page(
    kind: LegalKind,
    body: LegalPublishRequest,
    actor: User = Depends(_write),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageLegal = Depends(get_manage_legal),
) -> LegalPageResponse:
    """Publishes the next version. A new privacy statement version asks
    every user to acknowledge it again."""
    saved = await use_case.publish(
        actor, kind, {str(k): v for k, v in body.texts.items()}, context=context
    )
    return _page(await use_case.current(saved.kind, actor_locale(actor)))


@router.get("/admin/legal/privacy/draft", response_model=LegalDraftResponse, tags=["legal"])
async def privacy_statement_draft(
    locale: ContentLocale = Query("en-GB"),
    _user: User = Depends(_read),
    use_case: ManageLegal = Depends(get_manage_legal),
) -> LegalDraftResponse:
    """A draft written from this instance's configuration, to edit and
    publish. `{{ privacy_mode }}` marks where the privacy mode section goes."""
    return LegalDraftResponse(locale=locale, body=await use_case.draft(locale))


@router.get(
    "/admin/legal/privacy/acknowledgements",
    response_model=PrivacyAcknowledgementOverviewResponse,
    tags=["legal"],
)
async def privacy_acknowledgements(
    _user: User = Depends(_read),
    use_case: ManageLegal = Depends(get_manage_legal),
) -> PrivacyAcknowledgementOverviewResponse:
    """Which person acknowledged which privacy statement version: those on
    the current version, and those still asked with the version they
    acknowledged last."""
    overview = await use_case.acknowledgements()

    def entry(e: PrivacyAcknowledgement) -> PrivacyAcknowledgementEntry:
        return PrivacyAcknowledgementEntry(
            user=UserSummaryResponse(id=e.user.public_id, display_name=e.user.display_name),
            version=e.version,
            acknowledged_at=e.acknowledged_at,
        )

    return PrivacyAcknowledgementOverviewResponse(
        current_version=overview.current_version,
        acknowledged=[entry(e) for e in overview.acknowledged],
        pending=[entry(e) for e in overview.pending],
    )


def actor_locale(user: User) -> str:
    return "de-AT" if user.language.value == "deAT" else "en-GB"


# ── The signed-in user: privacy statement and consents ───────────────


@router.get("/users/me/privacy", response_model=PrivacyStatusResponse, tags=["account"])
async def own_privacy_status(
    user: User = Depends(get_current_user), use_case: OwnPrivacy = Depends(get_own_privacy)
) -> PrivacyStatusResponse:
    s = await use_case.status(user)
    return PrivacyStatusResponse(
        current_version=s.current_version,
        acknowledged_version=s.acknowledged_version,
        pending=s.pending,
    )


@router.post(
    "/users/me/privacy/acknowledge", status_code=status.HTTP_204_NO_CONTENT, tags=["account"]
)
async def acknowledge_privacy(
    body: PrivacyAcknowledgeRequest,
    user: User = Depends(get_current_user),
    use_case: OwnPrivacy = Depends(get_own_privacy),
) -> None:
    """409 when the version is not the current one any more."""
    await use_case.acknowledge(user, body.version)


@router.post("/users/me/privacy/decline", status_code=status.HTTP_204_NO_CONTENT, tags=["account"])
async def decline_privacy(
    response: Response,
    identity: WebIdentity = Depends(get_web_identity),
    context: RequestContext = Depends(get_request_context),
    logout: Logout = Depends(get_logout),
) -> None:
    """Declining signs the user out; they are asked again at the next login."""
    await logout.execute(identity, context=context)
    clear_session_cookie(response)


def _consents(states: list[ConsentState]) -> list[ConsentResponse]:
    return [
        ConsentResponse(kind=s.kind, granted=s.granted_at is not None, granted_at=s.granted_at)
        for s in states
    ]


@router.get("/users/me/consents", response_model=list[ConsentResponse], tags=["account"])
async def own_consents(user: User = Depends(get_current_user)) -> list[ConsentResponse]:
    return _consents(ManageOwnConsents.state(user))


@router.put("/users/me/consents/{kind}", response_model=list[ConsentResponse], tags=["account"])
async def grant_consent(
    kind: str,
    user: User = Depends(get_current_user),
    use_case: ManageOwnConsents = Depends(get_manage_own_consents),
) -> list[ConsentResponse]:
    return _consents(await use_case.grant(user, kind))


@router.delete("/users/me/consents/{kind}", response_model=list[ConsentResponse], tags=["account"])
async def withdraw_consent(
    kind: str,
    user: User = Depends(get_current_user),
    context: RequestContext = Depends(get_request_context),
    use_case: ManageOwnConsents = Depends(get_manage_own_consents),
) -> list[ConsentResponse]:
    """Withdrawing ai_agents revokes the user's agent tokens; withdrawing
    health_data deletes their allergies, intolerances and diets."""
    return _consents(await use_case.withdraw(user, kind, context=context))
