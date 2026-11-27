"""The theme choices a user picks on their account page. They are display
preferences only; the frontend maps them onto OpenVue presets and the
palettes in frontend/src/core/config/colorPalettes.ts, whose names these
values must match."""

from src.shared_kernel.domain.value_objects.value_enum import StrValueEnum


class ThemePreset(StrValueEnum):
    AURA = "Aura"
    LARA = "Lara"
    MATERIAL = "Material"
    NORA = "Nora"


class ThemeSurface(StrValueEnum):
    NEUTRAL = "neutral"
    SLATE = "slate"
    GRAY = "gray"
    ZINC = "zinc"
    STONE = "stone"
    SOHO = "soho"
    VIVA = "viva"
    OCEAN = "ocean"


class ThemePrimary(StrValueEnum):
    CUISINE = "cuisine"
    SOUL = "soul"
    RED = "red"
    ORANGE = "orange"
    EMERALD = "emerald"
    GREEN = "green"
    LIME = "lime"
    AMBER = "amber"
    YELLOW = "yellow"
    TEAL = "teal"
    CYAN = "cyan"
    SKY = "sky"
    BLUE = "blue"
    INDIGO = "indigo"
    VIOLET = "violet"
    PURPLE = "purple"
    FUCHSIA = "fuchsia"
    PINK = "pink"
    ROSE = "rose"
