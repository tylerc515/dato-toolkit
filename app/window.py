"""Main application window: header bar, step navigation, and page wiring."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QByteArray, QEvent, QPoint, QRect, QSettings, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizeGrip,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.logo import get_icon, get_pixmap
from app.pages.batch_page import BatchPage
from app.pages.batch_page import STATUS_HINT as BATCH_STATUS_HINT
from app.pages.dashboard_page import DashboardPage
from app.pages.dashboard_page import STATUS_HINT as DASHBOARD_STATUS_HINT
from app.pages.generate_page import GeneratePage
from app.pages.generate_page import STATUS_HINT as GENERATE_STATUS_HINT
from app.pages.history_page import HistoryPage
from app.pages.history_page import STATUS_HINT as HISTORY_STATUS_HINT
from app.pages.import_page import ImportPage
from app.pages.import_page import STATUS_HINT as IMPORT_STATUS_HINT
from app.pages.reorder_page import ReorderPage
from app.pages.reorder_page import STATUS_HINT as REORDER_STATUS_HINT
from app.pages.settings_page import SettingsPage
from app.pages.settings_page import STATUS_HINT as SETTINGS_STATUS_HINT
from app.parser import TraceFileData
from app.project import APP_DIR_NAME, ProjectConfig, ProjectError, get_app_data_dir, load_project
from app.styles import color
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

INDICATOR_COLOR_UNKNOWN = "#5a6178"

TRAY_SHOW_TEXT = "Show TRACE Tracker Builder"
TRAY_EXIT_TEXT = "Exit"
TRAY_NOTIFICATION_TITLE = "Tracker Generated"
TRAY_NOTIFICATION_BODY = "'{title}' was generated successfully."
TRAY_NOTIFICATION_DURATION_MS = 5000

STATUS_HINTS = [
    DASHBOARD_STATUS_HINT,
    IMPORT_STATUS_HINT,
    REORDER_STATUS_HINT,
    GENERATE_STATUS_HINT,
    HISTORY_STATUS_HINT,
    SETTINGS_STATUS_HINT,
    BATCH_STATUS_HINT,
]
HISTORY_PAGE_INDEX = 4
SETTINGS_PAGE_INDEX = 5
BATCH_PAGE_INDEX = 6
HOME_BUTTON_TEXT = "⌂ Dashboard"
SETTINGS_BUTTON_TEXT = "⚙ Settings"

# --- Window chrome ---------------------------------------------------------

GEOMETRY_SETTINGS_KEY = "geometry"
DEFAULT_WINDOW_SIZE = (1100, 750)
RESIZE_MARGIN = 8
WINDOW_BUTTON_SIZE = 32
WINDOW_CLOSE_HOVER = "#e94560"

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
        self.tray_icon: Optional[QSystemTrayIcon] = None

        self._build_ui()
        self._setup_tray_icon()
        QApplication.instance().installEventFilter(self)
        self._restore_geometry()
        self._run_update_check()
        self._maybe_show_onboarding()

    # --- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        central = QFrame()
        central.setObjectName("AppFrame")
        central.setStyleSheet(f"QFrame#AppFrame {{ border: 1px solid {color('border')}; }}")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self.update_banner = self._build_update_banner()
        layout.addWidget(self.update_banner)

        self.step_container = QWidget()
        step_layout = QHBoxLayout(self.step_container)
        step_layout.setContentsMargins(16, 12, 16, 12)
        self.step_indicator = StepIndicator(STEP_LABELS)
        self.step_indicator.step_clicked.connect(self._go_to_step)
        step_layout.addWidget(self.step_indicator)
        layout.addWidget(self.step_container)

        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage()
        self.import_page = ImportPage()
        self.reorder_page = ReorderPage()
        self.generate_page = GeneratePage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()
        self.batch_page = BatchPage()
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.import_page)
        self.stack.addWidget(self.reorder_page)
        self.stack.addWidget(self.generate_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.batch_page)
        layout.addWidget(self.stack, 1)

        self.dashboard_page.new_tracker_requested.connect(self._on_new_project)
        self.dashboard_page.project_selected.connect(self._on_project_load_requested)
        self.dashboard_page.view_history_requested.connect(self._go_to_history)
        self.dashboard_page.batch_requested.connect(self._go_to_batch)
        self.import_page.files_ready.connect(self._on_files_ready)
        self.import_page.project_load_requested.connect(self._on_project_load_requested)
        self.reorder_page.back_requested.connect(lambda: self._go_to_step(0))
        self.reorder_page.continue_requested.connect(self._on_reorder_continue)
        self.generate_page.back_requested.connect(lambda: self._go_to_step(1))
        self.generate_page.new_project_requested.connect(self._on_new_project)
        self.generate_page.tracker_generated.connect(self._on_tracker_generated)
        self.history_page.back_requested.connect(self._go_to_dashboard)
        self.settings_page.back_requested.connect(self._go_to_dashboard)
        self.batch_page.back_requested.connect(self._go_to_dashboard)

        self.setCentralWidget(central)

        self.size_grip = QSizeGrip(self)
        self.size_grip.setStyleSheet("background: transparent;")
        self.size_grip.raise_()

        self.status_bar = self.statusBar()
        self.stack.currentChanged.connect(self._on_page_changed)
        self._on_page_changed(self.stack.currentIndex())

        self._setup_shortcuts()

    def _build_header(self) -> QFrame:
        header = _DragHeader(self)
        header.setStyleSheet(f"background-color: {color('surface')};")
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

        layout.addSpacing(12)

        self.home_button = QPushButton(HOME_BUTTON_TEXT)
        self.home_button.setProperty("flat", "true")
        self.home_button.setToolTip("Go to dashboard")
        self.home_button.clicked.connect(self._go_to_dashboard)
        layout.addWidget(self.home_button)

        self.settings_button = QPushButton(SETTINGS_BUTTON_TEXT)
        self.settings_button.setProperty("flat", "true")
        self.settings_button.setToolTip("Open settings")
        self.settings_button.clicked.connect(self._go_to_settings)
        layout.addWidget(self.settings_button)

        layout.addStretch(1)

        self.update_indicator = _UpdateIndicator()
        self.update_indicator.setToolTip("Checking for updates…")
        layout.addWidget(self.update_indicator, 0, Qt.AlignmentFlag.AlignTop)

        layout.addSpacing(12)

        self.minimize_button = self._make_window_button("−", color("chrome_hover"))
        self.minimize_button.setToolTip("Minimize")
        self.minimize_button.clicked.connect(self.showMinimized)
        layout.addWidget(self.minimize_button, 0, Qt.AlignmentFlag.AlignTop)

        self.maximize_button = self._make_window_button("□", color("chrome_hover"))
        self.maximize_button.setToolTip("Maximize")
        self.maximize_button.clicked.connect(self._toggle_maximize_restore)
        layout.addWidget(self.maximize_button, 0, Qt.AlignmentFlag.AlignTop)

        self.close_button = self._make_window_button("×", WINDOW_CLOSE_HOVER)
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignTop)

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
            f"color: {color('text')};"
            "}"
            "QPushButton:hover {"
            f"background-color: {hover_color};"
            "}"
        )
        return button

    def _build_update_banner(self) -> QFrame:
        banner = QFrame()
        banner.setStyleSheet(f"background-color: {color('warning')}; color: #1a1a2e;")
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
            self.update_indicator.set_color(color("warning"))
            self.update_indicator.setToolTip(f"Update available: v{result.latest_version}")
            self.update_banner_label.setText(UPDATE_BANNER_TEXT.format(version=f"v{result.latest_version}"))
            self.update_banner.setVisible(True)
        else:
            self.update_indicator.set_color(color("success"))
            self.update_indicator.setToolTip("You're using the latest version")

    def _open_releases_page(self) -> None:
        QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_PAGE_URL))

    # --- System tray ---------------------------------------------------------

    def _setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(get_icon(), self)
        self.tray_icon.setToolTip(APP_NAME)

        menu = QMenu()
        show_action = QAction(TRAY_SHOW_TEXT, self)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)
        exit_action = QAction(TRAY_EXIT_TEXT, self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)
        self.tray_icon.setContextMenu(menu)

        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tracker_generated(self, title: str) -> None:
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                TRAY_NOTIFICATION_TITLE,
                TRAY_NOTIFICATION_BODY.format(title=title),
                QSystemTrayIcon.MessageIcon.Information,
                TRAY_NOTIFICATION_DURATION_MS,
            )

    # --- Step navigation -------------------------------------------------

    def _go_to_step(self, index: int) -> None:
        self.stack.setCurrentIndex(index + 1)
        self.step_indicator.set_current_step(index, self._completed_steps)

    def _go_to_dashboard(self) -> None:
        self.stack.setCurrentIndex(0)

    def _go_to_history(self) -> None:
        self.stack.setCurrentIndex(HISTORY_PAGE_INDEX)

    def _go_to_settings(self) -> None:
        self.stack.setCurrentIndex(SETTINGS_PAGE_INDEX)

    def _go_to_batch(self) -> None:
        self.stack.setCurrentIndex(BATCH_PAGE_INDEX)

    def _on_page_changed(self, index: int) -> None:
        if 0 <= index < len(STATUS_HINTS):
            self.status_bar.showMessage(STATUS_HINTS[index])
        self.step_container.setVisible(0 < index < HISTORY_PAGE_INDEX)
        if index == 0:
            self.dashboard_page.refresh()
        elif index == HISTORY_PAGE_INDEX:
            self.history_page.refresh()

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

    # --- Keyboard shortcuts --------------------------------------------------

    def _setup_shortcuts(self) -> None:
        self._add_shortcut("Ctrl+N", self._on_new_project)
        self._add_shortcut("Ctrl+D", self._go_to_dashboard)
        self._add_shortcut("Ctrl+H", self._go_to_history)
        self._add_shortcut("Ctrl+,", self._go_to_settings)
        self._add_shortcut("Ctrl+B", self._go_to_batch)
        self._add_shortcut("Ctrl+Right", self._activate_primary_action)
        self._add_shortcut("Ctrl+Return", self._activate_primary_action)
        self._add_shortcut("Ctrl+Left", self._activate_back_action)
        self._add_shortcut("F1", self._toggle_current_help)

    def _add_shortcut(self, sequence: str, handler) -> QShortcut:
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.activated.connect(handler)
        return shortcut

    def _activate_primary_action(self) -> None:
        index = self.stack.currentIndex()
        if index == 1:
            self._click_if_enabled(self.import_page.continue_button)
        elif index == 2:
            self._click_if_enabled(self.reorder_page.continue_button)
        elif index == 3:
            self._click_if_enabled(self.generate_page.generate_button)
        elif index == BATCH_PAGE_INDEX:
            self._click_if_enabled(self.batch_page.generate_button)

    def _activate_back_action(self) -> None:
        index = self.stack.currentIndex()
        if index == 1:
            self._go_to_dashboard()
        elif index == 2:
            self.reorder_page.back_button.click()
        elif index == 3:
            self.generate_page.back_button.click()
        elif index in (HISTORY_PAGE_INDEX, SETTINGS_PAGE_INDEX, BATCH_PAGE_INDEX):
            self._go_to_dashboard()

    def _toggle_current_help(self) -> None:
        page = {
            1: self.import_page,
            2: self.reorder_page,
            3: self.generate_page,
            BATCH_PAGE_INDEX: self.batch_page,
        }.get(self.stack.currentIndex())
        if page is not None:
            page.help_panel.toggle()

    @staticmethod
    def _click_if_enabled(button: QPushButton) -> None:
        if button.isEnabled():
            button.click()

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
        if not (isinstance(geometry, QByteArray) and self.restoreGeometry(geometry)):
            self.resize(*DEFAULT_WINDOW_SIZE)
        self._center_on_screen()

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
        if self.tray_icon is not None:
            self.tray_icon.hide()
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)
