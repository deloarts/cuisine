"""The scopes a signed web token can carry. A session token has none; the
others are short-lived bridges between the steps of a login and are refused
everywhere else."""

# A full web session, the absence of a scope claim.
SESSION = ""
# Password proven, TOTP code still owed. Accepted by the TOTP step only.
TOTP_PENDING = "totp_pending"
# Two-factor authentication is enforced but not set up yet. Accepted by the
# enrolment endpoints only, which then hand out a real session.
TOTP_SETUP = "totp_setup"
# A WebAuthn challenge between the options and the verify request.
PASSKEY_LOGIN = "passkey_login"
PASSKEY_REGISTRATION = "passkey_registration"
