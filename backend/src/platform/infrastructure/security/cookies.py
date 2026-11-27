"""
The httponly cookies of the web login: the session token and the
trusted-device secret. Keeping them out of JavaScript's reach is the whole
point: an XSS payload has nothing to exfiltrate. Secure unless debug, so a
plain-http dev server still works.
"""

from fastapi import Response

from src.platform.infrastructure.config.settings import cfg

SESSION_COOKIE = "cuisine_session"
TRUSTED_DEVICE_COOKIE = "cuisine_trusted_device"
# The trusted-device cookie is only ever needed by the login endpoints.
TRUSTED_DEVICE_COOKIE_PATH = "/api/v1/auth"


def set_session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        path="/",
        httponly=True,
        samesite="strict",
        secure=not cfg.debug,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True, samesite="strict", secure=not cfg.debug
    )


def set_trusted_device_cookie(response: Response, secret: str, max_age: int) -> None:
    response.set_cookie(
        TRUSTED_DEVICE_COOKIE,
        secret,
        max_age=max_age,
        path=TRUSTED_DEVICE_COOKIE_PATH,
        httponly=True,
        samesite="strict",
        secure=not cfg.debug,
    )
