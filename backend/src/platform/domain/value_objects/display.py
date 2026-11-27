"""How the instance shows units, dates and times by default. Each user's
own language still decides the words; these decide the formats."""

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class UnitSystem(StrValueEnum):
    # Only metric exists today; the setting is there so imperial can follow
    # without a settings change for existing instances.
    METRIC = "metric"


class DateFormat(StrValueEnum):
    # 21.11.2026
    DMY_DOT = "dd.mm.yyyy"
    # 21/11/2026
    DMY_SLASH = "dd/mm/yyyy"
    # 2026-11-21
    ISO = "yyyy-mm-dd"
    # 11/21/2026
    MDY_SLASH = "mm/dd/yyyy"


class TimeFormat(StrValueEnum):
    H24 = "24h"
    H12 = "12h"


class Weekday(StrValueEnum):
    MONDAY = "monday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class BannerSeverity(StrValueEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AmountStyle(StrValueEnum):
    """How a user reads small metric amounts in recipes, a display
    preference only. Counts read as fractions either way."""

    # 0,125 l and 0,25 kg, exact to three decimals.
    DECIMALS = "decimals"
    # ⅛ l and ¼ kg when the amount is a common kitchen fraction of a
    # litre or kilogram, exact decimals otherwise.
    FRACTIONS = "fractions"
