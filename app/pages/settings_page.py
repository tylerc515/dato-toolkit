"""Settings page: appearance preferences and keyboard shortcuts reference.

Theme-selector decision (Task 23, Phase 8): this redesign ships ONE theme
(dark, TRACE-inspired) - there is no light-mode QSS in this pass. The old
Dark/Light QComboBox is kept in place but disabled, with a note explaining
that light theme support is coming later, rather than being ripped out.
This was the lower-churn option: the combo is a self-contained control
(get_theme()/set_theme() have no other call sites in the app besides this
page and the one-time read in main.py at startup), so no other file needed
to change to make this decision.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.design.tokens import Color, Spacing
from app.settings import get_theme
from app.styles import THEME_DARK, THEME_LIGHT
from app.widgets.components import Card, SecondaryButton

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Settings"
BACK_TEXT = "← Back"
APPEARANCE_TITLE = "Appearance"
THEME_LABEL_TEXT = "Theme"
THEME_COMING_SOON_TEXT = "Light theme coming in a future update."
SHORTCUTS_TITLE = "Keyboard Shortcuts"
STATUS_HINT = "Tip: Adjust application appearance settings here."

_THEME_DISPLAY_NAMES = {
    THEME_DARK: "Dark",
    THEME_LIGHT: "Light",
}

KEYBOARD_SHORTCUTS = [
    ("Ctrl+N", "Start a new tracker"),
    ("Ctrl+D", "Go to the dashboard"),
    ("Ctrl+H", "View export history"),
    ("Ctrl+B", "Open batch generation"),
    ("Ctrl+,", "Open settings"),
    ("Ctrl+T", "Open Data Converter"),
    ("Ctrl+→ / Ctrl+Enter", "Continue to the next step / Generate"),
    ("Ctrl+←", "Go back a step"),
    ("F1", "Show or hide help for the current step"),
]


class SettingsPage(QWidget):
    """Settings page: theme preference (view-only for now) and keyboard shortcuts."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        outer.setSpacing(Spacing.LG)

        header_row = QHBoxLayout()
        self.back_button = SecondaryButton(BACK_TEXT)
        self.back_button.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.back_button)
        header_row.addSpacing(12)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        outer.addLayout(header_row)

        outer.addWidget(self._build_appearance_card())
        outer.addWidget(self._build_shortcuts_card())
        outer.addStretch(1)

    def _build_appearance_card(self) -> Card:
        card = Card()
        card_layout = card.layout()

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
        # Only one theme ships in this release (dark) - the selector stays
        # visible so the option is discoverable, but disabled so it can't
        # be changed to an unsupported light theme. See module docstring.
        # The global QSS (app/styles.py) has no QComboBox:disabled rule, so
        # the muted text color is applied here directly (still token-driven,
        # not a hardcoded value) to make the disabled state visually clear.
        self.theme_combo.setEnabled(False)
        self.theme_combo.setToolTip(THEME_COMING_SOON_TEXT)
        self.theme_combo.setStyleSheet(f"color: {Color.TEXT_MUTED};")
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch(1)
        card_layout.addLayout(theme_row)

        note = QLabel(THEME_COMING_SOON_TEXT)
        note.setProperty("role", "muted")
        note.setWordWrap(True)
        card_layout.addWidget(note)

        return card

    def _build_shortcuts_card(self) -> Card:
        card = Card()
        card_layout = card.layout()

        heading = QLabel(SHORTCUTS_TITLE)
        heading.setProperty("role", "heading")
        card_layout.addWidget(heading)

        shortcuts_grid = QGridLayout()
        shortcuts_grid.setColumnStretch(1, 1)
        shortcuts_grid.setHorizontalSpacing(Spacing.MD)
        shortcuts_grid.setVerticalSpacing(Spacing.XS)
        for row, (keys, description) in enumerate(KEYBOARD_SHORTCUTS):
            keys_label = QLabel(keys)
            keys_label.setTextFormat(Qt.TextFormat.PlainText)
            keys_label.setStyleSheet("font-weight: 600;")
            shortcuts_grid.addWidget(keys_label, row, 0)
            desc_label = QLabel(description)
            desc_label.setTextFormat(Qt.TextFormat.PlainText)
            shortcuts_grid.addWidget(desc_label, row, 1)
        card_layout.addLayout(shortcuts_grid)

        return card
