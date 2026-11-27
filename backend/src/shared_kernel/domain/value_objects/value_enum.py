"""A str enum whose str() is its value, so it can be written to logs, JSON
and database columns without `.value` everywhere."""

from enum import Enum


class StrValueEnum(str, Enum):
    def __str__(self) -> str:
        return str(self.value)
