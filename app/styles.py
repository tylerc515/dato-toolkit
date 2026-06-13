"""Dark theme styling for TRACE Tracker Builder."""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget

COLOR_BACKGROUND = "#1a1a2e"
COLOR_SURFACE = "#16213e"
COLOR_ACCENT = "#0f3460"
COLOR_HIGHLIGHT = "#e94560"
COLOR_TEXT = "#eaeaea"
COLOR_MUTED_TEXT = "#9aa0b4"
COLOR_BORDER = "#2c3759"
COLOR_SUCCESS = "#3ddc97"
COLOR_WARNING = "#f7b731"
COLOR_ERROR = "#e94560"

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Calibri", sans-serif;
    color: {COLOR_TEXT};
}}

QMainWindow, QWidget {{
    background-color: {COLOR_BACKGROUND};
}}

QLabel {{
    background: transparent;
}}

QLabel[role="muted"] {{
    color: {COLOR_MUTED_TEXT};
}}

QLabel[role="heading"] {{
    font-size: 18px;
    font-weight: 600;
}}

QFrame[card="true"] {{
    background-color: {COLOR_SURFACE};
    border-radius: 12px;
    border: 1px solid {COLOR_BORDER};
}}

QPushButton {{
    background-color: {COLOR_ACCENT};
    color: {COLOR_TEXT};
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: #16498a;
}}

QPushButton:pressed {{
    background-color: #0a2745;
}}

QPushButton:disabled {{
    background-color: #2a3050;
    color: {COLOR_MUTED_TEXT};
}}

QPushButton[accent="true"] {{
    background-color: {COLOR_HIGHLIGHT};
    font-weight: 600;
    font-size: 15px;
    padding: 12px 24px;
    border-radius: 10px;
}}

QPushButton[accent="true"]:hover {{
    background-color: #ff5c75;
}}

QPushButton[accent="true"]:disabled {{
    background-color: #5b3641;
    color: {COLOR_MUTED_TEXT};
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    border: 1px solid {COLOR_BORDER};
}}

QPushButton[flat="true"]:hover {{
    background-color: {COLOR_ACCENT};
}}

QLineEdit, QTextEdit, QComboBox {{
    background-color: {COLOR_BACKGROUND};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {COLOR_HIGHLIGHT};
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {COLOR_HIGHLIGHT};
}}

QListWidget {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 6px;
}}

QListWidget::item {{
    background-color: {COLOR_ACCENT};
    border-radius: 8px;
    padding: 10px;
    margin: 4px;
}}

QListWidget::item:selected {{
    background-color: #16498a;
    border: 1px solid {COLOR_HIGHLIGHT};
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: {COLOR_BACKGROUND};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_ACCENT};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_HIGHLIGHT};
}}

QProgressBar {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    text-align: center;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {COLOR_HIGHLIGHT};
    border-radius: 7px;
}}

QStatusBar {{
    background-color: {COLOR_SURFACE};
    color: {COLOR_MUTED_TEXT};
    border-top: 1px solid {COLOR_BORDER};
}}

QToolTip {{
    background-color: {COLOR_SURFACE};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_HIGHLIGHT};
    border-radius: 6px;
    padding: 4px 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER};
    background: {COLOR_BACKGROUND};
}}

QCheckBox::indicator:checked {{
    background: {COLOR_HIGHLIGHT};
    border: 1px solid {COLOR_HIGHLIGHT};
}}
"""


def apply_card_shadow(widget: QWidget) -> None:
    """Apply a subtle drop shadow to a card-style widget."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(24)
    effect.setOffset(0, 4)
    effect.setColor(QColor(0, 0, 0, 160))
    widget.setGraphicsEffect(effect)
