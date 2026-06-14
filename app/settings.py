"""Persisted application settings (theme, etc.) via QSettings."""

from __future__ import annotations

from PyQt6.QtCore import QSettings

from app.project import APP_DIR_NAME
from app.styles import DEFAULT_THEME, THEME_NAMES

THEME_SETTINGS_KEY = "theme"


def get_theme() -> str:
    """Return the persisted theme name, falling back to the default."""
    settings = QSettings(APP_DIR_NAME, APP_DIR_NAME)
    theme = settings.value(THEME_SETTINGS_KEY)
    return theme if theme in THEME_NAMES else DEFAULT_THEME


def set_theme(theme: str) -> None:
    """Persist the given theme name."""
    settings = QSettings(APP_DIR_NAME, APP_DIR_NAME)
    settings.setValue(THEME_SETTINGS_KEY, theme)
