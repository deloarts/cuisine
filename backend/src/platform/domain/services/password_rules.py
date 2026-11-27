"""The rules a new password must meet."""

from src.platform.domain.exceptions import WeakPasswordError

# bcrypt reads only the first 72 bytes, so a longer password gains nothing.
MAX_PASSWORD_BYTES = 72


def assert_password_acceptable(password: str, min_length: int, *, email: str = "") -> None:
    if len(password) < min_length:
        raise WeakPasswordError(f"The password must be at least {min_length} characters long.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise WeakPasswordError(f"The password must be at most {MAX_PASSWORD_BYTES} bytes long.")
    if email and password.strip().lower() == email.strip().lower():
        raise WeakPasswordError("The password must not be the e-mail address.")
