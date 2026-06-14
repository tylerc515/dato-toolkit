"""Reusable UI widgets shared across pages: step indicator, help panel, onboarding."""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.logo import get_pixmap
from app.styles import color

HELP_PANEL_WIDTH = 320
ONBOARDING_TITLE = "Welcome to TRACE Tracker Builder"
ONBOARDING_STEPS = [
    (
        "1. Import Files",
        "Drag and drop your TRACE UT export CSV files, or click to browse. "
        "Each file becomes one section of your tracker.",
    ),
    (
        "2. Arrange Sections",
        "Drag sections into the order you want them to appear, rename them if "
        "needed, and review the auto-generated tracker title.",
    ),
    (
        "3. Generate Tracker",
        "Choose where to save the output, then click Generate Tracker to "
        "create a formatted Excel file (and optionally a PDF).",
    ),
]


class StepIndicator(QWidget):
    """Horizontal stepper showing the three wizard steps."""

    step_clicked = pyqtSignal(int)

    def __init__(self, steps: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self._labels = steps
        self._buttons: list[QPushButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for index, label in enumerate(steps):
            if index > 0:
                connector = QFrame()
                connector.setFixedHeight(2)
                connector.setStyleSheet(f"background-color: {color('border')};")
                layout.addWidget(connector, 1)

            button = QPushButton(f"{index + 1}. {label}")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(f"Go to step {index + 1}: {label}")
            button.clicked.connect(lambda _checked, i=index: self.step_clicked.emit(i))
            self._buttons.append(button)
            layout.addWidget(button)

        self.set_current_step(0)

    def set_current_step(self, current_index: int, completed: set[int] | None = None) -> None:
        completed = completed or set()
        for index, button in enumerate(self._buttons):
            if index == current_index:
                button.setText(f"{index + 1}. {self._labels[index]}")
                button.setStyleSheet(
                    f"background-color: {color('highlight')}; color: {color('text')}; "
                    f"font-weight: 600; border-radius: 8px; padding: 8px 16px;"
                )
                button.setEnabled(index < current_index or index in completed or index == current_index)
            elif index in completed or index < current_index:
                button.setText(f"✓ {self._labels[index]}")
                button.setStyleSheet(
                    f"background-color: {color('surface')}; color: {color('success')}; "
                    f"border: 1px solid {color('success')}; border-radius: 8px; padding: 8px 16px;"
                )
                button.setEnabled(True)
            else:
                button.setText(f"{index + 1}. {self._labels[index]}")
                button.setStyleSheet(
                    f"background-color: {color('surface')}; color: {color('muted_text')}; "
                    f"border: 1px solid {color('border')}; border-radius: 8px; padding: 8px 16px;"
                )
                button.setEnabled(False)


class HelpPanel(QFrame):
    """Collapsible help panel that slides in/out from the right edge of a page."""

    def __init__(self, title: str, body_html: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self._expanded = False
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)

        heading = QLabel(title)
        heading.setProperty("role", "heading")
        heading.setWordWrap(True)
        layout.addWidget(heading)

        body = QLabel(body_html)
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(body)
        layout.addStretch(1)

        self._animation = QPropertyAnimation(self, b"maximumWidth")
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def toggle(self) -> None:
        self._expanded = not self._expanded
        target = HELP_PANEL_WIDTH if self._expanded else 0
        self._animation.stop()
        self._animation.setStartValue(self.maximumWidth())
        self._animation.setEndValue(target)
        self._animation.start()


class OnboardingDialog(QDialog):
    """First-launch walkthrough of the three wizard steps."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(ONBOARDING_TITLE)
        self.setMinimumWidth(480)
        self.setModal(True)

        layout = QVBoxLayout(self)

        logo_label = QLabel()
        logo_label.setPixmap(get_pixmap(240, 140))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)
        layout.addSpacing(16)

        heading = QLabel(ONBOARDING_TITLE)
        heading.setProperty("role", "heading")
        layout.addWidget(heading)

        intro = QLabel("Build a TRACE inspection tracker in three quick steps:")
        intro.setProperty("role", "muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for title, description in ONBOARDING_STEPS:
            step_label = QLabel(f"<b>{title}</b><br>{description}")
            step_label.setWordWrap(True)
            layout.addWidget(step_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        get_started = QPushButton("Get Started")
        get_started.setProperty("accent", "true")
        get_started.clicked.connect(self.accept)
        button_row.addWidget(get_started)
        layout.addLayout(button_row)
