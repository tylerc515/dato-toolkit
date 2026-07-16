"""Persistent footer bar shown on every page."""

from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.design.tokens import Color, FONT_FAMILY, FontSize


class _LinkLabel(QLabel):
    """QLabel that opens a URL on left-click and changes color on hover via QSS."""

    def __init__(self, text: str, url: str, hover_color: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self._url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QLabel {{ color: {Color.TEXT_MUTED}; font-family: '{FONT_FAMILY}'; font-size: {FontSize.LABEL}px; }}"
            f"QLabel:hover {{ color: {hover_color}; }}"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            webbrowser.open(self._url)
        super().mousePressEvent(event)


class FooterBar(QWidget):
    """Persistent 28px footer bar with developer attribution and documentation link."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setObjectName("FooterBar")
        self.setStyleSheet(
            f"#FooterBar {{ background-color: {Color.PAGE_BG}; border-top: 1px solid {Color.BORDER_STRONG}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        dev_link = _LinkLabel(
            "Developed by Tyler Chambers",
            "https://github.com/tylerc515",
            Color.TEXT_PRIMARY,
        )
        separator = QLabel(" · ")
        separator.setStyleSheet(
            f"QLabel {{ color: {Color.TEXT_MUTED}; font-family: '{FONT_FAMILY}'; font-size: {FontSize.LABEL}px; }}"
        )
        docs_link = _LinkLabel(
            "Documentation",
            "https://github.com/tylerc515/dato-toolkit/wiki",
            Color.ACCENT_TEXT,
        )

        layout.addStretch(1)
        layout.addWidget(dev_link)
        layout.addWidget(separator)
        layout.addWidget(docs_link)
        layout.addStretch(1)
