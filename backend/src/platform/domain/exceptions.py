"""The semantic bases every domain error inherits, and the errors of
Platform itself.

exception_handlers.py maps each semantic base to an HTTP status. An error
that inherits DomainError directly answers 500 without echoing its message.
The cookbook keeps its own errors in its own domain package and inherits
the bases from here."""


class DomainError(Exception):
    """Base for all domain errors."""


# ── Semantic bases ────────────────────────────────────────────────────


class BadRequestError(DomainError):
    """The request cannot be carried out as asked, for example because an
    integration is not configured."""


class AuthenticationError(DomainError):
    """The caller could not be authenticated, for example because a token,
    code or challenge is wrong or expired."""


class ForbiddenError(DomainError):
    """The caller is known but is not allowed to do this."""


class NotFoundError(DomainError):
    """The requested record or resource does not exist."""


class ConflictError(DomainError):
    """The request clashes with the current state of the data, for example
    a duplicate name."""


class PayloadTooLargeError(DomainError):
    """An uploaded file exceeds its size limit."""


class UnsupportedFileTypeError(DomainError):
    """An uploaded file has a type that is not accepted."""


class InvalidInputError(DomainError):
    """The input is well formed but breaks a domain rule."""


class RateLimitedError(DomainError):
    """The caller sent too many requests and has to wait."""

    def __init__(self, message: str, retry_after_seconds: int = 0) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ServiceUnavailableError(DomainError):
    """A feature or external system the request needs is unavailable."""


# ── Authentication ────────────────────────────────────────────────────


class InvalidCredentialsError(AuthenticationError):
    """The login or password is wrong. Unknown logins raise the
    same error, so the answer never tells whether an account exists."""


class InactiveUserError(AuthenticationError):
    """The account exists and the credential was right, but it is disabled."""


class InvalidTokenError(AuthenticationError):
    """A session, challenge, setup, personal access token or API key is
    missing, malformed, expired or revoked."""


class InvalidTotpCodeError(AuthenticationError):
    """The one-time code is wrong, expired or was already used."""


class PasskeyRejectedError(AuthenticationError):
    """A passkey login did not verify or names no registered passkey."""


class LoginLockedError(RateLimitedError):
    """Too many failed logins for this name or address."""


# ── Account and permissions ───────────────────────────────────────────


class PermissionDeniedError(ForbiddenError):
    """The caller lacks the permission an action needs."""


class CsrfHeaderMissingError(ForbiddenError):
    """An unsafe request authenticated by the session cookie lacks the
    header that proves it came from the web app's own script."""


class ApiKeyAuthDisabledError(ForbiddenError):
    """API keys are switched off in the security settings."""


class PasswordConfirmationError(ForbiddenError):
    """A sensitive change to the caller's own account needs the current
    password, and the one given is wrong."""


class TotpRequiredError(ForbiddenError):
    """Two-factor authentication is enforced, so it cannot be turned off."""


class TotpSetupRequiredError(ForbiddenError):
    """The request needs two-factor authentication, which the account has
    not set up yet, such as the settings for a user who holds a settings
    permission but signed in before enrolling."""


class UserNotFoundError(NotFoundError):
    """No user with this id."""


class UserGroupNotFoundError(NotFoundError):
    """No group with this id."""


class SessionNotFoundError(NotFoundError):
    """No session of the caller with this id."""


class TrustedDeviceNotFoundError(NotFoundError):
    """No trusted device of the caller with this id."""


class PasskeyNotFoundError(NotFoundError):
    """No passkey of the caller with this id."""


class TokenNotFoundError(NotFoundError):
    """No personal access token or API key with this id."""


class DuplicateUserError(ConflictError):
    """The e-mail address is already taken."""


class DuplicateGroupError(ConflictError):
    """The group name is already taken."""


class DuplicatePasskeyError(ConflictError):
    """The passkey is already registered."""


class SystemUserProtectedError(ForbiddenError):
    """The system user cannot be deleted, deactivated or stripped of rights."""


class UserOutranksActorError(ForbiddenError):
    """The target account holds permissions the acting administrator does
    not, so the administrator may not change, reset, sign out or delete it."""


class TotpAlreadyEnabledError(ConflictError):
    """Two-factor authentication is already on for this account."""


class TotpNotEnrolledError(ConflictError):
    """Confirming two-factor authentication needs an enrolment first."""


class PasskeyRegistrationFailedError(InvalidInputError):
    """The browser's registration response did not verify."""


class InvalidDateRangeError(InvalidInputError):
    """A date range whose start lies after its end."""


class WeakPasswordError(InvalidInputError):
    """The new password breaks the password rules."""


class InvalidPermissionError(InvalidInputError):
    """A permission is unknown or may not be granted here."""


class InvalidSettingsError(InvalidInputError):
    """A settings value is out of range."""


class PublicRecipesNotAllowedError(InvalidInputError):
    """A recipe or a default visibility was set to public while the instance
    does not allow public recipes."""


class PeerRecipesNotAllowedError(InvalidInputError):
    """A recipe or a default visibility was set to peers (every paired
    instance) while peering is off."""


# ── Agents ────────────────────────────────────────────────────────────


class AgentAccessDisabledError(ForbiddenError):
    """Agent access through the MCP surface is switched off."""


