"""The kinds of mail the instance sends and the operational alerts."""

from dataclasses import dataclass

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class MailTemplateKind(StrValueEnum):
    TEST_MAIL = "test_mail"
    OPERATIONAL_ALERT = "operational_alert"
    USER_CREATED = "user_created"


class AlertKind(StrValueEnum):
    BACKUP_FAILED = "backup_failed"
    WEBHOOK_DISABLED = "webhook_disabled"
    MAINTENANCE_SWITCHED = "maintenance_switched"
    STORAGE_WARNING = "storage_warning"


@dataclass(frozen=True)
class AlertSpec:
    kind: AlertKind
    # One sentence for the admin's alert list.
    description: str


ALERTS: dict[AlertKind, AlertSpec] = {
    AlertKind.BACKUP_FAILED: AlertSpec(
        AlertKind.BACKUP_FAILED, "The nightly or a manual database dump failed or is overdue."
    ),
    AlertKind.WEBHOOK_DISABLED: AlertSpec(
        AlertKind.WEBHOOK_DISABLED,
        "A webhook was switched off after its last deliveries all failed.",
    ),
    AlertKind.MAINTENANCE_SWITCHED: AlertSpec(
        AlertKind.MAINTENANCE_SWITCHED, "Maintenance mode was switched on or off."
    ),
    AlertKind.STORAGE_WARNING: AlertSpec(
        AlertKind.STORAGE_WARNING, "The storage and backup check found a new warning."
    ),
}
