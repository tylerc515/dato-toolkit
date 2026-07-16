"""Left sidebar navigation - replaces the old top header nav bar."""
from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.design.icons import icon
from app.design.tokens import Color, FontSize, Radius, Spacing
from app.logo import get_pixmap

# Widened from 220 to 248 so the longest nav label ("Data converter")
# fits on one line at the larger FontSize.SECTION (16px). The button's
# sizeHint is 219px; with the sidebar's 12px content margins each side
# (24px total) that needs at least 243px, so 248 leaves a small cushion.
SIDEBAR_WIDTH = 248

# (item_id, label, icon name, section) - icon names confirmed to resolve
# under the ph. prefix; see docs/superpowers/plans/2026-07-01-visual-redesign.md
_TOOLS_ITEMS = [
    ("dashboard", "Dashboard", "house"),
    ("tracksheet", "Tracksheet", "table"),
    ("email", "Update email", "envelope-simple"),
    ("converter", "Data converter", "arrows-left-right"),
    ("history", "History", "clock-counter-clockwise"),
]
_SETTINGS_ITEM = ("settings", "Settings", "gear")

# External tool that opens in the browser, not an in-app page. It sits in the
# Tools list after "Data converter" but is NOT a nav target: clicking it opens
# the URL and never changes the active nav state.
ASME_CALCULATOR_URL = "https://tylerc515.github.io/asme-tube-calculator/"
ASME_CALCULATOR_ICON = "arrow-square-out"  # external-link glyph implies "opens elsewhere"


class _NavButton(QPushButton):
    def __init__(self, item_id: str, label: str, icon_name: str, parent: QWidget | None = None):
        super().__init__(f"  {label}", parent)
        self.item_id = item_id
        self._icon_name = icon_name
        self._apply_inactive_icon()
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                background: transparent;
                border: none;
                border-radius: {Radius.SIDEBAR_ITEM}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                color: {Color.TEXT_MUTED};
                font-size: {FontSize.SECTION}px;
            }}
            QPushButton:hover {{
                background-color: {Color.CARD_BG};
            }}
            QPushButton[active="true"] {{
                background-color: {Color.ACCENT_BG_TINT};
                color: {Color.ACCENT_TEXT};
                font-weight: 500;
            }}
            """
        )

    def _apply_inactive_icon(self) -> None:
        self.setIcon(icon(self._icon_name, color=Color.TEXT_MUTED))

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.setIcon(icon(self._icon_name, color=Color.ACCENT_TEXT if active else Color.TEXT_MUTED))
        self.style().unpolish(self)
        self.style().polish(self)


class Sidebar(QWidget):
    """Persistent left navigation. Emits nav_item_clicked(item_id) on click."""

    nav_item_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setStyleSheet(
            f"background-color: {Color.SIDEBAR_BG}; border-right: 1px solid {Color.BORDER};"
        )
        self._nav_buttons: dict[str, _NavButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.LG)
        layout.setSpacing(Spacing.XS)

        brand_row = QHBoxLayout()
        logo_label = QLabel()
        logo_label.setPixmap(get_pixmap(28, 28))
        brand_row.addWidget(logo_label)
        brand_row.addSpacing(Spacing.SM)
        name_label = QLabel("DATO Toolkit")
        name_label.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; font-size: {FontSize.SECTION}px; font-weight: 600;")
        brand_row.addWidget(name_label)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(Spacing.LG)

        layout.addWidget(self._section_label("Tools"))
        for item_id, label, icon_name in _TOOLS_ITEMS:
            layout.addWidget(self._add_nav_button(item_id, label, icon_name))
            if item_id == "converter":
                layout.addWidget(self._add_asme_link())

        layout.addStretch(1)

        # Settings sits alone at the bottom, set apart from the tools list by
        # a top border rather than a "SYSTEM" section label - with only one
        # item and no user/account row above it anymore, a section heading
        # here would be redundant with the separator + bottom position doing
        # that job visually.
        settings_row = QFrame()
        settings_row.setStyleSheet(f"border-top: 1px solid {Color.BORDER};")
        settings_layout = QVBoxLayout(settings_row)
        settings_layout.setContentsMargins(0, Spacing.SM, 0, 0)
        settings_layout.setSpacing(0)
        settings_id, settings_label, settings_icon_name = _SETTINGS_ITEM
        settings_layout.addWidget(self._add_nav_button(settings_id, settings_label, settings_icon_name))
        layout.addWidget(settings_row)

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setStyleSheet(
            f"color: {Color.TEXT_FAINT}; font-size: {FontSize.LABEL}px; font-weight: 600; "
            f"padding: {Spacing.SM}px {Spacing.MD}px 4px {Spacing.MD}px;"
        )
        return label

    def _add_nav_button(self, item_id: str, label: str, icon_name: str) -> _NavButton:
        btn = _NavButton(item_id, label, icon_name)
        btn.clicked.connect(lambda: self.nav_item_clicked.emit(item_id))
        self._nav_buttons[item_id] = btn
        return btn

    def _add_asme_link(self) -> _NavButton:
        """External link styled like a nav item but that opens the browser.
        Deliberately NOT registered in `_nav_buttons`: it never emits
        `nav_item_clicked` and never receives active state."""
        btn = _NavButton("asme_calculator", "ASME Calculator", ASME_CALCULATOR_ICON)
        btn.setToolTip("Opens in your browser")
        btn.clicked.connect(lambda: webbrowser.open(ASME_CALCULATOR_URL))
        self._asme_button = btn
        return btn

    def set_active(self, item_id: str) -> None:
        for current_id, btn in self._nav_buttons.items():
            btn.set_active(current_id == item_id)
