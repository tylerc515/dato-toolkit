"""Theme palettes and stylesheet generation for DATO Toolkit."""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget

THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_NAMES = (THEME_DARK, THEME_LIGHT)
DEFAULT_THEME = THEME_DARK

THEMES: dict[str, dict[str, str]] = {
    THEME_DARK: {
        "background": "#1a1a2e",
        "surface": "#16213e",
        "accent": "#0f3460",
        "button_hover": "#16498a",
        "button_pressed": "#0a2745",
        "button_disabled_bg": "#2a3050",
        "highlight": "#e94560",
        "highlight_hover": "#ff5c75",
        "highlight_disabled_bg": "#5b3641",
        "text": "#eaeaea",
        "muted_text": "#9aa0b4",
        "border": "#2c3759",
        "success": "#3ddc97",
        "warning": "#f7b731",
        "error": "#e94560",
        "chrome_hover": "#2a2a4a",
    },
    THEME_LIGHT: {
        "background": "#f3f5fa",
        "surface": "#ffffff",
        "accent": "#3a5a99",
        "button_hover": "#4a6cae",
        "button_pressed": "#2c4677",
        "button_disabled_bg": "#e4e7f0",
        "highlight": "#e94560",
        "highlight_hover": "#ff5c75",
        "highlight_disabled_bg": "#f4d9de",
        "text": "#1a1a2e",
        "muted_text": "#6b7290",
        "border": "#d6dbe8",
        "success": "#1f9d63",
        "warning": "#f7b731",
        "error": "#d33b54",
        "chrome_hover": "#e2e6f0",
    },
}

_active_theme = DEFAULT_THEME


def set_active_theme(theme: str) -> None:
    """Set the theme used by `color()` lookups for newly built widgets."""
    global _active_theme
    _active_theme = theme if theme in THEMES else DEFAULT_THEME


def get_active_theme() -> str:
    return _active_theme


def color(name: str, theme: str | None = None) -> str:
    """Look up a palette color by name for the given (or active) theme."""
    palette = THEMES.get(theme or _active_theme, THEMES[DEFAULT_THEME])
    return palette[name]


def build_stylesheet(theme: str) -> str:
    """Build the application-wide QSS for the given theme."""
    p = THEMES.get(theme, THEMES[DEFAULT_THEME])
    return f"""
* {{
    font-family: "Segoe UI", "Calibri", sans-serif;
    color: {p["text"]};
}}

QMainWindow, QWidget {{
    background-color: {p["background"]};
}}

QLabel {{
    background: transparent;
}}

QLabel[role="muted"] {{
    color: {p["muted_text"]};
}}

QLabel[role="heading"] {{
    font-size: 18px;
    font-weight: 600;
}}

QFrame[card="true"] {{
    background-color: {p["surface"]};
    border-radius: 12px;
    border: 1px solid {p["border"]};
}}

QPushButton {{
    background-color: {p["accent"]};
    color: {p["text"]};
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {p["button_hover"]};
}}

QPushButton:pressed {{
    background-color: {p["button_pressed"]};
}}

QPushButton:disabled {{
    background-color: {p["button_disabled_bg"]};
    color: {p["muted_text"]};
}}

QPushButton[accent="true"] {{
    background-color: {p["highlight"]};
    font-weight: 600;
    font-size: 15px;
    padding: 12px 24px;
    border-radius: 10px;
}}

QPushButton[accent="true"]:hover {{
    background-color: {p["highlight_hover"]};
}}

QPushButton[accent="true"]:disabled {{
    background-color: {p["highlight_disabled_bg"]};
    color: {p["muted_text"]};
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    border: 1px solid {p["border"]};
}}

QPushButton[flat="true"]:hover {{
    background-color: {p["accent"]};
}}

QLineEdit, QTextEdit, QComboBox {{
    background-color: {p["background"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {p["highlight"]};
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {p["highlight"]};
}}

QListWidget {{
    background-color: {p["surface"]};
    border: 1px solid {p["border"]};
    border-radius: 10px;
    padding: 6px;
}}

QListWidget::item {{
    background-color: {p["accent"]};
    border-radius: 8px;
    padding: 10px;
    margin: 4px;
}}

QListWidget::item:selected {{
    background-color: {p["button_hover"]};
    border: 1px solid {p["highlight"]};
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: {p["background"]};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {p["accent"]};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p["highlight"]};
}}

QProgressBar {{
    background-color: {p["surface"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    text-align: center;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {p["highlight"]};
    border-radius: 7px;
}}

QStatusBar {{
    background-color: {p["surface"]};
    color: {p["muted_text"]};
    border-top: 1px solid {p["border"]};
}}

QToolTip {{
    background-color: {p["surface"]};
    color: {p["text"]};
    border: 1px solid {p["highlight"]};
    border-radius: 6px;
    padding: 4px 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {p["border"]};
    background: {p["background"]};
}}

QCheckBox::indicator:checked {{
    background: {p["highlight"]};
    border: 1px solid {p["highlight"]};
}}
"""


def apply_card_shadow(widget: QWidget) -> None:
    """Apply a subtle drop shadow to a card-style widget."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(24)
    effect.setOffset(0, 4)
    effect.setColor(QColor(0, 0, 0, 160))
    widget.setGraphicsEffect(effect)
