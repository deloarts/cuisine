"""
Recovery commands for the operator, run inside the backend container:

    python -m src.bootstrap.cli.admin reset-password <email or system>
    python -m src.bootstrap.cli.admin reset-totp <email or system>
    python -m src.bootstrap.cli.admin maintenance on|off|status [--message TEXT]

Both sign the account out everywhere. The new password is read from the
terminal, never from the command line, so it stays out of the shell history.
"""

import argparse
import asyncio
import getpass
import sys

from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemyTrustedDeviceRepository,
)
from src.platform.adapters.outbound.persistence.repositories.security_repositories import (
    SqlAlchemyUserSessionRepository,
)
from src.platform.adapters.outbound.persistence.repositories.settings_repository import (
    SqlAlchemySettingsRepository,
)
from src.platform.adapters.outbound.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from src.platform.adapters.outbound.persistence.session import SessionLocal
from src.platform.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.platform.domain.entities.settings import MaintenanceSettings
from src.platform.domain.exceptions import WeakPasswordError
from src.platform.domain.services.password_rules import assert_password_acceptable
from src.platform.infrastructure.security.hashing import BcryptPasswordHasher
from src.shared_kernel.domain.services.clock import now_utc


async def _reset(login: str, *, password: str | None, totp: bool) -> int:
    async with SessionLocal() as db:
        users = SqlAlchemyUserRepository(db)
        user = await users.get_by_login(login)
        if user is None or user.is_service_account:
            print(f"No user {login!r}.", file=sys.stderr)
            return 1
        if password is not None:
            security = await SqlAlchemySettingsRepository(db).get_security()
            try:
                assert_password_acceptable(password, security.min_password_length, email=user.email)
            except WeakPasswordError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            user.hashed_password = await BcryptPasswordHasher().hash(password)
        if totp:
            user.totp_enabled = False
            user.totp_secret = None
            await SqlAlchemyTrustedDeviceRepository(db).revoke_all(user.id, now_utc())
        user.token_version += 1
        await users.save(user)
        await SqlAlchemyUserSessionRepository(db).revoke_all(user.id, now_utc())
        await SqlAlchemyUnitOfWork(db).commit()
    print(f"Done. {login!r} is signed out everywhere.")
    return 0


async def _maintenance(action: str, message: str | None) -> int:
    """Switches maintenance mode from the server, for upgrades and restores:
    the app turns read-only within a few seconds on every worker."""
    async with SessionLocal() as db:
        repo = SqlAlchemySettingsRepository(db)
        current = await repo.get_maintenance()
        if action == "status":
            state = "on" if current.enabled else "off"
            print(
                f"Maintenance mode is {state}."
                + (f" Since {current.since}." if current.since else "")
            )
            return 0
        enabled = action == "on"
        messages = {"en-GB": message} if message else current.messages
        await repo.save_maintenance(
            MaintenanceSettings(
                enabled=enabled,
                messages=messages if enabled else current.messages,
                since=(current.since or now_utc()) if enabled else None,
            )
        )
        await SqlAlchemyUnitOfWork(db).commit()
    print(f"Maintenance mode is {action}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="admin")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("reset-password").add_argument("login")
    sub.add_parser("reset-totp").add_argument("login")
    maintenance = sub.add_parser("maintenance")
    maintenance.add_argument("action", choices=["on", "off", "status"])
    maintenance.add_argument("--message", default=None)
    args = parser.parse_args(argv)

    if args.command == "maintenance":
        return asyncio.run(_maintenance(args.action, args.message))

    if args.command == "reset-password":
        first = getpass.getpass("New password: ")
        if first != getpass.getpass("Repeat: "):
            print("The passwords differ.", file=sys.stderr)
            return 1
        return asyncio.run(_reset(args.login, password=first, totp=False))
    return asyncio.run(_reset(args.login, password=None, totp=True))


if __name__ == "__main__":
    raise SystemExit(main())
