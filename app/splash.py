"""Animated splash screen shown while the application starts up."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen

from app.design.tokens import Color
from app.logo import get_pixmap

SPLASH_WIDTH = 480
SPLASH_HEIGHT = 280
SPLASH_CORNER_RADIUS = 16

APP_TITLE_TEXT = "DATO Toolkit"
APP_SUBTITLE_TEXT = "Data and Test Operations"

BAR_COLOR_START = Color.ACCENT
BAR_COLOR_END = Color.ACCENT_TEXT
BAR_MARGIN = 60
BAR_HEIGHT = 2

STATUS_MESSAGES = [
    "Initializing...",
    "Loading components...",
    "Checking for updates...",
    "Ready.",
]
STATUS_INTERVAL_MS = 300

LOADING_DURATION_MS = 1200
LOADING_TICK_MS = 16

# Minimum time the splash screen stays visible before the main window appears.
SPLASH_MIN_DURATION_MS = 1500


class SplashScreen(QSplashScreen):
    """A frameless, rounded splash screen with a logo, title, and loading bar."""

    def __init__(self):
        pixmap = QPixmap(SPLASH_WIDTH, SPLASH_HEIGHT)
        pixmap.fill(Qt.GlobalColor.transparent)
        super().__init__(
            pixmap,
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._progress = 0.0
        self._status_index = 0

        self._center_on_screen()

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(LOADING_TICK_MS)
        self._progress_timer.timeout.connect(self._advance_progress)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(STATUS_INTERVAL_MS)
        self._status_timer.timeout.connect(self._advance_status)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.geometry()
        x = geometry.x() + (geometry.width() - SPLASH_WIDTH) // 2
        y = geometry.y() + (geometry.height() - SPLASH_HEIGHT) // 2
        self.move(x, y)

    def start(self) -> None:
        """Begin the loading bar animation and status text cycle."""
        self._progress_timer.start()
        self._status_timer.start()

    def _advance_progress(self) -> None:
        step = LOADING_TICK_MS / LOADING_DURATION_MS
        self._progress = min(1.0, self._progress + step)
        if self._progress >= 1.0:
            self._progress_timer.stop()
        self.repaint()

    def _advance_status(self) -> None:
        if self._status_index < len(STATUS_MESSAGES) - 1:
            self._status_index += 1
        else:
            self._status_timer.stop()
        self.repaint()

    def drawContents(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Color.PAGE_BG))
        painter.drawRoundedRect(rect, SPLASH_CORNER_RADIUS, SPLASH_CORNER_RADIUS)

        width = self.width()
        height = self.height()
        logo_area_height = int(height * 0.6)

        logo = get_pixmap(200, 116)
        logo_x = (width - logo.width()) // 2
        logo_y = (logo_area_height - logo.height()) // 2
        painter.drawPixmap(logo_x, logo_y, logo)

        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.setPen(QColor(Color.TEXT_PRIMARY))
        title_rect = QRectF(0, logo_area_height, width, 30)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, APP_TITLE_TEXT)

        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor(Color.TEXT_MUTED))
        subtitle_rect = QRectF(0, logo_area_height + 28, width, 20)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, APP_SUBTITLE_TEXT)

        bar_y = logo_area_height + 58
        bar_width = width - 2 * BAR_MARGIN

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Color.BORDER))
        painter.drawRect(BAR_MARGIN, bar_y, bar_width, BAR_HEIGHT)

        filled_width = int(bar_width * self._progress)
        if filled_width > 0:
            gradient = QLinearGradient(BAR_MARGIN, 0, BAR_MARGIN + bar_width, 0)
            gradient.setColorAt(0.0, QColor(BAR_COLOR_START))
            gradient.setColorAt(1.0, QColor(BAR_COLOR_END))
            painter.setBrush(QBrush(gradient))
            painter.drawRect(BAR_MARGIN, bar_y, filled_width, BAR_HEIGHT)

        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor(Color.TEXT_MUTED))
        status_rect = QRectF(0, bar_y + 12, width, 24)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, STATUS_MESSAGES[self._status_index])
