"""
The admin settings, one JSON row per section. Reading merges the stored
values over the dataclass defaults and ignores keys the dataclass no longer
has, so adding or removing a setting needs no migration. The mail password
and the USDA API key are encrypted inside the JSON with secret_box.
"""

from dataclasses import asdict
from dataclasses import fields
from datetime import datetime
from typing import Any
from uuid import UUID
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.outbound.persistence.models.settings_model import SettingsModel
from src.platform.domain.entities.settings import GENERAL_ENUM_FIELDS
from src.platform.domain.entities.settings import AgentSettings
from src.platform.domain.entities.settings import BannerSettings
from src.platform.domain.entities.settings import FeatureSettings
from src.platform.domain.entities.settings import GeneralSettings
from src.platform.domain.entities.settings import IntegrationSettings
from src.platform.domain.entities.settings import MailSettings
from src.platform.domain.entities.settings import MailTemplateSettings
from src.platform.domain.entities.settings import MailTemplateText
from src.platform.domain.entities.settings import MaintenanceSettings
from src.platform.domain.entities.settings import NotificationSettings
from src.platform.domain.entities.settings import PrivacySettings
from src.platform.domain.entities.settings import RetentionSettings
from src.platform.domain.entities.settings import SecuritySettings
from src.platform.domain.entities.settings import ShoppingSettings
from src.platform.domain.value_objects.display import BannerSeverity
from src.platform.infrastructure.security.secret_box import SecretDecryptionError
from src.platform.infrastructure.security.secret_box import decrypt_secret
from src.platform.infrastructure.security.secret_box import encrypt_secret
from src.shared_kernel.domain.services.clock import now_utc

# The settings row that holds the instance's own identity. It is no admin
# section: nothing reads it as a dataclass and no route writes it.
INSTANCE_SECTION = "instance"


def _uuid_or_none(value: object) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except ValueError:
        return None


class SqlAlchemySettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def _load(self, section: str) -> dict[str, Any]:
        row = await self._db.get(SettingsModel, section)
        return dict(row.data) if row is not None else {}

    async def _store(self, section: str, data: dict[str, Any]) -> None:
        row = await self._db.get(SettingsModel, section)
        if row is None:
            # Two writers can find a section missing at once, such as the
            # nightly jobs and the shopping purge saving the job state on a
            # fresh database. The insert runs in a savepoint, so the loser
            # updates the winner's row instead of failing.
            try:
                async with self._db.begin_nested():
                    self._db.add(SettingsModel(section=section, data=data, changed=now_utc()))
                return
            except IntegrityError:
                row = await self._db.get(SettingsModel, section, populate_existing=True)
                if row is None:
                    raise
        row.data = data
        row.changed = now_utc()
        await self._db.flush()

    @staticmethod
    def _known(cls: type[Any], data: dict[str, Any]) -> dict[str, Any]:
        names = {f.name for f in fields(cls)}
        return {k: v for k, v in data.items() if k in names}

    async def get_general(self) -> GeneralSettings:
        data = self._known(GeneralSettings, await self._load("general"))
        # A stored value an enum no longer knows falls back to the default.
        for name, enum in GENERAL_ENUM_FIELDS.items():
            if name in data:
                try:
                    data[name] = enum(data[name])
                except ValueError:
                    data.pop(name)
        return GeneralSettings(**data)

    async def get_security(self) -> SecuritySettings:
        return SecuritySettings(**self._known(SecuritySettings, await self._load("security")))

    async def get_mail(self) -> MailSettings:
        data = self._known(MailSettings, await self._load("mail"))
        stored_password = str(data.get("password") or "")
        if stored_password:
            try:
                data["password"] = decrypt_secret(stored_password)
            except SecretDecryptionError:
                data["password"] = ""
        return MailSettings(**data)

    async def save_general(self, settings: GeneralSettings) -> None:
        data = asdict(settings)
        for name in GENERAL_ENUM_FIELDS:
            data[name] = getattr(settings, name).value
        await self._store("general", data)

    async def save_security(self, settings: SecuritySettings) -> None:
        await self._store("security", asdict(settings))

    async def save_mail(self, settings: MailSettings) -> None:
        data = asdict(settings)
        data["password"] = encrypt_secret(settings.password) if settings.password else ""
        await self._store("mail", data)

    async def get_integrations(self) -> IntegrationSettings:
        data = self._known(IntegrationSettings, await self._load("integrations"))
        stored_key = str(data.get("usda_api_key") or "")
        if stored_key:
            try:
                data["usda_api_key"] = decrypt_secret(stored_key)
            except SecretDecryptionError:
                data.pop("usda_api_key")
        integrations = IntegrationSettings(**data)
        integrations.usda_enabled = (await self.get_features()).usda
        return integrations

    async def save_integrations(self, settings: IntegrationSettings) -> None:
        data = asdict(settings)
        data["usda_api_key"] = (
            encrypt_secret(settings.usda_api_key) if settings.usda_api_key else ""
        )
        await self._store("integrations", data)
        await self._set_feature("usda", settings.usda_enabled)

    async def get_agents(self) -> AgentSettings:
        agents = AgentSettings(**self._known(AgentSettings, await self._load("agents")))
        agents.enabled = (await self.get_features()).agents
        return agents

    async def save_agents(self, settings: AgentSettings) -> None:
        await self._store("agents", asdict(settings))
        await self._set_feature("agents", settings.enabled)

    async def get_privacy(self) -> PrivacySettings:
        return PrivacySettings(**self._known(PrivacySettings, await self._load("privacy")))

    async def save_privacy(self, settings: PrivacySettings) -> None:
        await self._store("privacy", asdict(settings))

    async def get_shopping(self) -> ShoppingSettings:
        return ShoppingSettings(**self._known(ShoppingSettings, await self._load("shopping")))

    async def save_shopping(self, settings: ShoppingSettings) -> None:
        await self._store("shopping", asdict(settings))

    async def get_notifications(self) -> NotificationSettings:
        notifications = NotificationSettings(
            **self._known(NotificationSettings, await self._load("notifications"))
        )
        notifications.webhooks_enabled = (await self.get_features()).webhooks
        return notifications

    async def save_notifications(self, settings: NotificationSettings) -> None:
        await self._store("notifications", asdict(settings))
        await self._set_feature("webhooks", settings.webhooks_enabled)

    async def get_banner(self) -> BannerSettings:
        data = self._known(BannerSettings, await self._load("banner"))
        try:
            data["severity"] = BannerSeverity(data.get("severity", BannerSeverity.INFO.value))
        except ValueError:
            data.pop("severity")
        for name in ("starts_at", "ends_at"):
            raw = data.get(name)
            data[name] = datetime.fromisoformat(raw) if isinstance(raw, str) and raw else None
        data["messages"] = {
            str(k): str(v) for k, v in dict(data.get("messages") or {}).items() if v
        }
        return BannerSettings(**data)

    async def save_banner(self, settings: BannerSettings) -> None:
        data = asdict(settings)
        data["severity"] = settings.severity.value
        data["starts_at"] = settings.starts_at.isoformat() if settings.starts_at else None
        data["ends_at"] = settings.ends_at.isoformat() if settings.ends_at else None
        await self._store("banner", data)

    # The feature switches are the one source of truth for the agents,
    # webhooks and USDA flags, which their own sections mirror.

    async def get_features(self) -> FeatureSettings:
        stored = await self._load("features")
        if not stored:
            # Before the switches were saved once, the flags of the older
            # sections still count.
            stored = {
                "agents": (await self._load("agents")).get("enabled", True),
                "webhooks": (await self._load("notifications")).get("webhooks_enabled", True),
                "usda": (await self._load("integrations")).get("usda_enabled", True),
            }
        return FeatureSettings(**self._known(FeatureSettings, stored))

    async def save_features(self, settings: FeatureSettings) -> None:
        await self._store("features", asdict(settings))

    async def _set_feature(self, name: str, value: bool) -> None:
        features = await self.get_features()
        setattr(features, name, value)
        await self.save_features(features)

    async def get_maintenance(self) -> MaintenanceSettings:
        data = self._known(MaintenanceSettings, await self._load("maintenance"))
        raw = data.get("since")
        data["since"] = datetime.fromisoformat(raw) if isinstance(raw, str) and raw else None
        data["messages"] = {str(k): str(v) for k, v in dict(data.get("messages") or {}).items()}
        return MaintenanceSettings(**data)

    async def save_maintenance(self, settings: MaintenanceSettings) -> None:
        data = asdict(settings)
        data["since"] = settings.since.isoformat() if settings.since else None
        await self._store("maintenance", data)

    async def get_retention(self) -> RetentionSettings:
        return RetentionSettings(**self._known(RetentionSettings, await self._load("retention")))

    async def save_retention(self, settings: RetentionSettings) -> None:
        await self._store("retention", asdict(settings))

    async def get_mail_templates(self) -> MailTemplateSettings:
        overrides: dict[str, dict[str, MailTemplateText]] = {}
        stored = dict((await self._load("mail_templates")).get("overrides") or {})
        for key, locales in stored.items():
            if not isinstance(locales, dict):
                continue
            for locale, text in locales.items():
                if isinstance(text, dict):
                    overrides.setdefault(str(key), {})[str(locale)] = MailTemplateText(
                        subject=str(text.get("subject", "")), body=str(text.get("body", ""))
                    )
        return MailTemplateSettings(overrides=overrides)

    async def save_mail_templates(self, settings: MailTemplateSettings) -> None:
        await self._store(
            "mail_templates",
            {
                "overrides": {
                    key: {loc: {"subject": t.subject, "body": t.body} for loc, t in locs.items()}
                    for key, locs in settings.overrides.items()
                }
            },
        )

    async def get_job_state(self) -> dict[str, object]:
        return await self._load("job_state")

    async def instance_id(self) -> UUID:
        """The instance's own id, created on the first call and never
        changed afterwards. Two first calls at once agree: the loser of the
        insert reads the winner's id instead of writing its own."""
        stored = _uuid_or_none((await self._load(INSTANCE_SECTION)).get("instance_id"))
        if stored is not None:
            return stored
        created = uuid4()
        try:
            async with self._db.begin_nested():
                row = await self._db.get(SettingsModel, INSTANCE_SECTION)
                if row is None:
                    self._db.add(
                        SettingsModel(
                            section=INSTANCE_SECTION,
                            data={"instance_id": str(created)},
                            changed=now_utc(),
                        )
                    )
                else:
                    # The row exists but holds no readable id, so no id was
                    # ever handed out and one may be written.
                    row.data = {**dict(row.data), "instance_id": str(created)}
                    row.changed = now_utc()
            return created
        except IntegrityError:
            row = await self._db.get(SettingsModel, INSTANCE_SECTION, populate_existing=True)
            found = _uuid_or_none(dict(row.data).get("instance_id")) if row is not None else None
            if found is None:
                raise
            return found

    async def save_job_state(self, state: dict[str, object]) -> None:
        await self._store("job_state", dict(state))
