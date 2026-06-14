"""Settings page: appearance preferences (theme)."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.settings import get_theme, set_theme
from app.styles import THEME_DARK, THEME_LIGHT, apply_card_shadow, build_stylesheet, set_active_theme

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Settings"
BACK_TEXT = "← Back"
APPEARANCE_TITLE = "Appearance"
THEME_LABEL_TEXT = "Theme"
THEME_RESTART_HINT = (
    "Some elements (the title bar, step indicator, and splash screen) will pick up "
    "the new theme's colors after you restart the app."
)
STATUS_HINT = "Tip: Adjust application appearance settings here."

_THEME_DISPLAY_NAMES = {
    THEME_DARK: "Dark",
    THEME_LIGHT: "Light",
}


class SettingsPage(QWidget):
    """Settings page: theme selection and other preferences."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        header_row = QHBoxLayout()
        self.back_button = QPushButton(BACK_TEXT)
        self.back_button.setProperty("flat", "true")
        self.back_button.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.back_button)
        header_row.addSpacing(12)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        outer.addLayout(header_row)

        card = QFrame()
        card.setProperty("card", "true")
        apply_card_shadow(card)
        card_layout = QVBoxLayout(card)

        heading = QLabel(APPEARANCE_TITLE)
        heading.setProperty("role", "heading")
        card_layout.addWidget(heading)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel(THEME_LABEL_TEXT))

        self.theme_combo = QComboBox()
        for theme_name in (THEME_DARK, THEME_LIGHT):
            self.theme_combo.addItem(_THEME_DISPLAY_NAMES[theme_name], theme_name)
        index = self.theme_combo.findData(get_theme())
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        card_layout.addLayout(theme_row)

        hint = QLabel(THEME_RESTART_HINT)
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        outer.addWidget(card)
        outer.addStretch(1)

    def _on_theme_changed(self, index: int) -> None:
        theme = self.theme_combo.itemData(index)
        if not theme:
            return
        set_theme(theme)
        set_active_theme(theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(theme))
