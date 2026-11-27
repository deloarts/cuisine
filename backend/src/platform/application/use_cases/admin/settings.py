"""Reading and saving the admin settings, one section at a time."""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import asdict
from dataclasses import replace

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.file_access import FileAccess
from src.platform.application.services.mailer import Mailer
from src.platform.application.services.mailer import content_locale
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.services.webhook_publisher import WebhookPublisher
from src.platform.domain.entities.settings import AgentSettings
from src.platform.domain.entities.settings import BannerSettings
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.entities.settings import GeneralSettings
from src.platform.domain.entities.settings import IntegrationSettings
from src.platform.domain.entities.settings import MailSettings
from src.platform.domain.entities.settings import MaintenanceSettings
from src.platform.domain.entities.settings import NotificationSettings
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.settings import RetentionSettings
from src.platform.domain.entities.settings import SecuritySettings
from src.platform.domain.entities.settings import ShoppingSettings
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import InvalidSettingsError
from src.platform.domain.exceptions import MailNotConfiguredError
from src.platform.domain.services.settings_rules import validate_agents
from src.platform.domain.services.settings_rules import validate_banner
from src.platform.domain.services.settings_rules import validate_general
from src.platform.domain.services.settings_rules import validate_integrations
from src.platform.domain.services.settings_rules import validate_mail
from src.platform.domain.services.settings_rules import validate_maintenance
from src.platform.domain.services.settings_rules import validate_privacy
from src.platform.domain.services.settings_rules import validate_retention
from src.platform.domain.services.settings_rules import validate_security
from src.platform.domain.services.settings_rules import validate_shopping
from src.platform.domain.value_objects.mail import AlertKind
from src.platform.domain.value_objects.mail import MailTemplateKind
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.domain.value_objects.webhook_event import SETTINGS_CHANGED
from src.platform.ports.outbound.mail_service import IMailService
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.stored_file_repository import IStoredFileRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# Called with the privacy settings before and after a save, inside its
# transaction.
PrivacySavedHook = Callable[[PrivacySettings, PrivacySettings], Awaitable[None]]
# Called with the feature switches before and after a save that changed
# them, inside its transaction.
FeaturesSavedHook = Callable[[FeatureSettings, FeatureSettings], Awaitable[None]]


def _changed_fields(before: object, after: object) -> list[str]:
    old, new = asdict(before), asdict(after)  # type: ignore[call-overload]
    return sorted(k for k in new if old.get(k) != new[k])


