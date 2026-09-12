"""Frameless dialogs with the app's own chrome.

The main window is frameless with custom chrome, so native-framed
QDialog / QMessageBox windows looked foreign next to it, and a frameless
QDialog cannot draw a QSS border on itself (Qt only honours background
properties on QDialog). Every in-app dialog therefore derives from
:class:`AppDialog`: a translucent frameless window whose only child is a
``QFrame#DialogFrame``. That frame carries the visible 1px
``Color.DIALOG_BORDER`` border and rounded corners (rule in app.styles),
so the dialog always separates cleanly from the page behind it.

:class:`MessageDialog` replaces the QMessageBox.warning / critical /
question calls that used to be scattered across the pages.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.design.qss import apply_style
from app.design.tooltip import set_tooltip
from app.design.tokens import Color, FontSize, Spacing

DIALOG_FRAME_OBJECT_NAME = "DialogFrame"
CLOSE_BUTTON_SIZE = 28
MESSAGE_MIN_WIDTH = 420
MESSAGE_MAX_WIDTH = 560


class AppDialog(QDialog):
    """Frameless modal dialog: bordered rounded frame, title row, body, button row.

    Subclasses add content to ``self.body`` and call :meth:`add_button`
    for the right-aligned action row (add the primary action last).
    """

    def __init__(self, parent: QWidget | None = None, title: str = ""):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        # Let the rounded frame corners show the page behind them. The global
        # `QWidget { background }` rule would otherwise paint the corners.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        apply_style(self, "background: transparent;")
        self.setModal(True)
        self.setWindowTitle(title)
        self._drag_offset: QPoint | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame()
        self.frame.setObjectName(DIALOG_FRAME_OBJECT_NAME)
        root.addWidget(self.frame)

        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(Spacing.XL, Spacing.LG, Spacing.XL, Spacing.XL)
        self.frame_layout.setSpacing(Spacing.MD)

        self.title_row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        apply_style(self.title_label, f"font-size: {FontSize.DIALOG_TITLE}px; font-weight: 600;")
        self.title_row.addWidget(self.title_label, 1)
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(CLOSE_BUTTON_SIZE, CLOSE_BUTTON_SIZE)
        set_tooltip(self.close_button, "Close")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_style(
            self.close_button,
            f"background: transparent; border: none; color: {Color.TEXT_MUTED}; "
            f"font-size: {FontSize.PAGE_TITLE}px; padding: 0;",
            {":hover": f"color: {Color.TEXT_PRIMARY}; background-color: {Color.BORDER_STRONG};"},
        )
        self.close_button.clicked.connect(self.reject)
        self.title_row.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignTop)
        self.frame_layout.addLayout(self.title_row)

        self.body = QVBoxLayout()
        self.body.setSpacing(Spacing.MD)
        self.frame_layout.addLayout(self.body, 1)

        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(Spacing.SM)
        self.button_row.addStretch(1)
        self.frame_layout.addLayout(self.button_row)

    def add_button(self, text: str, *, primary: bool = False) -> QPushButton:
        """Append a button to the action row. Primary buttons use the accent style."""
        button = QPushButton(text)
        button.setProperty("accent" if primary else "flat", "true")
        self.button_row.addWidget(button)
        if primary:
            button.setDefault(True)
        return button

    # Dragging by the title row, matching the main window's custom title bar.
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._in_title_row(event.position().toPoint()):
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def _in_title_row(self, pos: QPoint) -> bool:
        return self.title_row.geometry().contains(self.frame.mapFrom(self, pos))


class MessageDialog(AppDialog):
    """Modal message with a tone-colored title and one or more action buttons.

    ``buttons`` is an ordered list of ``(label, accepts)`` pairs, left to
    right; the last one is the primary action. Use the class helpers for
    the common shapes.
    """

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        text: str,
        buttons: list[tuple[str, bool]] | None = None,
        tone: str | None = None,
    ):
        super().__init__(parent, title)
        if tone is not None:
            self.title_label.setProperty("tone", tone)
        self.setMinimumWidth(MESSAGE_MIN_WIDTH)
        self.setMaximumWidth(MESSAGE_MAX_WIDTH)

        self.message_label = QLabel(text)
        # Messages often embed file names or error text - never let Qt sniff
        # a stray "<" in them as HTML.
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        self.message_label.setWordWrap(True)
        self.message_label.setProperty("role", "label")
        self.body.addWidget(self.message_label)

        buttons = buttons or [("OK", True)]
        for index, (label, accepts) in enumerate(buttons):
            button = self.add_button(label, primary=index == len(buttons) - 1)
            button.clicked.connect(self.accept if accepts else self.reject)

    @classmethod
    def warning(cls, parent: QWidget | None, title: str, text: str) -> None:
        cls(parent, title, text, tone="warning").exec()

    @classmethod
    def critical(cls, parent: QWidget | None, title: str, text: str) -> None:
        cls(parent, title, text, tone="danger").exec()

    @classmethod
    def question(
        cls,
        parent: QWidget | None,
        title: str,
        text: str,
        accept_text: str = "Yes",
        reject_text: str = "No",
        tone: str | None = None,
    ) -> bool:
        """Two-button confirmation. True when the accepting button was chosen."""
        dialog = cls(parent, title, text, [(reject_text, False), (accept_text, True)], tone=tone)
        return dialog.exec() == QDialog.DialogCode.Accepted
