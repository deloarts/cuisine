"""The interface languages. The values are the frontend's locale codes."""

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class Language(StrValueEnum):
    DE_AT = "deAT"
    EN_GB = "enGB"