class AgentToolNotAllowedError(ForbiddenError):
    """The token may not run this tool, for example a draft tool with an
    API key."""


class AgentBudgetExceededError(RateLimitedError):
    """The token spent its call or draft budget."""


# ── OAuth ────────────────────────────────────────────────────────────


class OAuthRequestError(InvalidInputError):
    """An OAuth request breaks the protocol. `error` is the RFC 6749 error
    code the client receives (`invalid_request`, `invalid_scope`,
    `invalid_redirect_uri`, `unsupported_grant_type` and the like)."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error


class OAuthGrantError(OAuthRequestError):
    """An authorization code or refresh token is unknown, expired, used or
    issued to another client (`invalid_grant`)."""

    def __init__(self, message: str) -> None:
        super().__init__("invalid_grant", message)


class OAuthClientError(AuthenticationError):
    """The client is unknown or failed to authenticate (`invalid_client`)."""


class OAuthRedirectRejectedError(InvalidInputError):
    """An authorization request names an unknown client or a redirect URI
    the client did not register, or one outside the redirect host
    allowlist. The consent page shows it and never redirects, since the
    target is not trusted."""


class OAuthDisabledError(ForbiddenError):
    """OAuth connections are switched off in the agent settings."""


class OAuthGrantNotFoundError(NotFoundError):
    """No connected app of the caller with this id."""


# ── Public ids ───────────────────────────────────────────────────────


class PublicIdNotFoundError(NotFoundError):
    """No row the user may open has this public id."""


# ── Files ─────────────────────────────────────────────────────────────


class StoredFileNotFoundError(NotFoundError):
    """No stored file with this id."""


class FileInUseError(ConflictError):
    """The file is a recipe image, an avatar or a branding image, so it is
    removed through what uses it rather than on its own."""


class FileTooLargeError(PayloadTooLargeError):
    """The upload is larger than the limit for its kind."""


class FileTypeNotAcceptedError(UnsupportedFileTypeError):
    """The upload is not an image or PDF the storage accepts, or its
    content does not match its declared type."""


# ── Mail ──────────────────────────────────────────────────────────────


class MailNotConfiguredError(BadRequestError):
    """Mail delivery is switched off or has no server configured."""


class MailDeliveryError(ServiceUnavailableError):
    """The mail server refused the message or could not be reached."""


# ── Notifications ─────────────────────────────────────────────────────


class WebhookSubscriptionNotFoundError(NotFoundError):
    """No webhook subscription with this id."""


class WebhookDeliveryNotFoundError(NotFoundError):
    """No delivery with this id in this subscription."""


class InvalidWebhookConfigurationError(InvalidInputError):
    """The webhook URL or event list is not acceptable, for example a URL
    that points at the instance itself."""


class NoticeNotFoundError(NotFoundError):
    """No in-app notice with this id."""


# ── Operations ────────────────────────────────────────────────────────


class BackupAlreadyRequestedError(ConflictError):
    """A backup was requested and the sidecar has not picked it up yet."""


class BackupControlUnavailableError(ServiceUnavailableError):
    """The backup sidecar's control directory is not set up, so "back up
    now" cannot reach it."""


class MaintenanceModeError(ServiceUnavailableError):
    """The instance is in maintenance and read-only."""


# ── Legal and consents ────────────────────────────────────────────────


class PrivacyAcknowledgementRequiredError(ForbiddenError):
    """The user has to acknowledge the current privacy statement first."""


class LegalPageNotFoundError(NotFoundError):
    """No version of this legal page is published yet."""


class StalePrivacyVersionError(ConflictError):
    """The acknowledged version is not the current privacy statement."""


class ConsentRequiredError(ForbiddenError):
    """The action needs a consent the user has not given, such as agent
    tokens without the AI agents consent."""


# ── Peering ───────────────────────────────────────────────────────────


class PeeringDisabledError(NotFoundError):
    """The peering feature switch is off, so every peering route answers as
    if it did not exist."""


class PeerNotFoundError(NotFoundError):
    """No paired instance with this id."""


class PeerInvitationNotFoundError(NotFoundError):
    """No open peering invitation with this id."""


class InvalidPeerInvitationError(AuthenticationError):
    """The invitation code of a handshake is unknown, used or expired."""


class PeerAuthenticationError(AuthenticationError):
    """A peering request is not signed by an active peer: unknown sender,
    revoked pairing, wrong signature, a timestamp outside the window or a
    replayed message id."""


class PeerAlreadyPairedError(ConflictError):
    """The instance is already paired and active; revoke the pairing before
    pairing again."""


class PeeringVersionMismatchError(InvalidInputError):
    """The two instances share no protocol version, or no version of a
    required format. The message names the versions of both sides."""


class InvalidPeerConfigurationError(InvalidInputError):
    """An invitation link, a peer's base URL or a peer's identity is not
    acceptable, for example a URL the target guard refuses or plain http
    outside debug mode."""


class PeerRefusedError(BadRequestError):
    """The peer answered a peering request with a refusal. The message
    repeats the peer's own, shortened."""


class PeerUnreachableError(ServiceUnavailableError):
    """The peer could not be reached or did not answer with a peering
    answer."""
