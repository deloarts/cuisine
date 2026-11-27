"""
Dependency providers: the database session, the infrastructure adapters and
the use cases built from them. Routes depend on the use case they need, so
a route never constructs a repository itself.

The process-wide adapters are cached. The Redis-backed throttle and replay
guard are separate providers, so the test suite can swap them for the
in-process versions.
"""

from collections.abc import AsyncIterator
from collections.abc import Callable
from functools import cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.adapters.inbound.api.middleware.maintenance import maintenance_state
from src.platform.adapters.inbound.api.privacy_gate import privacy_state
from src.platform.adapters.outbound.external.authorization_codes import RedisAuthorizationCodeStore
from src.platform.adapters.outbound.external.login_attempts import RedisLoginAttemptTracker
from src.platform.adapters.outbound.external.mail.render import JinjaMailRenderer
from src.platform.adapters.outbound.external.mail.send_limiter import InMemorySendLimiter
from src.platform.adapters.outbound.external.peering.httpx_peer_client import HttpxPeerClient
from src.platform.adapters.outbound.external.pillow_image_processor import PillowImageProcessor
from src.platform.adapters.outbound.external.replay_guard import RedisReplayGuard
from src.platform.adapters.outbound.external.request_rate_limiter import RedisRequestRateLimiter
from src.platform.adapters.outbound.external.smtp_mail_service import SmtpMailService
from src.platform.adapters.outbound.external.system.backup_control import FileBackupControl
from src.platform.adapters.outbound.external.system.backup_directory import BackupDirectoryReader
from src.platform.adapters.outbound.external.system.psutil_host import PsutilHostReader
from src.platform.adapters.outbound.external.system.service_probe import ServiceProbe
from src.platform.adapters.outbound.external.webhook.httpx_sender import HttpxWebhookSender
from src.platform.adapters.outbound.external.webhook.target_guard import WebhookTargetGuard
from src.platform.adapters.outbound.persistence.public_id_lookup import SqlAlchemyPublicIdResolver
from src.platform.adapters.outbound.persistence.repositories.agent_call_repository import (
    SqlAlchemyAgentCallRepository,
)
from src.platform.adapters.outbound.persistence.repositories.legal_repository import (
    SqlAlchemyLegalRepository,
)
from src.platform.adapters.outbound.persistence.repositories.notice_repository import (
    SqlAlchemyNoticeRepository,
)
from src.platform.adapters.outbound.persistence.repositories.oauth_repositories import (
    SqlAlchemyOAuthClientRepository,
)
from src.platform.adapters.outbound.persistence.repositories.oauth_repositories import (
    SqlAlchemyOAuthGrantRepository,
)
from src.platform.adapters.outbound.persistence.repositories.oauth_repositories import (
    SqlAlchemyOAuthTokenRepository,
)
from src.platform.adapters.outbound.persistence.repositories.peer_channel_repository import (
    SqlAlchemyPeerChannelRepository,
)
from src.platform.adapters.outbound.persistence.repositories.peer_repository import (
    SqlAlchemyPeerInvitationRepository,
)
from src.platform.adapters.outbound.persistence.repositories.peer_repository import (
    SqlAlchemyPeerRepository,
)
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemyApiKeyRepository,
)
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemyPasskeyRepository,
)
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemyPatRepository,
)
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemySecurityEventRepository,
)
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemyTrustedDeviceRepository,
)
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemyUserSessionRepository,
)
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.storage_stats_repository import (
    SqlAlchemyStorageStatsReader,
)
from src.platform.adapters.outbound.persistence.repositories.stored_file_repository import (
    SqlAlchemyStoredFileRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_group_repository import (
    SqlAlchemyUserGroupRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.repositories.webhook_repository import (
    SqlAlchemyWebhookDeliveryRepository,
)
from src.platform.adapters.outbound.persistence.repositories.webhook_repository import (
    SqlAlchemyWebhookSubscriptionRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.platform.adapters.outbound.storage.factory import active_content_store
from src.platform.application.dto.context import RequestContext
from src.platform.application.services.file_access import FileAccess
from src.platform.application.services.login_session import LoginSession
from src.platform.application.services.mailer import Mailer
from src.platform.application.services.peer_calls import PeerCalls
from src.platform.application.services.peer_channel import PeerChannel
from src.platform.application.services.peering_identity import PeeringIdentity
from src.platform.application.services.security_audit import SecurityAudit
from src.platform.application.services.webhook_publisher import WebhookPublisher
from src.platform.application.use_cases.account.avatar import ManageOwnAvatar
from src.platform.application.use_cases.account.legal_and_consents import ManageLegal
from src.platform.application.use_cases.account.legal_and_consents import ManageOwnConsents
from src.platform.application.use_cases.account.legal_and_consents import OwnPrivacy
from src.platform.application.use_cases.account.own_profile import ChangeOwnPassword
from src.platform.application.use_cases.account.own_profile import UpdateOwnProfile
from src.platform.application.use_cases.account.passkeys import ManageOwnPasskeys
from src.platform.application.use_cases.account.sessions import ManageOwnSessions
from src.platform.application.use_cases.account.sessions import ManageOwnTrustedDevices
from src.platform.application.use_cases.account.totp import ManageOwnTotp
from src.platform.application.use_cases.admin.agent_calls import ListAgentCalls
from src.platform.application.use_cases.admin.groups import ManageGroups
from src.platform.application.use_cases.admin.mail_templates import ManageMailTemplates
from src.platform.application.use_cases.admin.notices import ManageNotices
from src.platform.application.use_cases.admin.notices import OwnNotices
from src.platform.application.use_cases.admin.operations import PurgeExpired
from src.platform.application.use_cases.admin.operations import Purger
from src.platform.application.use_cases.admin.operations import RequestBackupNow
from src.platform.application.use_cases.admin.operations import RunNightlyChecks
from src.platform.application.use_cases.admin.security_events import ListSecurityEvents
from src.platform.application.use_cases.admin.settings import FeaturesSavedHook
from src.platform.application.use_cases.admin.settings import ManageSettings
from src.platform.application.use_cases.admin.settings import PrivacySavedHook
from src.platform.application.use_cases.admin.system import ReadHostStatus
from src.platform.application.use_cases.admin.system import ReadStorageStatus
from src.platform.application.use_cases.admin.tokens import ManageApiKeys
from src.platform.application.use_cases.admin.tokens import ManagePats
from src.platform.application.use_cases.admin.users import ManageUsers
from src.platform.application.use_cases.admin.webhooks import ManageWebhooks
from src.platform.application.use_cases.auth.authenticate_agent import AuthenticateAgent
from src.platform.application.use_cases.auth.logout import Logout
from src.platform.application.use_cases.auth.passkey_login import PasskeyLogin
from src.platform.application.use_cases.auth.password_login import PasswordLogin
from src.platform.application.use_cases.auth.totp_login import TotpLogin
from src.platform.application.use_cases.files.manage_files import ManageFiles
from src.platform.application.use_cases.files.sweep_unused_files import SweepUnusedFiles
from src.platform.application.use_cases.oauth.authorize import AuthorizeOAuthClient
from src.platform.application.use_cases.oauth.grants import ManageOwnOAuthGrants
from src.platform.application.use_cases.oauth.grants import PurgeOAuthRecords
from src.platform.application.use_cases.oauth.register_client import RegisterOAuthClient
from src.platform.application.use_cases.oauth.tokens import IssueOAuthTokens
from src.platform.application.use_cases.peering.authenticate_peer import AuthenticatePeer
from src.platform.application.use_cases.peering.channel_jobs import AnnouncePeerChanges
from src.platform.application.use_cases.peering.channel_jobs import PeerChannelStatus
from src.platform.application.use_cases.peering.channel_jobs import RunPeerChannelJobs
from src.platform.application.use_cases.peering.channel_receiving import PeerContact
from src.platform.application.use_cases.peering.channel_receiving import ReceivePeerEvents
from src.platform.application.use_cases.peering.channel_receiving import SyncFromPeer
from src.platform.application.use_cases.peering.channel_sending import DeliverPeerEvents
from src.platform.application.use_cases.peering.channel_source import AnswerPeerChannel
from src.platform.application.use_cases.peering.channel_source import RepairPeerChannel
from src.platform.application.use_cases.peering.invitations import ManagePeerInvitations
from src.platform.application.use_cases.peering.pairing import PairWithPeer
from src.platform.application.use_cases.peering.pairing import PeerPairedHook
from src.platform.application.use_cases.peering.peers import AnswerPeer
from src.platform.application.use_cases.peering.peers import ManagePeers
from src.platform.application.use_cases.peering.peers import PeerChangedHook
from src.platform.application.use_cases.peering.peers import PeerRevokedHook
from src.platform.application.use_cases.resolve.resolve_public_id import ResolvePublicId
from src.platform.const import IMAGE_MAX_EDGE
from src.platform.const import NAME
from src.platform.const import THUMBNAIL_MAX_EDGE
from src.platform.const import VERSION
from src.platform.domain.entities.peer import Peer
from src.platform.infrastructure.config.settings import cfg
from src.platform.infrastructure.instance_facts import ConfiguredInstanceFacts
from src.platform.infrastructure.logging.logger import recent_logs
from src.platform.infrastructure.logging.ring_buffer import RingBufferHandler
from src.platform.infrastructure.redis_client import get_redis
from src.platform.infrastructure.security.hashing import BcryptPasswordHasher
from src.platform.infrastructure.security.opaque_secret import Sha256SecretHasher
from src.platform.infrastructure.security.token import JwtTokenService
from src.platform.infrastructure.security.totp import PyOtpTotpService
from src.platform.infrastructure.security.webauthn import WebAuthnVerifier
from src.platform.ports.outbound.authorization_codes import IAuthorizationCodeStore
from src.platform.ports.outbound.feature_switches import IFeatureSwitches
from src.platform.ports.outbound.file_access import IFileAccess
from src.platform.ports.outbound.health_data_eraser import IHealthDataEraser
from src.platform.ports.outbound.instance_facts import IInstanceFacts
from src.platform.ports.outbound.login_attempts import ILoginAttemptTracker
from src.platform.ports.outbound.peer_client import IPeerClient
from src.platform.ports.outbound.peer_content import IPeerContentConsumer
from src.platform.ports.outbound.peer_content import IPeerContentProvider
from src.platform.ports.outbound.replay_guard import IReplayGuard
from src.platform.ports.outbound.repositories.public_id_resolver import IPublicIdAccess
from src.platform.ports.outbound.request_rate_limiter import IRequestRateLimiter
from src.platform.ports.outbound.webhook_sender import IWebhookSender
from src.platform.ports.outbound.webhook_sender import IWebhookTargetGuard
from src.shared_kernel.domain.services.clock import now_utc

# ── Database ─────────────────────────────────────────────────────────


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


class Platform:
    """The repositories of one request, all on the request's session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.uow = SqlAlchemyUnitOfWork(db)
        self.users = SqlAlchemyUserRepository(db)
        self.groups = SqlAlchemyUserGroupRepository(db)
        self.sessions = SqlAlchemyUserSessionRepository(db)
        self.trusted_devices = SqlAlchemyTrustedDeviceRepository(db)
        self.passkeys = SqlAlchemyPasskeyRepository(db)
        self.pats = SqlAlchemyPatRepository(db)
        self.api_keys = SqlAlchemyApiKeyRepository(db)
        self.security_events = SqlAlchemySecurityEventRepository(db)
        self.settings = SqlAlchemySettingsRepository(db)
        self.files = SqlAlchemyStoredFileRepository(db, active_content_store(db))
        self.agent_calls = SqlAlchemyAgentCallRepository(db)
        self.oauth_clients = SqlAlchemyOAuthClientRepository(db)
        self.oauth_grants = SqlAlchemyOAuthGrantRepository(db)
        self.oauth_tokens = SqlAlchemyOAuthTokenRepository(db)
        self.audit = SecurityAudit(self.security_events)
        self.webhook_subscriptions = SqlAlchemyWebhookSubscriptionRepository(db)
        self.webhook_deliveries = SqlAlchemyWebhookDeliveryRepository(db)
        self.notices = SqlAlchemyNoticeRepository(db)
        self.legal = SqlAlchemyLegalRepository(db)
        self.peers = SqlAlchemyPeerRepository(db)
        self.peer_invitations = SqlAlchemyPeerInvitationRepository(db)
        self.peer_channels = SqlAlchemyPeerChannelRepository(db)
        # Any use case may publish a peer channel event in its own
        # transaction (`PeerChannel.publish`).
        self.peer_channel = PeerChannel(peers=self.peers, channels=self.peer_channels)
        # Any use case may publish a webhook event in its own transaction.
        self.webhooks = WebhookPublisher(
            subscriptions=self.webhook_subscriptions,
            deliveries=self.webhook_deliveries,
            settings_repo=self.settings,
        )


def get_platform(db: AsyncSession = Depends(get_db)) -> Platform:
    return Platform(db)


# ── Process-wide adapters ────────────────────────────────────────────


@cache
def tokens() -> JwtTokenService:
    return JwtTokenService()


@cache
def hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


@cache
def secrets() -> Sha256SecretHasher:
    return Sha256SecretHasher()


@cache
def totp() -> PyOtpTotpService:
    return PyOtpTotpService()


@cache
def passkey_verifier() -> WebAuthnVerifier:
    return WebAuthnVerifier(cfg.domain, rp_name=NAME.capitalize())


@cache
def image_processor() -> PillowImageProcessor:
    return PillowImageProcessor(IMAGE_MAX_EDGE, THUMBNAIL_MAX_EDGE)


@cache
def mail_service() -> SmtpMailService:
    return SmtpMailService(WebhookTargetGuard())


def get_login_attempts() -> ILoginAttemptTracker:
    return RedisLoginAttemptTracker(get_redis())


def get_replay_guard() -> IReplayGuard:
    return RedisReplayGuard(get_redis())


def get_request_rate_limiter() -> IRequestRateLimiter:
    return RedisRequestRateLimiter(get_redis())


def get_authorization_codes() -> IAuthorizationCodeStore:
    return RedisAuthorizationCodeStore(get_redis())


# ── Use cases ────────────────────────────────────────────────────────


def _login_session(p: Platform) -> LoginSession:
    return LoginSession(
        user_repo=p.users,
        session_repo=p.sessions,
        trusted_device_repo=p.trusted_devices,
        settings_repo=p.settings,
        tokens=tokens(),
        secrets=secrets(),
        audit=p.audit,
        uow=p.uow,
    )


def get_password_login(
    p: Platform = Depends(get_platform),
    attempts: ILoginAttemptTracker = Depends(get_login_attempts),
) -> PasswordLogin:
    return PasswordLogin(
        user_repo=p.users,
        settings_repo=p.settings,
        trusted_device_repo=p.trusted_devices,
        attempts=attempts,
        hasher=hasher(),
        tokens=tokens(),
        secrets=secrets(),
        login_session=_login_session(p),
        audit=p.audit,
        uow=p.uow,
    )


def get_totp_login(
    p: Platform = Depends(get_platform),
    attempts: ILoginAttemptTracker = Depends(get_login_attempts),
    replay: IReplayGuard = Depends(get_replay_guard),
) -> TotpLogin:
    return TotpLogin(
        user_repo=p.users,
        settings_repo=p.settings,
        attempts=attempts,
        replay=replay,
        totp=totp(),
        tokens=tokens(),
        login_session=_login_session(p),
        audit=p.audit,
        uow=p.uow,
    )


def get_passkey_login(
    p: Platform = Depends(get_platform),
    replay: IReplayGuard = Depends(get_replay_guard),
) -> PasskeyLogin:
    return PasskeyLogin(
        user_repo=p.users,
        passkey_repo=p.passkeys,
        verifier=passkey_verifier(),
        replay=replay,
        tokens=tokens(),
        login_session=_login_session(p),
        audit=p.audit,
        uow=p.uow,
    )


def get_logout(p: Platform = Depends(get_platform)) -> Logout:
    return Logout(session_repo=p.sessions, audit=p.audit, uow=p.uow)


def get_update_own_profile(p: Platform = Depends(get_platform)) -> UpdateOwnProfile:
    return UpdateOwnProfile(user_repo=p.users, settings_repo=p.settings, uow=p.uow)


def get_change_own_password(p: Platform = Depends(get_platform)) -> ChangeOwnPassword:
    return ChangeOwnPassword(
        user_repo=p.users,
        session_repo=p.sessions,
        settings_repo=p.settings,
        hasher=hasher(),
        audit=p.audit,
        uow=p.uow,
        oauth_grants=manage_own_oauth_grants(p),
    )


def get_manage_own_totp(
    p: Platform = Depends(get_platform), replay: IReplayGuard = Depends(get_replay_guard)
) -> ManageOwnTotp:
    return ManageOwnTotp(
        user_repo=p.users,
        settings_repo=p.settings,
        trusted_device_repo=p.trusted_devices,
        totp=totp(),
        replay=replay,
        hasher=hasher(),
        login_session=_login_session(p),
        audit=p.audit,
        uow=p.uow,
    )


def get_manage_own_sessions(p: Platform = Depends(get_platform)) -> ManageOwnSessions:
    return ManageOwnSessions(
        session_repo=p.sessions, settings_repo=p.settings, audit=p.audit, uow=p.uow
    )


def get_manage_own_trusted_devices(
    p: Platform = Depends(get_platform),
) -> ManageOwnTrustedDevices:
    return ManageOwnTrustedDevices(trusted_device_repo=p.trusted_devices, audit=p.audit, uow=p.uow)


def get_manage_own_passkeys(
    p: Platform = Depends(get_platform), replay: IReplayGuard = Depends(get_replay_guard)
) -> ManageOwnPasskeys:
    return ManageOwnPasskeys(
        passkey_repo=p.passkeys,
        verifier=passkey_verifier(),
        replay=replay,
        tokens=tokens(),
        audit=p.audit,
        uow=p.uow,
    )


def get_manage_pats(p: Platform = Depends(get_platform)) -> ManagePats:
    return ManagePats(
        pat_repo=p.pats, settings_repo=p.settings, secrets=secrets(), audit=p.audit, uow=p.uow
    )


def get_manage_api_keys(p: Platform = Depends(get_platform)) -> ManageApiKeys:
    return ManageApiKeys(
        key_repo=p.api_keys,
        user_repo=p.users,
        settings_repo=p.settings,
        secrets=secrets(),
        audit=p.audit,
        uow=p.uow,
    )


def get_manage_users(p: Platform = Depends(get_platform)) -> ManageUsers:
    return ManageUsers(
        user_repo=p.users,
        group_repo=p.groups,
        session_repo=p.sessions,
        trusted_device_repo=p.trusted_devices,
        settings_repo=p.settings,
        hasher=hasher(),
        key_repo=p.api_keys,
        event_repo=p.security_events,
        file_repo=p.files,
        images=image_processor(),
        audit=p.audit,
        uow=p.uow,
        webhooks=p.webhooks,
        mailer=mailer(p),
    )


def get_manage_groups(p: Platform = Depends(get_platform)) -> ManageGroups:
    return ManageGroups(group_repo=p.groups, user_repo=p.users, audit=p.audit, uow=p.uow)


def get_manage_settings(p: Platform = Depends(get_platform)) -> ManageSettings:
    legal = manage_legal(p)
    return ManageSettings(
        settings_repo=p.settings,
        mail=mail_service(),
        audit=p.audit,
        uow=p.uow,
        files=p.files,
        file_access=file_access(p),
        webhooks=p.webhooks,
        mailer=mailer(p),
        on_maintenance_changed=maintenance_state.forget,
        on_privacy_changed=legal.republish_privacy,
        on_privacy_saved=[factory(p.db) for factory in _privacy_saved_hooks],
        on_features_saved=[factory(p.db) for factory in _features_saved_hooks],
    )


# The cookbook registers what follows a saved change of the privacy settings
# (recipes that stop or start being public for paired instances), from the
# composition root.
PrivacySavedHookFactory = Callable[[AsyncSession], PrivacySavedHook]
_privacy_saved_hooks: list[PrivacySavedHookFactory] = []


def register_privacy_saved_hook(factory: PrivacySavedHookFactory) -> None:
    if factory not in _privacy_saved_hooks:
        _privacy_saved_hooks.append(factory)


# The cookbook registers what follows a saved change of the feature switches
# (recipes set to paired instances that start or stop going to them when
# peering is switched), from the composition root.
FeaturesSavedHookFactory = Callable[[AsyncSession], FeaturesSavedHook]
_features_saved_hooks: list[FeaturesSavedHookFactory] = []


def register_features_saved_hook(factory: FeaturesSavedHookFactory) -> None:
    if factory not in _features_saved_hooks:
        _features_saved_hooks.append(factory)


# ── Mail, operations, legal and consents ─────────────────────────────


@cache
def mail_renderer() -> JinjaMailRenderer:
    return JinjaMailRenderer()


@cache
def send_limiter() -> InMemorySendLimiter:
    return InMemorySendLimiter()


@cache
def backup_control() -> FileBackupControl:
    return FileBackupControl(cfg.backup.control_dir)


@cache
def instance_facts() -> ConfiguredInstanceFacts:
    return ConfiguredInstanceFacts()


def get_instance_facts() -> IInstanceFacts:
    return instance_facts()


def get_feature_switches(p: Platform = Depends(get_platform)) -> IFeatureSwitches:
    return p.settings


def mailer(p: Platform) -> Mailer:
    return Mailer(
        settings_repo=p.settings,
        mail=mail_service(),
        renderer=mail_renderer(),
        limiter=send_limiter(),
        domain=cfg.domain,
    )


def get_manage_mail_templates(p: Platform = Depends(get_platform)) -> ManageMailTemplates:
    return ManageMailTemplates(
        settings_repo=p.settings,
        renderer=mail_renderer(),
        mailer=mailer(p),
        audit=p.audit,
        uow=p.uow,
    )


def get_request_backup_now() -> RequestBackupNow:
    return RequestBackupNow(control=backup_control())


def purge_expired(p: Platform) -> PurgeExpired:
    return PurgeExpired(
        settings_repo=p.settings,
        events=p.security_events,
        agent_calls=p.agent_calls,
        deliveries=p.webhook_deliveries,
        uow=p.uow,
        extra=[
            *(factory(p.db) for factory in RETENTION_PURGERS),
            PurgeOAuthRecords(
                client_repo=p.oauth_clients, grant_repo=p.oauth_grants, token_repo=p.oauth_tokens
            ),
        ],
    )


def nightly_checks(p: Platform) -> RunNightlyChecks:
    return RunNightlyChecks(
        settings_repo=p.settings,
        storage=read_storage_status(p),
        control=backup_control(),
        mailer=mailer(p),
        uow=p.uow,
    )


def manage_legal(p: Platform) -> ManageLegal:
    return ManageLegal(
        legal=p.legal,
        settings_repo=p.settings,
        user_repo=p.users,
        facts=instance_facts(),
        audit=p.audit,
        uow=p.uow,
        on_published=privacy_state.forget,
    )


def get_manage_legal(p: Platform = Depends(get_platform)) -> ManageLegal:
    return manage_legal(p)


def get_own_privacy(p: Platform = Depends(get_platform)) -> OwnPrivacy:
    return OwnPrivacy(legal=p.legal, user_repo=p.users, uow=p.uow)


# The cookbook registers how a user's health data is deleted when they
# withdraw the health data consent (src/bootstrap), and the purge steps of
# its own retention (recipe revisions). Platform never imports the cookbook.
HealthDataEraserFactory = Callable[[AsyncSession], IHealthDataEraser]
RetentionPurgerFactory = Callable[[AsyncSession], Purger]
_health_data_eraser: list[HealthDataEraserFactory] = []
RETENTION_PURGERS: list[RetentionPurgerFactory] = []


def register_health_data_eraser(factory: HealthDataEraserFactory) -> None:
    _health_data_eraser[:] = [factory]


def register_retention_purger(factory: RetentionPurgerFactory) -> None:
    RETENTION_PURGERS.append(factory)


# Each package registers the read rule and page of the kinds its public ids
# resolve to (src/bootstrap); a kind without a rule never resolves.
PublicIdAccessFactory = Callable[[AsyncSession], IPublicIdAccess]
_public_id_access: dict[str, PublicIdAccessFactory] = {}


def register_public_id_access(kind: str, factory: PublicIdAccessFactory) -> None:
    _public_id_access[kind] = factory


def get_resolve_public_id(p: Platform = Depends(get_platform)) -> ResolvePublicId:
    return ResolvePublicId(
        resolver=SqlAlchemyPublicIdResolver(p.db),
        access={kind: factory(p.db) for kind, factory in _public_id_access.items()},
    )


def get_manage_own_consents(p: Platform = Depends(get_platform)) -> ManageOwnConsents:
    eraser = _health_data_eraser[0](p.db) if _health_data_eraser else None
    return ManageOwnConsents(
        user_repo=p.users,
        pat_repo=p.pats,
        health_data=eraser,
        audit=p.audit,
        uow=p.uow,
        oauth_grants=manage_own_oauth_grants(p),
    )


def get_recent_logs() -> RingBufferHandler:
    return recent_logs


# ── Admin area: host, storage, webhooks, notices ─────────────────────


@cache
def host_reader() -> PsutilHostReader:
    return PsutilHostReader()


@cache
def webhook_guard() -> WebhookTargetGuard:
    return WebhookTargetGuard()


@cache
def _webhook_sender() -> HttpxWebhookSender:
    return HttpxWebhookSender(webhook_guard())


def get_webhook_sender() -> IWebhookSender:
    return _webhook_sender()


def get_webhook_guard() -> IWebhookTargetGuard:
    return webhook_guard()


def get_read_host_status(p: Platform = Depends(get_platform)) -> ReadHostStatus:
    return ReadHostStatus(
        host=host_reader(),
        probe=ServiceProbe(p.db, get_redis()),
        app_version=VERSION,
        settings_repo=p.settings,
        uow=p.uow,
    )


def read_storage_status(p: Platform) -> ReadStorageStatus:
    return ReadStorageStatus(
        stats=SqlAlchemyStorageStatsReader(p.db),
        backups=BackupDirectoryReader(
            cfg.backup.dir, keep_days=cfg.backup.keep_days, hour_utc=cfg.backup.hour
        ),
        content=active_content_store(p.db),
        endpoint_url=cfg.storage.endpoint_url,
        control=backup_control(),
    )


def get_read_storage_status(p: Platform = Depends(get_platform)) -> ReadStorageStatus:
    return read_storage_status(p)


def get_manage_webhooks(
    p: Platform = Depends(get_platform),
    sender: IWebhookSender = Depends(get_webhook_sender),
    guard: IWebhookTargetGuard = Depends(get_webhook_guard),
) -> ManageWebhooks:
    return ManageWebhooks(
        subscriptions=p.webhook_subscriptions,
        deliveries=p.webhook_deliveries,
        settings_repo=p.settings,
        sender=sender,
        guard=guard,
        audit=p.audit,
        uow=p.uow,
    )


def get_manage_notices(p: Platform = Depends(get_platform)) -> ManageNotices:
    return ManageNotices(notices=p.notices, user_repo=p.users, audit=p.audit, uow=p.uow)


def get_own_notices(p: Platform = Depends(get_platform)) -> OwnNotices:
    return OwnNotices(notices=p.notices, uow=p.uow)


def get_list_security_events(p: Platform = Depends(get_platform)) -> ListSecurityEvents:
    return ListSecurityEvents(repo=p.security_events)


# Each package registers the rule for the files its records refer to
# (src/bootstrap); Platform itself knows avatars and branding images.
FileAccessFactory = Callable[[AsyncSession], IFileAccess]
_file_access: list[FileAccessFactory] = []


def register_file_access(factory: FileAccessFactory) -> None:
    if factory not in _file_access:
        _file_access.append(factory)


def file_access(p: Platform) -> FileAccess:
    return FileAccess(
        user_repo=p.users,
        settings_repo=p.settings,
        features=[factory(p.db) for factory in _file_access],
    )


def get_file_access(p: Platform = Depends(get_platform)) -> FileAccess:
    return file_access(p)


def sweep_unused_files(p: Platform) -> SweepUnusedFiles:
    return SweepUnusedFiles(file_repo=p.files, access=file_access(p), uow=p.uow)


def get_manage_files(p: Platform = Depends(get_platform)) -> ManageFiles:
    return ManageFiles(
        file_repo=p.files, images=image_processor(), access=file_access(p), uow=p.uow
    )


def get_manage_own_avatar(p: Platform = Depends(get_platform)) -> ManageOwnAvatar:
    return ManageOwnAvatar(
        user_repo=p.users, file_repo=p.files, images=image_processor(), uow=p.uow
    )


def get_list_agent_calls(p: Platform = Depends(get_platform)) -> ListAgentCalls:
    return ListAgentCalls(repo=p.agent_calls)


def get_authenticate_agent(p: Platform = Depends(get_platform)) -> AuthenticateAgent:
    return AuthenticateAgent(
        pat_repo=p.pats,
        key_repo=p.api_keys,
        user_repo=p.users,
        settings_repo=p.settings,
        secrets=secrets(),
        uow=p.uow,
        legal=p.legal,
        oauth_clients=p.oauth_clients,
        oauth_grants=p.oauth_grants,
        oauth_tokens=p.oauth_tokens,
    )


# ── OAuth for hosted AI clients ──────────────────────────────────────


def get_register_oauth_client(p: Platform = Depends(get_platform)) -> RegisterOAuthClient:
    return RegisterOAuthClient(
        client_repo=p.oauth_clients,
        settings_repo=p.settings,
        secrets=secrets(),
        audit=p.audit,
        uow=p.uow,
    )


def get_authorize_oauth_client(
    p: Platform = Depends(get_platform),
    codes: IAuthorizationCodeStore = Depends(get_authorization_codes),
) -> AuthorizeOAuthClient:
    return AuthorizeOAuthClient(
        client_repo=p.oauth_clients,
        settings_repo=p.settings,
        codes=codes,
        secrets=secrets(),
        audit=p.audit,
        uow=p.uow,
        issuer=cfg.domain,
    )


def get_issue_oauth_tokens(
    p: Platform = Depends(get_platform),
    codes: IAuthorizationCodeStore = Depends(get_authorization_codes),
) -> IssueOAuthTokens:
    return IssueOAuthTokens(
        client_repo=p.oauth_clients,
        grant_repo=p.oauth_grants,
        token_repo=p.oauth_tokens,
        user_repo=p.users,
        settings_repo=p.settings,
        codes=codes,
        secrets=secrets(),
        audit=p.audit,
        uow=p.uow,
    )


def manage_own_oauth_grants(p: Platform) -> ManageOwnOAuthGrants:
    return ManageOwnOAuthGrants(
        grant_repo=p.oauth_grants,
        token_repo=p.oauth_tokens,
        client_repo=p.oauth_clients,
        audit=p.audit,
        uow=p.uow,
    )


def get_manage_own_oauth_grants(p: Platform = Depends(get_platform)) -> ManageOwnOAuthGrants:
    return manage_own_oauth_grants(p)


# ── Peering ──────────────────────────────────────────────────────────


def get_own_base_url() -> str:
    """Where this instance's web app and API live, as other instances reach
    it: `DOMAIN`, which mail links and the passkey relying party use too."""
    return cfg.domain.rstrip("/")


def get_peering_requires_https() -> bool:
    """Peering refuses plain http outside debug mode."""
    return not cfg.debug


@cache
def _peer_client() -> HttpxPeerClient:
    return HttpxPeerClient(webhook_guard(), require_https=not cfg.debug)


def get_peer_client() -> IPeerClient:
    return _peer_client()


# The cookbook registers what happens when a pairing is revoked, from either
# side (removing the peer's mirrors), from the composition root.
PeerRevokedHookFactory = Callable[[AsyncSession], PeerRevokedHook]
_peer_revoked_hooks: list[PeerRevokedHookFactory] = []


def register_peer_revoked_hook(factory: PeerRevokedHookFactory) -> None:
    _peer_revoked_hooks.append(factory)


def _revoked_hooks(p: Platform) -> list[PeerRevokedHook]:
    async def purge_channel(peer: Peer) -> None:
        # The channel state, log and inbound queue of a revoked peer go
        # in the revoking transaction, before the registered hooks run.
        await p.peer_channels.purge(peer.id)

    return [purge_channel, *(factory(p.db) for factory in _peer_revoked_hooks)]


# The cookbook registers what follows a pairing, a first one or one after a
# revoke (sending every recipe the new peer should hold), from the
# composition root.
PeerPairedHookFactory = Callable[[AsyncSession], PeerPairedHook]
_peer_paired_hooks: list[PeerPairedHookFactory] = []


def register_peer_paired_hook(factory: PeerPairedHookFactory) -> None:
    if factory not in _peer_paired_hooks:
        _peer_paired_hooks.append(factory)


# The cookbook registers what follows a change of a peer's switches or
# capabilities (sending or withdrawing recipes, the visibility of mirrors,
# refetching mirrors), from the composition root.
PeerChangedHookFactory = Callable[[AsyncSession], PeerChangedHook]
_peer_changed_hooks: list[PeerChangedHookFactory] = []


def register_peer_changed_hook(factory: PeerChangedHookFactory) -> None:
    if factory not in _peer_changed_hooks:
        _peer_changed_hooks.append(factory)


def _changed_hooks(p: Platform) -> list[PeerChangedHook]:
    async def refetch_on_new_capability(
        peer: Peer, _changed: frozenset[str], gained: frozenset[str]
    ) -> None:
        # A peer that can show more now: compare everything with it again
        # soon, which refetches what the consumers forgot.
        if gained:
            await p.peer_channels.update_state(peer.id, {"reconcile_due_at": now_utc()})

    return [refetch_on_new_capability, *(factory(p.db) for factory in _peer_changed_hooks)]


# The cookbook registers, per item kind, what this instance shares with a
# peer (provider) and how it takes in what a peer shares (consumer), from
# the composition root. Platform moves the items without knowing them.
PeerContentProviderFactory = Callable[[AsyncSession], IPeerContentProvider]
PeerContentConsumerFactory = Callable[[AsyncSession], IPeerContentConsumer]
_peer_content_providers: dict[str, PeerContentProviderFactory] = {}
_peer_content_consumers: dict[str, PeerContentConsumerFactory] = {}


def register_peer_content(
    kind: str,
    *,
    provider: PeerContentProviderFactory | None = None,
    consumer: PeerContentConsumerFactory | None = None,
) -> None:
    """Registers the provider and consumer of an item kind; registering a
    kind again replaces them, so tests can swap in their own."""
    if provider is not None:
        _peer_content_providers[kind] = provider
    if consumer is not None:
        _peer_content_consumers[kind] = consumer


def unregister_peer_content(kind: str) -> None:
    _peer_content_providers.pop(kind, None)
    _peer_content_consumers.pop(kind, None)


def _providers(p: Platform) -> dict[str, IPeerContentProvider]:
    return {kind: factory(p.db) for kind, factory in _peer_content_providers.items()}


def _consumers(p: Platform) -> dict[str, IPeerContentConsumer]:
    return {kind: factory(p.db) for kind, factory in _peer_content_consumers.items()}


def _peering_identity(p: Platform, base_url: str) -> PeeringIdentity:
    return PeeringIdentity(settings_repo=p.settings, base_url=base_url, app_version=VERSION)


def get_manage_peer_invitations(
    p: Platform = Depends(get_platform), base_url: str = Depends(get_own_base_url)
) -> ManagePeerInvitations:
    return ManagePeerInvitations(
        invitations=p.peer_invitations, base_url=base_url, audit=p.audit, uow=p.uow
    )


def get_pair_with_peer(
    p: Platform = Depends(get_platform),
    base_url: str = Depends(get_own_base_url),
    client: IPeerClient = Depends(get_peer_client),
    guard: IWebhookTargetGuard = Depends(get_webhook_guard),
    require_https: bool = Depends(get_peering_requires_https),
) -> PairWithPeer:
    return PairWithPeer(
        peers=p.peers,
        invitations=p.peer_invitations,
        identity=_peering_identity(p, base_url),
        client=client,
        guard=guard,
        settings_repo=p.settings,
        audit=p.audit,
        uow=p.uow,
        require_https=require_https,
        on_paired=[factory(p.db) for factory in _peer_paired_hooks],
    )


def get_manage_peers(
    p: Platform = Depends(get_platform),
    base_url: str = Depends(get_own_base_url),
    client: IPeerClient = Depends(get_peer_client),
    guard: IWebhookTargetGuard = Depends(get_webhook_guard),
    require_https: bool = Depends(get_peering_requires_https),
) -> ManagePeers:
    return ManagePeers(
        peers=p.peers,
        groups=p.groups,
        identity=_peering_identity(p, base_url),
        client=client,
        guard=guard,
        settings_repo=p.settings,
        audit=p.audit,
        uow=p.uow,
        require_https=require_https,
        on_revoked=_revoked_hooks(p),
        on_changed=_changed_hooks(p),
    )


def get_authenticate_peer(
    p: Platform = Depends(get_platform), replay: IReplayGuard = Depends(get_replay_guard)
) -> AuthenticatePeer:
    return AuthenticatePeer(peers=p.peers, replay=replay, audit=p.audit, uow=p.uow)


def get_answer_peer(
    p: Platform = Depends(get_platform), base_url: str = Depends(get_own_base_url)
) -> AnswerPeer:
    return answer_peer(p, base_url)


def manage_peers(
    p: Platform, base_url: str, client: IPeerClient, guard: IWebhookTargetGuard | None = None
) -> ManagePeers:
    return ManagePeers(
        peers=p.peers,
        groups=p.groups,
        identity=_peering_identity(p, base_url),
        client=client,
        guard=guard or webhook_guard(),
        settings_repo=p.settings,
        audit=p.audit,
        uow=p.uow,
        require_https=get_peering_requires_https(),
        on_revoked=_revoked_hooks(p),
        on_changed=_changed_hooks(p),
    )


def answer_peer(p: Platform, base_url: str) -> AnswerPeer:
    return AnswerPeer(
        peers=p.peers,
        identity=_peering_identity(p, base_url),
        audit=p.audit,
        uow=p.uow,
        on_revoked=_revoked_hooks(p),
    )


def peer_channel_jobs(
    p: Platform,
    client: IPeerClient,
    base_url: str,
    guard: IWebhookTargetGuard | None = None,
) -> RunPeerChannelJobs:
    """The channel worker's use case, for the worker in src/bootstrap and
    for tests that drive it by hand."""
    calls = PeerCalls(client=client, settings_repo=p.settings)
    return RunPeerChannelJobs(
        peers=p.peers,
        channels=p.peer_channels,
        channel=p.peer_channel,
        features=p.settings,
        deliver=DeliverPeerEvents(peers=p.peers, channels=p.peer_channels, calls=calls, uow=p.uow),
        sync=SyncFromPeer(
            peers=p.peers,
            channels=p.peer_channels,
            calls=calls,
            consumers=_consumers(p),
            renegotiate=manage_peers(p, base_url, client, guard).renegotiate,
            uow=p.uow,
        ),
        repair=RepairPeerChannel(
            channels=p.peer_channels,
            channel=p.peer_channel,
            providers=_providers(p),
            uow=p.uow,
        ),
        uow=p.uow,
    )


def announce_peer_changes(p: Platform, base_url: str) -> AnnouncePeerChanges:
    return AnnouncePeerChanges(
        peers=p.peers,
        channel=p.peer_channel,
        identity=_peering_identity(p, base_url),
        settings_repo=p.settings,
        uow=p.uow,
    )


def get_peer_contact(p: Platform = Depends(get_platform)) -> PeerContact:
    return PeerContact(peers=p.peers, channels=p.peer_channels, uow=p.uow)


def get_receive_peer_events(
    p: Platform = Depends(get_platform), base_url: str = Depends(get_own_base_url)
) -> ReceivePeerEvents:
    answer = answer_peer(p, base_url)

    async def revoked_by_peer(peer: Peer, context: RequestContext) -> None:
        await answer.revoked_by_peer(peer, context=context)

    return ReceivePeerEvents(channels=p.peer_channels, uow=p.uow, revoked_by_peer=revoked_by_peer)


def get_answer_peer_channel(p: Platform = Depends(get_platform)) -> AnswerPeerChannel:
    return AnswerPeerChannel(channels=p.peer_channels, providers=_providers(p), uow=p.uow)


def get_peer_channel_status(p: Platform = Depends(get_platform)) -> PeerChannelStatus:
    return PeerChannelStatus(peers=p.peers, channels=p.peer_channels, uow=p.uow)
