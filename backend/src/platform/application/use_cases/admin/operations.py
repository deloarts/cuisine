"""
Operations the admin area triggers or the nightly job runs: "back up now",
the restore guidance, the retention purge and the checks that mail an
alert when a backup failed or a new storage warning appeared.
"""

from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from src.platform.application.services.mailer import Mailer
from src.platform.application.use_cases.admin.system import ReadStorageStatus
from src.platform.domain.entities.settings import RetentionSettings
from src.platform.domain.exceptions import BackupAlreadyRequestedError
from src.platform.domain.exceptions import BackupControlUnavailableError
from src.platform.domain.value_objects.mail import AlertKind
from src.platform.domain.value_objects.storage_warning import StorageWarning
from src.platform.ports.outbound.backup_control import IBackupControl
from src.platform.ports.outbound.repositories.agent_call_repository import IAgentCallRepository
from src.platform.ports.outbound.repositories.security_event_repository import (
    ISecurityEventRepository,
)
from src.platform.ports.outbound.repositories.settings_repository import ISettingsRepository
from src.platform.ports.outbound.repositories.webhook_repository import IWebhookDeliveryRepository
from src.platform.ports.outbound.unit_of_work import IUnitOfWork
from src.shared_kernel.domain.services.clock import now_utc

# A purge step another package adds (the cookbook's recipe revisions): it
# gets the retention settings and returns how many rows it removed, in the
# purge's transaction.
Purger = Callable[[RetentionSettings], Awaitable[int]]

# Warnings that describe the setup, not a problem that appeared; they are
# shown in the tab but never mailed.
_STANDING = frozenset({StorageWarning.BACKUPS_ON_DATABASE_HOST})


class RequestBackupNow:
    def __init__(self, *, control: IBackupControl) -> None:
        self._control = control

    async def run(self) -> None:
        if not self._control.available:
            raise BackupControlUnavailableError(
                "The backup sidecar is not reachable; set BACKUP__CONTROL_DIR and share it "
                "with the backup service."
            )
        if await self._control.pending():
            raise BackupAlreadyRequestedError("A backup is already requested.")
        await self._control.request(now_utc())


@dataclass(frozen=True)
class RestoreStep:
    text: str
    command: str | None = None


_GUIDANCE = {
    "en-GB": [
        "Restoring replaces the whole database; take a dump on demand first if the current state "
        "may still be needed.",
        "Stop the backend and the frontend.",
        "Empty the database.",
        "Restore the dump.",
        "Start everything again. The env file must hold the same SECURITY__ENCRYPTION_KEY as when "
        "the dump was taken.",
    ],
    "de-AT": [
        "Ein Restore ersetzt die ganze Datenbank; mach vorher eine Sicherung, falls der jetzige "
        "Stand noch gebraucht wird.",
        "Stopp Backend und Frontend.",
        "Leer die Datenbank.",
        "Spiel die Sicherung ein.",
        "Starte alles wieder. Die Env-Datei braucht denselben SECURITY__ENCRYPTION_KEY wie beim "
        "Erstellen der Sicherung.",
    ],
}


def restore_guidance(locale: str, dump_name: str | None) -> list[RestoreStep]:
    """The restore steps of docs/OPERATIONS.md section 3 with the newest
    dump's name filled in. Restoring stays a task on the server."""
    texts = _GUIDANCE.get(locale, _GUIDANCE["en-GB"])
    dump = dump_name or "cuisine-<date>.dump"
    db = '"$POSTGRES_DB"'
    user = '"$POSTGRES_USER"'
    return [
        RestoreStep(texts[0]),
        RestoreStep(texts[1], "docker compose stop backend frontend"),
        RestoreStep(
            texts[2],
            f"docker compose exec -T postgres sh -c 'dropdb -U {user} {db} && "
            f"createdb -U {user} {db}'",
        ),
        RestoreStep(
            texts[3],
            f"docker compose exec -T postgres sh -c 'pg_restore -U {user} -d {db} --no-owner' "
            f"< {dump}",
        ),
        RestoreStep(texts[4], "docker compose up -d"),
    ]


class PurgeExpired:
    def __init__(
        self,
        *,
        settings_repo: ISettingsRepository,
        events: ISecurityEventRepository,
        agent_calls: IAgentCallRepository,
        deliveries: IWebhookDeliveryRepository,
        uow: IUnitOfWork,
        extra: list[Purger] | None = None,
    ) -> None:
        self._settings = settings_repo
        self._events = events
        self._agent_calls = agent_calls
        self._deliveries = deliveries
        self._uow = uow
        self._extra = extra or []

    async def run(self) -> dict[str, int]:
        retention = await self._settings.get_retention()
        now = now_utc()
        removed: dict[str, int] = {}
        if retention.security_log_days:
            removed["security_log"] = await self._events.delete_older_than(
                now - timedelta(days=retention.security_log_days)
            )
        if retention.agent_calls_days:
            removed["agent_calls"] = await self._agent_calls.delete_older_than(
                now - timedelta(days=retention.agent_calls_days)
            )
        if retention.webhook_deliveries_days:
            removed["webhook_deliveries"] = await self._deliveries.prune(
                now - timedelta(days=retention.webhook_deliveries_days)
            )
        for index, purge in enumerate(self._extra):
            removed[f"extra_{index}"] = await purge(retention)
        await self._uow.commit()
        return removed


class RunNightlyChecks:
    """Mails an alert once per failed backup run and once per storage
    warning that was not there at the last check."""

    def __init__(
        self,
        *,
        settings_repo: ISettingsRepository,
        storage: ReadStorageStatus,
        control: IBackupControl,
        mailer: Mailer,
        uow: IUnitOfWork,
    ) -> None:
        self._settings = settings_repo
        self._storage = storage
        self._control = control
        self._mailer = mailer
        self._uow = uow

    async def run(self) -> list[str]:
        state = dict(await self._settings.get_job_state())
        alerted: list[str] = []
        last = await self._control.last_run()
        if last is not None and last.ok is False:
            key = last.started.isoformat()
            if state.get("alerted_backup_run") != key:
                await self._mailer.alert(
                    AlertKind.BACKUP_FAILED,
                    f"The {last.trigger} backup that started at {key} failed. Check the backup "
                    "service's log: docker compose logs backup.",
                )
                state["alerted_backup_run"] = key
                alerted.append(AlertKind.BACKUP_FAILED.value)
        status = await self._storage.run()
        current = sorted(w.value for w in status.warnings if w not in _STANDING)
        before = state.get("alerted_warnings")
        known = set(before) if isinstance(before, list) else set()
        new = [w for w in current if w not in known]
        if new:
            await self._mailer.alert(
                AlertKind.STORAGE_WARNING,
                "New storage and backup warnings: " + ", ".join(new) + ". See the admin area's "
                "Storage and backup tab.",
            )
            alerted.append(AlertKind.STORAGE_WARNING.value)
        state["alerted_warnings"] = current
        state["last_checked"] = now_utc().isoformat()
        await self._settings.save_job_state(state)
        await self._uow.commit()
        return alerted
