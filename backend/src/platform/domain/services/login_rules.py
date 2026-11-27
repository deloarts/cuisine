"""
The second-factor policy of the login.

The system user holds every permission, so it never gets a session on a
password alone: its two-factor authentication is mandatory whatever the
security settings say, it cannot be turned off in the app, and "trust this
device" never skips it. A lost authenticator is recovered on the server with
`admin reset-totp system`, which walks the account through enrolment again
at its next sign-in. Passkeys would sign it in without the code, so it
cannot use them.

Whoever may read or change the instance settings needs two-factor
authentication too, whatever the security settings say: such an account
enrols at its next sign-in, cannot turn it off while it holds either
permission, and until it has enrolled the settings refuse it.
"""

from src.platform.domain.entities.user import User
from src.platform.domain.exceptions import SystemUserProtectedError
from src.platform.domain.exceptions import TotpRequiredError
from src.platform.domain.value_objects.permission import Permission

# The permissions that only an account with two-factor authentication uses.
TOTP_GUARDED_PERMISSIONS: frozenset[str] = frozenset(
    {Permission.READ_SETTINGS, Permission.WRITE_SETTINGS}
)


def totp_mandatory(user: User) -> bool:
    """Whether the user needs two-factor authentication whatever the
    security settings say: the system user, and anyone holding a settings
    permission directly or through a group."""
    return user.is_systemuser or not TOTP_GUARDED_PERMISSIONS.isdisjoint(user.effective_permissions)


def totp_enrolment_required(user: User, *, enforce_totp: bool) -> bool:
    """Whether a user without two-factor authentication must enrol before
    getting a session: everyone while enforcement is on, and always the
    users for whom it is mandatory."""
    return enforce_totp or totp_mandatory(user)


def permission_needs_totp(user: User, permission: str) -> bool:
    """Whether `permission` is refused to the user for now because it
    needs two-factor authentication the user has not set up yet. The system
    user never gets a session without its code, so it is not asked again."""
    if user.is_systemuser:
        return False
    return permission in TOTP_GUARDED_PERMISSIONS and not user.totp_enabled


def effective_trusted_device_days(user: User, configured_days: int) -> int:
    """How many days "trust this device" may skip the second factor. Always
    0 for the system user, whose mandatory code would otherwise be true in
    name only."""
    if user.is_systemuser:
        return 0
    return configured_days


def assert_can_disable_totp(user: User) -> None:
    """Refuses turning off two-factor authentication for the system user."""
    if user.is_systemuser:
        raise SystemUserProtectedError(
            "Two-factor authentication is mandatory for the system user. Use "
            "`admin reset-totp system` on the server, which asks for a new setup "
            "at the next sign-in."
        )
    if totp_mandatory(user):
        raise TotpRequiredError(
            "Two-factor authentication is required for accounts that may read or change "
            "the settings."
        )


def assert_can_use_passkeys(user: User) -> None:
    """Refuses passkeys for the system user, which signs in with its
    password and code only."""
    if user.is_systemuser:
        raise SystemUserProtectedError("The system user signs in with its password and code only.")