class ManageSettings:
    def __init__(
        self,
        *,
        settings_repo: ISettingsRepository,
        mail: IMailService,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        files: IStoredFileRepository | None = None,
        file_access: FileAccess | None = None,
        webhooks: WebhookPublisher | None = None,
        mailer: Mailer | None = None,
        on_maintenance_changed: Callable[[], None] | None = None,
        on_privacy_changed: Callable[[User], Awaitable[object]] | None = None,
        on_privacy_saved: list[PrivacySavedHook] | None = None,
        on_features_saved: list[FeaturesSavedHook] | None = None,
    ) -> None:
        self._on_privacy_saved = on_privacy_saved or []
        self._on_features_saved = on_features_saved or []
        self._mailer = mailer
        self._on_maintenance_changed = on_maintenance_changed
        self._on_privacy_changed = on_privacy_changed
        self._settings = settings_repo
        self._mail = mail
        self._audit = audit
        self._uow = uow
        self._files = files
        self._file_access = file_access
        self._webhooks = webhooks

    async def _audit_change(
        self, actor: User, section: str, fields: list[str], context: RequestContext
    ) -> None:
        await self._audit.record(
            SecurityEventType.SETTINGS_CHANGED,
            actor=actor,
            context=context,
            detail={"section": section, "fields": fields},
        )
        if self._webhooks is not None and fields:
            # Names the section and fields only, never a value: settings
            # hold the mail password and keys.
            await self._webhooks.publish(
                SETTINGS_CHANGED.key, {"section": section, "fields": fields}
            )
        await self._uow.commit()

    async def general(self) -> GeneralSettings:
        return await self._settings.get_general()

    async def security(self) -> SecuritySettings:
        return await self._settings.get_security()

    async def mail(self) -> MailSettings:
        return await self._settings.get_mail()

    async def save_general(
        self, actor: User, new: GeneralSettings, *, context: RequestContext
    ) -> GeneralSettings:
        validate_general(new)
        if new.login_background_file_id is not None:
            await self._assert_image(actor, new.login_background_file_id, "login background")
        before = await self._settings.get_general()
        await self._settings.save_general(new)
        await self._audit_change(actor, "general", _changed_fields(before, new), context)
        return new

    async def save_security(
        self, actor: User, new: SecuritySettings, *, context: RequestContext
    ) -> SecuritySettings:
        validate_security(new)
        before = await self._settings.get_security()
        await self._settings.save_security(new)
        await self._audit_change(actor, "security", _changed_fields(before, new), context)
        return new

    async def save_mail(
        self,
        actor: User,
        new: MailSettings,
        *,
        keep_password: bool,
        context: RequestContext,
    ) -> MailSettings:
        """With `keep_password` the stored password stays, since the API
        never sends it out and a form cannot echo it back."""
        before = await self._settings.get_mail()
        if keep_password:
            new = replace(new, password=before.password)
        validate_mail(new)
        await self._settings.save_mail(new)
        fields = _changed_fields(before, new)
        await self._audit_change(actor, "mail", fields, context)
        return new

    async def integrations(self) -> IntegrationSettings:
        return await self._settings.get_integrations()

    async def save_integrations(
        self,
        actor: User,
        new: IntegrationSettings,
        *,
        keep_key: bool,
        context: RequestContext,
    ) -> IntegrationSettings:
        """With `keep_key` the stored USDA key stays, like the mail password."""
        before = await self._settings.get_integrations()
        if keep_key:
            new = replace(new, usda_api_key=before.usda_api_key)
        validate_integrations(new)
        await self._settings.save_integrations(new)
        await self._audit_change(actor, "integrations", _changed_fields(before, new), context)
        return new

    async def privacy(self) -> PrivacySettings:
        return await self._settings.get_privacy()

    async def save_privacy(
        self, actor: User, new: PrivacySettings, *, context: RequestContext
    ) -> PrivacySettings:
        """Any change of the privacy mode, the public recipes switch
        included, publishes a new privacy statement version, so every user
        acknowledges the new mode. The search engine switch alone does not,
        since the statement does not depend on it. Existing recipes are never
        rewritten."""
        validate_privacy(new, peering=(await self._settings.get_features()).peering)
        before = await self._settings.get_privacy()
        await self._settings.save_privacy(new)
        fields = _changed_fields(before, new)
        if set(fields) - {"index_public_recipes"} and self._on_privacy_changed is not None:
            await self._on_privacy_changed(actor)
        if fields:
            for hook in self._on_privacy_saved:
                await hook(before, new)
        await self._audit_change(actor, "privacy", fields, context)
        return new

    async def shopping(self) -> ShoppingSettings:
        return await self._settings.get_shopping()

    async def save_shopping(
        self, actor: User, new: ShoppingSettings, *, context: RequestContext
    ) -> ShoppingSettings:
        validate_shopping(new)
        before = await self._settings.get_shopping()
        await self._settings.save_shopping(new)
        await self._audit_change(actor, "shopping", _changed_fields(before, new), context)
        return new

    async def agents(self) -> AgentSettings:
        return await self._settings.get_agents()

    async def save_agents(
        self, actor: User, new: AgentSettings, *, context: RequestContext
    ) -> AgentSettings:
        validate_agents(new)
        before = await self._settings.get_agents()
        await self._settings.save_agents(new)
        await self._audit_change(actor, "agents", _changed_fields(before, new), context)
        return new

    async def _assert_image(self, actor: User, public_id: str, label: str) -> None:
        """A branding image is served to everyone, so it must be one the
        administrator may read already, never a private recipe's photo."""
        stored = await self._files.get_by_public_id(public_id) if self._files else None
        readable = stored is not None and (
            self._file_access is None or await self._file_access.may_read(actor, stored)
        )
        if stored is None or not readable:
            raise InvalidSettingsError(f"The {label} is not a stored file.")
        if not stored.content_type.startswith("image/"):
            raise InvalidSettingsError(f"The {label} must be an image.")

    async def notifications(self) -> NotificationSettings:
        return await self._settings.get_notifications()

    async def save_notifications(
        self, actor: User, new: NotificationSettings, *, context: RequestContext
    ) -> NotificationSettings:
        before = await self._settings.get_notifications()
        await self._settings.save_notifications(new)
        await self._audit_change(actor, "notifications", _changed_fields(before, new), context)
        return new

    async def banner(self) -> BannerSettings:
        return await self._settings.get_banner()

    async def save_banner(
        self, actor: User, new: BannerSettings, *, context: RequestContext
    ) -> BannerSettings:
        validate_banner(new)
        before = await self._settings.get_banner()
        await self._settings.save_banner(new)
        await self._audit_change(actor, "banner", _changed_fields(before, new), context)
        return new

    async def features(self) -> FeatureSettings:
        return await self._settings.get_features()

    async def save_features(
        self, actor: User, new: FeatureSettings, *, context: RequestContext
    ) -> FeatureSettings:
        """Switching peering on or off changes who may receive recipes (the
        peers visibility applies only while it is on), so it publishes a new
        privacy statement version like a change of the privacy mode."""
        before = await self._settings.get_features()
        await self._settings.save_features(new)
        fields = _changed_fields(before, new)
        if "peering" in fields and self._on_privacy_changed is not None:
            await self._on_privacy_changed(actor)
        if fields:
            for hook in self._on_features_saved:
                await hook(before, new)
        await self._audit_change(actor, "features", fields, context)
        return new

    async def retention(self) -> RetentionSettings:
        return await self._settings.get_retention()

    async def save_retention(
        self, actor: User, new: RetentionSettings, *, context: RequestContext
    ) -> RetentionSettings:
        validate_retention(new)
        before = await self._settings.get_retention()
        await self._settings.save_retention(new)
        await self._audit_change(actor, "retention", _changed_fields(before, new), context)
        return new

    async def maintenance(self) -> MaintenanceSettings:
        return await self._settings.get_maintenance()

    async def save_maintenance(
        self, actor: User, enabled: bool, messages: dict[str, str], *, context: RequestContext
    ) -> MaintenanceSettings:
        before = await self._settings.get_maintenance()
        new = MaintenanceSettings(
            enabled=enabled,
            messages={k: v.strip() for k, v in messages.items() if v.strip()},
            since=(before.since if before.enabled else now_utc()) if enabled else None,
        )
        validate_maintenance(new)
        await self._settings.save_maintenance(new)
        await self._audit_change(actor, "maintenance", _changed_fields(before, new), context)
        if self._on_maintenance_changed is not None:
            self._on_maintenance_changed()
        if before.enabled != enabled and self._mailer is not None:
            state = "on" if enabled else "off"
            await self._mailer.alert(
                AlertKind.MAINTENANCE_SWITCHED,
                f"{actor.full_name} switched maintenance mode {state}.",
            )
        return new

    async def send_test_mail(self, actor: User, *, to: str | None = None) -> None:
        """Sends the test mail template to `to`, the acting user by default,
        in the acting user's language."""
        if self._mailer is None:
            raise MailNotConfiguredError("Mail delivery is not configured.")
        await self._mailer.send_template(
            MailTemplateKind.TEST_MAIL,
            to=to or actor.email,
            locale=content_locale(actor.language.value),
            context={"full_name": actor.full_name},
        )
