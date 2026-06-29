"""Persistent footer bar shown on every page."""

from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class _LinkLabel(QLabel):
    """QLabel that opens a URL on left-click and changes color on hover via QSS."""

    def __init__(self, text: str, url: str, hover_color: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self._url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QLabel { color: #6e7681; font-family: 'Segoe UI'; font-size: 9pt; }"
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
            "#FooterBar { background-color: #0d1117; border-top: 1px solid #2f3650; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        dev_link = _LinkLabel(
            "Developed by Tyler Chambers",
            "https://github.com/tylerc515",
            "#eaeaea",
        )
        separator = QLabel(" · ")
        separator.setStyleSheet(
            "QLabel { color: #6e7681; font-family: 'Segoe UI'; font-size: 9pt; }"
        )
        docs_link = _LinkLabel(
            "Documentation",
            "https://github.com/tylerc515/dato-toolkit/wiki",
            "#2f80ed",
        )

        layout.addStretch(1)
        layout.addWidget(dev_link)
        layout.addWidget(separator)
        layout.addWidget(docs_link)
        layout.addStretch(1)
