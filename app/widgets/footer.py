"""Persistent footer bar shown on every page."""

from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.design.qss import apply_style
from app.design.tokens import Color, FONT_FAMILY, FontSize

BSI_WEBSITE_URL = "https://www.boilerservicesandinspection.com"


class _LinkLabel(QLabel):
    """QLabel that opens a URL on left-click and changes color on hover via QSS."""

    def __init__(self, text: str, url: str, hover_color: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self._url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_style(
            self,
            f"color: {Color.TEXT_MUTED}; font-family: '{FONT_FAMILY}'; font-size: {FontSize.LABEL}px;",
            {":hover": f"color: {hover_color};"},
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            webbrowser.open(self._url)
        super().mousePressEvent(event)


class FooterBar(QWidget):
    """Persistent 28px footer bar with developer attribution, company site, and documentation link."""

    @staticmethod
    def _separator() -> QLabel:
        label = QLabel(" · ")
        apply_style(
            label,
            f"color: {Color.TEXT_MUTED}; font-family: '{FONT_FAMILY}'; font-size: {FontSize.LABEL}px;",
        )
        return label

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setObjectName("FooterBar")
        apply_style(self, f"background-color: {Color.PAGE_BG}; border-top: 1px solid {Color.BORDER_STRONG};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        dev_link = _LinkLabel(
            "Developed by Tyler Chambers",
            "https://github.com/tylerc515",
            Color.TEXT_PRIMARY,
        )
        # Company site sits between the two: it is attribution like the developer
        # link, so it shares that hover color and leaves Documentation as the only
        # accent-colored item in the bar.
        bsi_link = _LinkLabel(
            "Boiler Services and Inspection",
            BSI_WEBSITE_URL,
            Color.TEXT_PRIMARY,
        )
        docs_link = _LinkLabel(
            "Documentation",
            "https://github.com/tylerc515/dato-toolkit/wiki",
            Color.ACCENT_TEXT,
        )

        layout.addStretch(1)
        layout.addWidget(dev_link)
        layout.addWidget(self._separator())
        layout.addWidget(bsi_link)
        layout.addWidget(self._separator())
        layout.addWidget(docs_link)
        layout.addStretch(1)
