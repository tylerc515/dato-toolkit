"""Main application window: header bar, step navigation, and page wiring."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QByteArray, QEvent, QPoint, QRect, QSettings, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.logo import get_icon, get_pixmap
from app.pages.generate_page import GeneratePage
from app.pages.generate_page import STATUS_HINT as GENERATE_STATUS_HINT
from app.pages.import_page import ImportPage
from app.pages.import_page import STATUS_HINT as IMPORT_STATUS_HINT
from app.pages.reorder_page import ReorderPage
from app.pages.reorder_page import STATUS_HINT as REORDER_STATUS_HINT
from app.parser import TraceFileData
from app.project import APP_DIR_NAME, ProjectConfig, ProjectError, get_app_data_dir, load_project
from app.styles import COLOR_SUCCESS, COLOR_SURFACE, COLOR_TEXT, COLOR_WARNING
from app.updater import GITHUB_RELEASES_PAGE_URL, UpdateCheckResult, UpdateCheckWorker
from app.widgets import OnboardingDialog, StepIndicator

# --- UI text -------------------------------------------------------------

APP_NAME = "TRACE Tracker Builder"
WINDOW_MIN_WIDTH = 900
WINDOW_MIN_HEIGHT = 600
STEP_LABELS = ["Import Files", "Arrange Sections", "Generate Tracker"]
ONBOARDING_FLAG_FILENAME = "onboarding_complete"

UPDATE_BANNER_TEXT = "A new version ({version}) is available."
DOWNLOAD_UPDATE_TEXT = "Download Update"
DISMISS_TEXT = "Dismiss"

INDICATOR_COLOR_UP_TO_DATE = COLOR_SUCCESS
INDICATOR_COLOR_UPDATE_AVAILABLE = COLOR_WARNING
INDICATOR_COLOR_UNKNOWN = "#5a6178"

STATUS_HINTS = [IMPORT_STATUS_HINT, REORDER_STATUS_HINT, GENERATE_STATUS_HINT]

# --- Window chrome ---------------------------------------------------------

GEOMETRY_SETTINGS_KEY = "geometry"
DEFAULT_WINDOW_SIZE = (1100, 750)
RESIZE_MARGIN = 8
WINDOW_BUTTON_SIZE = 32
WINDOW_BUTTON_HOVER = "#2a2a4a"
WINDOW_CLOSE_HOVER = "#e94560"
WINDOW_BORDER_COLOR = "#2f3650"

_CURSOR_BY_DIRECTION = {
    "left": Qt.CursorShape.SizeHorCursor,
    "right": Qt.CursorShape.SizeHorCursor,
    "top": Qt.CursorShape.SizeVerCursor,
    "bottom": Qt.CursorShape.SizeVerCursor,
    "top-left": Qt.CursorShape.SizeFDiagCursor,
    "bottom-right": Qt.CursorShape.SizeFDiagCursor,
    "top-right": Qt.CursorShape.SizeBDiagCursor,
    "bottom-left": Qt.CursorShape.SizeBDiagCursor,
}

logger = logging.getLogger(__name__)


class _DragHeader(QFrame):
    """Header bar that doubles as the custom title bar's drag handle."""

    def __init__(self, window: "MainWindow", parent: QWidget | None = None):
        super().__init__(parent)
        self._window = window
        self._drag_offset: Optional[QPoint] = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            if self._window.isMaximized():
                ratio = event.position().x() / max(self.width(), 1)
                self._window._toggle_maximize_restore()
                self._drag_offset = QPoint(int(self._window.width() * ratio), self._drag_offset.y())
            self._window.move(global_pos - self._drag_offset)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._window._toggle_maximize_restore()
        super().mouseDoubleClickEvent(event)


