"""
Single source of truth for all colors, spacing, radius, and typography
in the app. No hex color, pixel spacing value, or font size should
appear as a literal anywhere else in the codebase - everything
references these constants.
"""


class Color:
    # Surfaces
    PAGE_BG = "#0c0c0e"
    SIDEBAR_BG = "#131316"
    CARD_BG = "#151517"
    TABLE_HEADER_BG = "#1a1a1d"
    INPUT_BG = "#0f0f11"

    # Borders
    BORDER = "#232326"
    BORDER_STRONG = "#2f2f34"

    # Text
    TEXT_PRIMARY = "#f4f4f5"
    TEXT_SECONDARY = "#d4d4d8"
    TEXT_MUTED = "#8b8b90"
    TEXT_FAINT = "#6b6b70"

    # Accent (blue - replaces the old red-pink brand accent everywhere)
    ACCENT = "#2563eb"
    ACCENT_HOVER = "#1d4ed8"
    ACCENT_TEXT = "#7fb0ff"
    ACCENT_BG_TINT = "#1a2c50"

    # Semantic
    SUCCESS = "#00B050"
    SUCCESS_HOVER = "#009a45"
    WARNING = "#f4b13b"
    DANGER = "#ef4444"


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 18
    XL = 22
    XXL = 28
    XXXL = 36


class Radius:
    INPUT = 7
    BUTTON = 8
    CARD = 10
    SIDEBAR_ITEM = 8
    PILL = 999


class FontSize:
    LABEL = 15
    SMALL = 15
    BODY = 16
    SECTION = 16
    PAGE_TITLE = 22
    STAT_NUMBER = 28


FONT_FAMILY = "Segoe UI"
