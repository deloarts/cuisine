"""
The kinds of security events the security log records, and their outcome.

A login is one type with a success or failure outcome, so the log can be
filtered for every failed login at once. The other types record a change
that happened, so their outcome is success, except a refused password
confirmation, a refused pairing, a failed peer authentication, a denied
OAuth approval and a reused OAuth token or code, which are failures.
"""

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class SecurityEventType(StrValueEnum):
    LOGIN = "login"
    LOGIN_THROTTLED = "login_throttled"
    LOGOUT = "logout"
    PASSWORD_CONFIRMATION = "password_confirmation"
    SESSION_REVOKED = "session_revoked"
    USER_CREATED = "user_created"
    USER_CHANGED = "user_changed"
    USER_DELETED = "user_deleted"
    USER_DEACTIVATED = "user_deactivated"
    USER_REACTIVATED = "user_reactivated"
    USER_PERMISSIONS_CHANGED = "user_permissions_changed"
    USER_GROUPS_CHANGED = "user_groups_changed"
    USER_FORCED_LOGOUT = "user_forced_logout"
    GROUP_CREATED = "group_created"
    GROUP_CHANGED = "group_changed"
    GROUP_DELETED = "group_deleted"
    PAT_CREATED = "pat_created"
    PAT_REVOKED = "pat_revoked"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    PASSWORD_CHANGED = "password_changed"
    TOTP_ENABLED = "totp_enabled"
    TOTP_DISABLED = "totp_disabled"
    TOTP_RESET = "totp_reset"
    TRUSTED_DEVICE_REVOKED = "trusted_device_revoked"
    PASSKEY_ADDED = "passkey_added"
    PASSKEY_REMOVED = "passkey_removed"
    SETTINGS_CHANGED = "settings_changed"
    PEER_INVITATION_CREATED = "peer_invitation_created"
    PEER_INVITATION_REVOKED = "peer_invitation_revoked"
    PEER_PAIRED = "peer_paired"
    PEER_PAIRING_REFUSED = "peer_pairing_refused"
    PEER_CHANGED = "peer_changed"
    PEER_REVOKED = "peer_revoked"
    PEER_AUTH_FAILED = "peer_auth_failed"
    OAUTH_CLIENT_REGISTERED = "oauth_client_registered"
    OAUTH_GRANT_APPROVED = "oauth_grant_approved"
    OAUTH_GRANT_DENIED = "oauth_grant_denied"
    OAUTH_GRANT_REVOKED = "oauth_grant_revoked"
    OAUTH_TOKEN_REUSED = "oauth_token_reused"


class SecurityEventOutcome(StrValueEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class LoginMethod(StrValueEnum):
    """How a login proved who the user is, kept in a login event's detail."""

    PASSWORD = "password"
    TOTP = "totp"
    PASSKEY = "passkey"
    TOTP_ENROLMENT = "totp_enrolment"


class LoginRefusal(StrValueEnum):
    """Why a login or a password confirmation was refused, kept in the
    event's detail."""

    INVALID_CREDENTIALS = "invalid_credentials"
    INACTIVE = "inactive"
    INVALID_TOTP = "invalid_totp"
    PASSKEY_REJECTED = "passkey_rejected"