class _UpdateIndicator(QLabel):
    """A small colored dot showing update-check status."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self.set_color(INDICATOR_COLOR_UNKNOWN)

    def set_color(self, color: str) -> None:
        self.setStyleSheet(f"background-color: {color}; border-radius: 7px;")


class MainWindow(QMainWindow):
    """The application's main window and wizard navigation."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(get_icon())
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setMouseTracking(True)

        self._completed_steps: set[int] = set()
        self._update_worker: Optional[UpdateCheckWorker] = None
        self._resize_direction: Optional[str] = None
        self._resize_start_geometry: Optional[QRect] = None
        self._resize_start_pos: Optional[QPoint] = None

        self._build_ui()
        QApplication.instance().installEventFilter(self)
        self._restore_geometry()
        self._run_update_check()
        self._maybe_show_onboarding()

    # --- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        central = QFrame()
        central.setObjectName("AppFrame")
        central.setStyleSheet(f"QFrame#AppFrame {{ border: 1px solid {WINDOW_BORDER_COLOR}; }}")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self.update_banner = self._build_update_banner()
        layout.addWidget(self.update_banner)

        step_container = QWidget()
        step_layout = QHBoxLayout(step_container)
        step_layout.setContentsMargins(16, 12, 16, 12)
        self.step_indicator = StepIndicator(STEP_LABELS)
        self.step_indicator.step_clicked.connect(self._go_to_step)
        step_layout.addWidget(self.step_indicator)
        layout.addWidget(step_container)

        self.stack = QStackedWidget()
        self.import_page = ImportPage()
        self.reorder_page = ReorderPage()
        self.generate_page = GeneratePage()
        self.stack.addWidget(self.import_page)
        self.stack.addWidget(self.reorder_page)
        self.stack.addWidget(self.generate_page)
        layout.addWidget(self.stack, 1)

        self.import_page.files_ready.connect(self._on_files_ready)
        self.import_page.project_load_requested.connect(self._on_project_load_requested)
        self.reorder_page.back_requested.connect(lambda: self._go_to_step(0))
        self.reorder_page.continue_requested.connect(self._on_reorder_continue)
        self.generate_page.back_requested.connect(lambda: self._go_to_step(1))
        self.generate_page.new_project_requested.connect(self._on_new_project)

        self.setCentralWidget(central)

        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background: transparent;")
        self.size_grip.raise_()

        self.status_bar = self.statusBar()
        self.stack.currentChanged.connect(self._update_status_hint)
        self._update_status_hint(0)

    def _build_header(self) -> QFrame:
        header = _DragHeader(self)
        header.setStyleSheet(f"background-color: {COLOR_SURFACE};")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 10, 16, 10)

        logo_label = QLabel()
        logo_label.setPixmap(get_pixmap(160, 93))
        logo_label.setMinimumWidth(160)
        layout.addWidget(logo_label)

        layout.addSpacing(12)

        name_label = QLabel(APP_NAME)
        name_label.setProperty("role", "heading")
        layout.addWidget(name_label)

        version_label = QLabel(f"v{__version__}")
        version_label.setProperty("role", "muted")
        layout.addWidget(version_label)

        layout.addStretch(1)

        self.update_indicator = _UpdateIndicator()
        self.update_indicator.setToolTip("Checking for updates…")
        layout.addWidget(self.update_indicator)

        layout.addSpacing(12)

        self.minimize_button = self._make_window_button("−", WINDOW_BUTTON_HOVER)
        self.minimize_button.setToolTip("Minimize")
        self.minimize_button.clicked.connect(self.showMinimized)
        layout.addWidget(self.minimize_button)

        self.maximize_button = self._make_window_button("□", WINDOW_BUTTON_HOVER)
        self.maximize_button.setToolTip("Maximize")
        self.maximize_button.clicked.connect(self._toggle_maximize_restore)
        layout.addWidget(self.maximize_button)

        self.close_button = self._make_window_button("×", WINDOW_CLOSE_HOVER)
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

        return header

    def _make_window_button(self, text: str, hover_color: str) -> QPushButton:
        button = QPushButton(text)
        button.setFixedSize(WINDOW_BUTTON_SIZE, WINDOW_BUTTON_SIZE)
        button.setStyleSheet(
            "QPushButton {"
            "background-color: transparent;"
            "border: none;"
            "border-radius: 6px;"
            "padding: 0px;"
            "font-size: 14px;"
            f"color: {COLOR_TEXT};"
            "}"
            "QPushButton:hover {"
            f"background-color: {hover_color};"
            "}"
        )
        return button

    def _build_update_banner(self) -> QFrame:
        banner = QFrame()
        banner.setStyleSheet(f"background-color: {COLOR_WARNING}; color: #1a1a2e;")
        banner.setVisible(False)
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 8, 16, 8)

        self.update_banner_label = QLabel("")
        self.update_banner_label.setStyleSheet("color: #1a1a2e;")
        layout.addWidget(self.update_banner_label, 1)

        download_button = QPushButton(DOWNLOAD_UPDATE_TEXT)
        download_button.clicked.connect(self._open_releases_page)
        layout.addWidget(download_button)

        dismiss_button = QPushButton(DISMISS_TEXT)
        dismiss_button.setProperty("flat", "true")
        dismiss_button.clicked.connect(lambda: banner.setVisible(False))
        layout.addWidget(dismiss_button)

        return banner

    # --- Onboarding --------------------------------------------------------

    def _maybe_show_onboarding(self) -> None:
        flag_path = get_app_data_dir() / ONBOARDING_FLAG_FILENAME
        if flag_path.exists():
            return
        dialog = OnboardingDialog(self)
        dialog.exec()
        try:
            flag_path.write_text("1", encoding="utf-8")
        except OSError:
            logger.warning("Could not write onboarding flag file at %s", flag_path)

    # --- Update checking -----------------------------------------------------

    def _run_update_check(self) -> None:
        self._update_worker = UpdateCheckWorker(__version__, self)
        self._update_worker.check_finished.connect(self._on_update_check_finished)
        self._update_worker.start()

    def _on_update_check_finished(self, result: UpdateCheckResult) -> None:
        if result.error:
            self.update_indicator.set_color(INDICATOR_COLOR_UNKNOWN)
            self.update_indicator.setToolTip("Could not check for updates")
            return

        if result.update_available:
            self.update_indicator.set_color(INDICATOR_COLOR_UPDATE_AVAILABLE)
            self.update_indicator.setToolTip(f"Update available: v{result.latest_version}")
            self.update_banner_label.setText(UPDATE_BANNER_TEXT.format(version=f"v{result.latest_version}"))
            self.update_banner.setVisible(True)
        else:
            self.update_indicator.set_color(INDICATOR_COLOR_UP_TO_DATE)
            self.update_indicator.setToolTip("You're using the latest version")

    def _open_releases_page(self) -> None:
        QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_PAGE_URL))

    # --- Step navigation -------------------------------------------------

    def _go_to_step(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.step_indicator.set_current_step(index, self._completed_steps)

    def _update_status_hint(self, index: int) -> None:
        if 0 <= index < len(STATUS_HINTS):
            self.status_bar.showMessage(STATUS_HINTS[index])

    def _on_files_ready(self, files: list[TraceFileData]) -> None:
        self.reorder_page.set_files(files)
        self._completed_steps.add(0)
        self._go_to_step(1)

    def _on_project_load_requested(self, project_path: Path) -> None:
        try:
            config = load_project(project_path)
        except ProjectError:
            logger.exception("Could not load project from %s", project_path)
            return
        self.reorder_page.load_project(config)
        self._completed_steps.add(0)
        self._go_to_step(1)

    def _on_reorder_continue(self, config: ProjectConfig) -> None:
        self.generate_page.set_project(config)
        self._completed_steps.add(1)
        self._go_to_step(2)

    def _on_new_project(self) -> None:
        self.import_page.clear_all()
        self._completed_steps.clear()
        self._go_to_step(0)

    # --- Window chrome -----------------------------------------------------

    def _toggle_maximize_restore(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("□")
            self.maximize_button.setToolTip("Maximize")
        else:
            self.showMaximized()
            self.maximize_button.setText("❐")
            self.maximize_button.setToolTip("Restore")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        grip_size = self.size_grip.sizeHint()
        self.size_grip.move(self.width() - grip_size.width(), self.height() - grip_size.height())

    def eventFilter(self, obj, event) -> bool:
        if isinstance(obj, QWidget) and obj.window() is self:
            event_type = event.type()
            if event_type == QEvent.Type.MouseMove:
                global_pos = event.globalPosition().toPoint()
                if event.buttons() == Qt.MouseButton.NoButton:
                    self._update_resize_cursor(global_pos)
                elif self._resize_direction is not None:
                    self._perform_resize(global_pos)
                    return True
            elif event_type == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    global_pos = event.globalPosition().toPoint()
                    direction = self._resize_direction_at(global_pos)
                    if direction is not None:
                        self._resize_direction = direction
                        self._resize_start_geometry = self.geometry()
                        self._resize_start_pos = global_pos
                        return True
            elif event_type == QEvent.Type.MouseButtonRelease:
                if self._resize_direction is not None:
                    self._resize_direction = None
                    self._resize_start_geometry = None
                    self._resize_start_pos = None
                    return True
        return super().eventFilter(obj, event)

    def _resize_direction_at(self, global_pos: QPoint) -> Optional[str]:
        if self.isMaximized():
            return None
        pos = self.mapFromGlobal(global_pos)
        rect = self.rect()
        margin = RESIZE_MARGIN

        left = -margin <= pos.x() <= margin
        right = rect.width() - margin <= pos.x() <= rect.width() + margin
        top = -margin <= pos.y() <= margin
        bottom = rect.height() - margin <= pos.y() <= rect.height() + margin

        if top and left:
            return "top-left"
        if top and right:
            return "top-right"
        if bottom and left:
            return "bottom-left"
        if bottom and right:
            return "bottom-right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    def _update_resize_cursor(self, global_pos: QPoint) -> None:
        direction = self._resize_direction_at(global_pos)
        if direction is not None:
            self.setCursor(_CURSOR_BY_DIRECTION[direction])
        else:
            self.unsetCursor()

    def _perform_resize(self, global_pos: QPoint) -> None:
        if self._resize_start_geometry is None or self._resize_start_pos is None:
            return
        delta = global_pos - self._resize_start_pos
        geo = QRect(self._resize_start_geometry)
        direction = self._resize_direction

        if "left" in direction:
            geo.setLeft(min(geo.left() + delta.x(), geo.right() - self.minimumWidth()))
        if "right" in direction:
            geo.setRight(max(geo.right() + delta.x(), geo.left() + self.minimumWidth()))
        if "top" in direction:
            geo.setTop(min(geo.top() + delta.y(), geo.bottom() - self.minimumHeight()))
        if "bottom" in direction:
            geo.setBottom(max(geo.bottom() + delta.y(), geo.top() + self.minimumHeight()))

        self.setGeometry(geo)

    # --- Geometry persistence -----------------------------------------------

    def _restore_geometry(self) -> None:
        settings = QSettings(APP_DIR_NAME, APP_DIR_NAME)
        geometry = settings.value(GEOMETRY_SETTINGS_KEY)
        if isinstance(geometry, QByteArray) and self.restoreGeometry(geometry) and self._is_on_screen():
            return
        self.resize(*DEFAULT_WINDOW_SIZE)
        self._center_on_screen()

    def _is_on_screen(self) -> bool:
        frame = self.frameGeometry()
        return any(screen.geometry().intersects(frame) for screen in QApplication.screens())

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = min(self.width(), available.width())
        height = min(self.height(), available.height())
        self.resize(width, height)
        self.move(
            available.x() + (available.width() - width) // 2,
            available.y() + (available.height() - height) // 2,
        )

    def closeEvent(self, event) -> None:
        settings = QSettings(APP_DIR_NAME, APP_DIR_NAME)
        settings.setValue(GEOMETRY_SETTINGS_KEY, self.saveGeometry())
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)
