"""
Legal pages and the privacy statement: publishing versions, the default
draft from the instance's configuration, each user's acknowledgement, and
the voluntary consents a user gives or withdraws in their account.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.platform.application.dto.context import RequestContext
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.use_cases.oauth.grants import ManageOwnOAuthGrants
from src.platform.domain.entities.legal import LegalKind
from src.platform.domain.entities.legal import LegalVersion
from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import ConsentRequiredError
from src.platform.domain.exceptions import LegalPageNotFoundError
from src.platform.domain.exceptions import StalePrivacyVersionError
from src.platform.domain.services.legal_rules import acknowledgement_pending
from src.platform.domain.services.legal_rules import legal_text
from src.platform.domain.services.legal_rules import privacy_mode_of
from src.platform.domain.services.legal_rules import validate_legal_texts
from src.platform.domain.services.privacy_draft import PrivacyFacts
from src.platform.domain.services.privacy_draft import privacy_draft
from src.platform.domain.services.privacy_draft import render_privacy_statement
from src.platform.domain.value_objects.permission import Permission
from src.platform.domain.value_objects.security_event_type import SecurityEventType
from src.platform.ports.outbound.health_data_eraser import IHealthDataEraser
from src.platform.ports.outbound.instance_facts import IInstanceFacts
from src.platform.ports.outbound.repositories.legal_repository import ILegalRepository
from src.platform.ports.outbound.repositories.pat_repository import IPatRepository
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.user_repository import IUserRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

HEALTH_DATA = "health_data"
AI_AGENTS = "ai_agents"
CONSENTS = (HEALTH_DATA, AI_AGENTS)


@dataclass(frozen=True)
class RenderedLegal:
    kind: LegalKind
    version: int
    locale: str
    body: str
    published_at: datetime


def render(version: LegalVersion, locale: str) -> RenderedLegal:
    served, text = legal_text(version, locale)
    body = (
        render_privacy_statement(text, version.privacy_mode, served)
        if version.kind == LegalKind.PRIVACY
        else text
    )
    return RenderedLegal(
        kind=version.kind,
        version=version.version,
        locale=served,
        body=body,
        published_at=version.published_at,
    )


@dataclass(frozen=True)
class PrivacyAcknowledgement:
    user: User
    # None when the user never acknowledged any version.
    version: int | None
    acknowledged_at: datetime | None


@dataclass(frozen=True)
class PrivacyAcknowledgementOverview:
    current_version: int | None
    # People who acknowledged the current version, and those still asked.
    acknowledged: list[PrivacyAcknowledgement]
    pending: list[PrivacyAcknowledgement]


class ManageLegal:
    def __init__(
        self,
        *,
        legal: ILegalRepository,
        settings_repo: ISettingsRepository,
        user_repo: IUserRepository,
        facts: IInstanceFacts,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        on_published: Callable[[], None] | None = None,
    ) -> None:
        self._legal = legal
        self._settings = settings_repo
        self._users = user_repo
        self._facts = facts
        self._audit = audit
        self._uow = uow
        self._on_published = on_published

    async def current(self, kind: LegalKind, locale: str) -> RenderedLegal:
        version = await self._legal.current(kind)
        if version is None:
            raise LegalPageNotFoundError("This page is not published yet.")
        return render(version, locale)

    async def history(self, kind: LegalKind) -> list[LegalVersion]:
        return await self._legal.history(kind)

    async def acknowledgements(self) -> PrivacyAcknowledgementOverview:
        """Which person acknowledged which privacy statement version. Every
        active person who is not a service account is asked; whoever has
        not acknowledged the current version is pending, with the version
        they acknowledged last."""
        current = await self._legal.current(LegalKind.PRIVACY)
        version = current.version if current else None
        people = [
            u for u in await self._users.list_all() if u.is_active and not u.is_service_account
        ]
        entries = sorted(
            (
                PrivacyAcknowledgement(
                    user=u,
                    version=u.privacy_acknowledged_version,
                    acknowledged_at=u.privacy_acknowledged_at,
                )
                for u in people
            ),
            key=lambda e: e.user.display_name.lower(),
        )
        done = [e for e in entries if version is not None and e.version == version]
        return PrivacyAcknowledgementOverview(
            current_version=version,
            acknowledged=done,
            pending=[e for e in entries if e not in done] if version is not None else [],
        )

    async def _publish(
        self, actor: User | None, kind: LegalKind, texts: dict[str, str]
    ) -> LegalVersion:
        current = await self._legal.current(kind)
        snapshot = (
            privacy_mode_of(
                await self._settings.get_privacy(),
                peering=(await self._settings.get_features()).peering,
            )
            if kind == LegalKind.PRIVACY
            else None
        )
        saved = await self._legal.add(
            LegalVersion(
                kind=kind,
                version=(current.version + 1) if current else 1,
                texts=texts,
                published_at=now_utc(),
                published_by_id=actor.id if actor and actor.id else None,
                privacy_mode=snapshot,
            )
        )
        if kind == LegalKind.PRIVACY and actor is not None and actor.id:
            # Whoever publishes the statement has read it.
            actor.privacy_acknowledged_version = saved.version
            actor.privacy_acknowledged_at = saved.published_at
            await self._users.save(actor)
        return saved

    async def publish(
        self, actor: User, kind: LegalKind, texts: dict[str, str], *, context: RequestContext
    ) -> LegalVersion:
        saved = await self._publish(actor, kind, validate_legal_texts(texts))
        await self._audit.record(
            SecurityEventType.SETTINGS_CHANGED,
            actor=actor,
            context=context,
            detail={"section": "legal", "fields": [f"{kind.value}.v{saved.version}"]},
        )
        await self._uow.commit()
        if self._on_published is not None:
            self._on_published()
        return saved

    async def republish_privacy(self, actor: User) -> LegalVersion | None:
        """After the privacy settings changed: the same text as a new
        version under the new mode, so everyone acknowledges again. Nothing
        when no statement was ever published. The caller commits."""
        current = await self._legal.current(LegalKind.PRIVACY)
        if current is None:
            return None
        saved = await self._publish(actor, LegalKind.PRIVACY, dict(current.texts))
        if self._on_published is not None:
            self._on_published()
        return saved

    async def facts(self) -> PrivacyFacts:
        general = await self._settings.get_general()
        retention = await self._settings.get_retention()
        features = await self._settings.get_features()
        agents = await self._settings.get_agents()
        mail = await self._settings.get_mail()
        backups = self._facts.backup_retention()
        return PrivacyFacts(
            instance_name=general.instance_name,
            storage_provider=self._facts.storage_provider(),
            backup_keep_days=backups.keep_days,
            backup_hour_utc=self._facts.backup_hour_utc(),
            security_log_days=retention.security_log_days,
            agent_calls_days=retention.agent_calls_days,
            webhook_deliveries_days=retention.webhook_deliveries_days,
            recipe_revisions_days=retention.recipe_revisions_days,
            agents_enabled=features.agents,
            agent_token_max_days=agents.token_max_lifetime_days,
            webhooks_enabled=features.webhooks,
            usda_enabled=features.usda,
            mail_enabled=mail.enabled,
            households_enabled=features.households,
            dinner_guests_enabled=features.dinner_guests,
            public_recipes_allowed=(await self._settings.get_privacy()).allow_public_recipes,
            peering_enabled=features.peering,
        )

    async def draft(self, locale: str) -> str:
        return privacy_draft(await self.facts(), locale)


@dataclass(frozen=True)
class PrivacyStatus:
    current_version: int | None
    acknowledged_version: int | None
    pending: bool


class OwnPrivacy:
    def __init__(
        self, *, legal: ILegalRepository, user_repo: IUserRepository, uow: IUnitOfWork
    ) -> None:
        self._legal = legal
        self._users = user_repo
        self._uow = uow

    async def status(self, user: User) -> PrivacyStatus:
        current = await self._legal.current(LegalKind.PRIVACY)
        return PrivacyStatus(
            current_version=current.version if current else None,
            acknowledged_version=user.privacy_acknowledged_version,
            pending=acknowledgement_pending(user, current),
        )

    async def acknowledge(self, user: User, version: int) -> None:
        current = await self._legal.current(LegalKind.PRIVACY)
        if current is None or current.version != version:
            raise StalePrivacyVersionError(
                "This is not the current privacy statement; reload it and read it again."
            )
        user.privacy_acknowledged_version = version
        user.privacy_acknowledged_at = now_utc()
        await self._users.save(user)
        await self._uow.commit()


@dataclass(frozen=True)
class ConsentState:
    kind: str
    granted_at: datetime | None


class ManageOwnConsents:
    """The voluntary consents. Withdrawing the AI agent consent revokes the
    user's agent tokens and ends their connected apps; withdrawing the
    health data consent deletes the user's allergies, intolerances and diets
    in the same transaction."""

    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        pat_repo: IPatRepository,
        health_data: IHealthDataEraser | None,
        audit: SecurityAudit,
        uow: IUnitOfWork,
        oauth_grants: ManageOwnOAuthGrants | None = None,
    ) -> None:
        self._users = user_repo
        self._pats = pat_repo
        self._oauth_grants = oauth_grants
        self._health = health_data
        self._audit = audit
        self._uow = uow

    @staticmethod
    def state(user: User) -> list[ConsentState]:
        return [
            ConsentState(HEALTH_DATA, user.consent_health_data_at),
            ConsentState(AI_AGENTS, user.consent_ai_agents_at),
        ]

    @staticmethod
    def _check(kind: str) -> None:
        if kind not in CONSENTS:
            raise LegalPageNotFoundError(f"No consent {kind!r}.")

    async def grant(self, user: User, kind: str) -> list[ConsentState]:
        self._check(kind)
        now = now_utc()
        if kind == HEALTH_DATA and user.consent_health_data_at is None:
            user.consent_health_data_at = now
        if kind == AI_AGENTS and user.consent_ai_agents_at is None:
            user.consent_ai_agents_at = now
        await self._users.save(user)
        await self._uow.commit()
        return self.state(user)

    async def withdraw(
        self, user: User, kind: str, *, context: RequestContext
    ) -> list[ConsentState]:
        self._check(kind)
        if kind == HEALTH_DATA:
            if self._health is None:
                raise ConsentRequiredError(
                    "Withdrawing is not possible right now, since the health data cannot be "
                    "deleted along with it."
                )
            await self._health.erase(user.id)
            user.consent_health_data_at = None
        else:
            now = now_utc()
            for token in await self._pats.list_for_user(user.id):
                if Permission.USE_MCP in token.permissions and token.revoked_at is None:
                    token.revoked_at = now
                    await self._pats.save(token)
                    await self._audit.record(
                        SecurityEventType.PAT_REVOKED,
                        actor=user,
                        target=user,
                        context=context,
                        detail={"reason": "ai_agents_consent_withdrawn"},
                    )
            if self._oauth_grants is not None:
                await self._oauth_grants.revoke_all(
                    user, reason="ai_agents_consent_withdrawn", context=context
                )
            user.consent_ai_agents_at = None
        await self._users.save(user)
        await self._uow.commit()
        return self.state(user)
