"""Theme palette and stylesheet generation for DATO Toolkit.

This app ships a single visual theme (the TRACE-inspired dark palette
defined in app.design.tokens). THEME_LIGHT / theme-switching machinery
is kept at the function-signature level only, so app/settings.py and
main.py don't need changes in this pass - see docs/superpowers/plans/
2026-07-01-visual-redesign.md Task 2 for why. Light mode is future work.

The color() function is a TRANSITIONAL SHIM: it maps the old semantic
palette key names (used by pages not yet rebuilt in this redesign) onto
the new Color tokens, so unmigrated pages keep rendering correctly
during the phased rollout. Delete it once every page has been rebuilt
(Phase 9) and a grep confirms no callers remain.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from app.design.tokens import Color, FontSize, FONT_FAMILY, Radius, Spacing

THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_NAMES = (THEME_DARK, THEME_LIGHT)
DEFAULT_THEME = THEME_DARK

# TRANSITIONAL: old semantic key -> new token. See module docstring.
_LEGACY_COLOR_MAP: dict[str, str] = {
    "background": Color.PAGE_BG,
    "surface": Color.CARD_BG,
    "accent": Color.CARD_BG,
    "button_hover": Color.BORDER_STRONG,
    "button_pressed": Color.SIDEBAR_BG,
    "button_disabled_bg": Color.CARD_BG,
    "highlight": Color.ACCENT,
    "highlight_hover": Color.ACCENT_HOVER,
    "highlight_disabled_bg": Color.BORDER_STRONG,
    "text": Color.TEXT_PRIMARY,
    "muted_text": Color.TEXT_MUTED,
    "border": Color.BORDER,
    "success": Color.SUCCESS,
    "warning": Color.WARNING,
    "error": Color.DANGER,
    "chrome_hover": Color.BORDER_STRONG,
}

_active_theme = DEFAULT_THEME


def set_active_theme(theme: str) -> None:
    """Set the theme used by `color()` lookups for newly built widgets."""
    global _active_theme
    _active_theme = theme if theme in THEME_NAMES else DEFAULT_THEME


def get_active_theme() -> str:
    return _active_theme


def color(name: str, theme: str | None = None) -> str:
    """TRANSITIONAL: look up a legacy palette key, mapped to its new token."""
    return _LEGACY_COLOR_MAP[name]


def build_stylesheet(theme: str) -> str:
    """Build the application-wide QSS. `theme` is accepted for call-site
    compatibility but ignored - this pass ships a single dark theme."""
    return f"""
* {{
    font-family: "{FONT_FAMILY}", "Calibri", sans-serif;
    color: {Color.TEXT_PRIMARY};
}}

QMainWindow, QWidget {{
    background-color: {Color.PAGE_BG};
}}

QLabel {{
    background: transparent;
}}

QLabel[role="muted"] {{
    color: {Color.TEXT_MUTED};
}}

QLabel[role="heading"] {{
    font-size: {FontSize.PAGE_TITLE}px;
    font-weight: 600;
}}

QFrame[card="true"] {{
    background-color: {Color.CARD_BG};
    border-radius: {Radius.CARD}px;
    border: 1px solid {Color.BORDER};
}}

QPushButton {{
    background-color: {Color.CARD_BG};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER_STRONG};
    border-radius: {Radius.BUTTON}px;
    padding: {Spacing.SM}px {Spacing.LG}px;
    font-size: {FontSize.SECTION}px;
}}

QPushButton:hover {{
    background-color: {Color.BORDER_STRONG};
}}

QPushButton:pressed {{
    background-color: {Color.SIDEBAR_BG};
}}

QPushButton:disabled {{
    background-color: {Color.CARD_BG};
    color: {Color.TEXT_MUTED};
}}

QPushButton[accent="true"] {{
    background-color: {Color.ACCENT};
    color: {Color.TEXT_PRIMARY};
    font-weight: 600;
    font-size: {FontSize.SECTION}px;
    padding: {Spacing.MD}px {Spacing.XXL}px;
    border: none;
    border-radius: {Radius.BUTTON}px;
}}

QPushButton[accent="true"]:hover {{
    background-color: {Color.ACCENT_HOVER};
}}

QPushButton[accent="true"]:disabled {{
    background-color: {Color.BORDER_STRONG};
    color: {Color.TEXT_MUTED};
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    border: 1px solid {Color.BORDER};
}}

QPushButton[flat="true"]:hover {{
    background-color: {Color.CARD_BG};
}}

QLineEdit, QTextEdit, QComboBox {{
    background-color: {Color.INPUT_BG};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.INPUT}px;
    padding: {Spacing.SM}px {Spacing.MD}px;
    selection-background-color: {Color.ACCENT};
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {Color.ACCENT};
}}

QListWidget {{
    background-color: {Color.CARD_BG};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.CARD}px;
    padding: {Spacing.SM}px;
}}

QListWidget::item {{
    background-color: {Color.INPUT_BG};
    border-radius: {Radius.BUTTON}px;
    padding: {Spacing.SM}px;
    margin: {Spacing.XS}px;
}}

QListWidget::item:selected {{
    background-color: {Color.ACCENT_BG_TINT};
    border: 1px solid {Color.ACCENT};
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: {Color.PAGE_BG};
    width: {Spacing.SM}px;
    border-radius: {Radius.INPUT}px;
}}

QScrollBar::handle:vertical {{
    background: {Color.BORDER_STRONG};
    border-radius: {Radius.INPUT}px;
    min-height: {Spacing.XXL}px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Color.ACCENT};
}}

QProgressBar {{
    background-color: {Color.CARD_BG};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.BUTTON}px;
    text-align: center;
    height: {Spacing.LG}px;
}}

QProgressBar::chunk {{
    background-color: {Color.ACCENT};
    border-radius: {Radius.INPUT}px;
}}

QStatusBar {{
    background-color: {Color.SIDEBAR_BG};
    color: {Color.TEXT_MUTED};
    border-top: 1px solid {Color.BORDER};
}}

QToolTip {{
    background-color: {Color.CARD_BG};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.ACCENT};
    border-radius: {Radius.INPUT}px;
    padding: {Spacing.XS}px {Spacing.SM}px;
}}

QCheckBox::indicator {{
    width: {Spacing.LG}px;
    height: {Spacing.LG}px;
    border-radius: {Spacing.XS}px;
    border: 1px solid {Color.BORDER};
    background: {Color.INPUT_BG};
}}

QCheckBox::indicator:checked {{
    background: {Color.ACCENT};
    border: 1px solid {Color.ACCENT};
}}
"""


def apply_card_shadow(widget: QWidget) -> None:
    """Apply a subtle drop shadow to a card-style widget."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(24)
    effect.setOffset(0, 4)
    effect.setColor(QColor(0, 0, 0, 160))
    widget.setGraphicsEffect(effect)
