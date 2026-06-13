"""Step 1: import TRACE export CSV files."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.parser import TraceFileData, TraceParseError, parse_trace_csv
from app.project import find_project_for_metadata
from app.styles import COLOR_ERROR, COLOR_WARNING, apply_card_shadow
from app.widgets import HelpPanel

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Step 1: Import Files"
DROP_ZONE_TEXT = "Drag & drop TRACE export files here, or click to browse"
DROP_ZONE_HINT = "Accepted file type: .csv"
CLEAR_ALL_TEXT = "Clear All"
CONTINUE_TEXT = "Continue →"
INVALID_FILE_TYPE_MESSAGE = "Only .csv files are supported. Please drop TRACE export CSV files."
WARNING_BANNER_TEXT = (
    "Warning: These files appear to be from different projects. "
    "Check that all files are from the same inspection."
)
HELP_TITLE = "Importing Files"
HELP_BODY = """
<p>Drag your TRACE UT export <b>.csv</b> files onto the drop zone, or click it to
browse for files.</p>
<p>Each file represents one boiler section. Once loaded, you'll see the section
name and how many elevations were found.</p>
<p>If a file can't be read, it will show an error card explaining what went wrong
&mdash; other files will still load normally.</p>
<p>When you're ready, click <b>Continue</b> to arrange your sections.</p>
"""
STATUS_HINT = "Tip: Drag and drop multiple TRACE export CSV files at once."
PROJECT_FOUND_TITLE = "Saved Project Found"
PROJECT_FOUND_TEXT = "A saved project for '{title}' was found. Load it?"

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """The outcome of attempting to parse one imported file."""

    path: str
    data: Optional[TraceFileData] = None
    error: Optional[str] = None


class _DropZone(QFrame):
    """Dashed drop target that accepts CSV files via drag-and-drop or click."""

    files_dropped = pyqtSignal(list)
    invalid_drop = pyqtSignal()
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(180)
        self.setStyleSheet(
            "QFrame { border: 2px dashed #2c3759; border-radius: 12px; background-color: #16213e; }"
            "QFrame:hover { border-color: #e94560; }"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("☁")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        text = QLabel(DROP_ZONE_TEXT)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet("font-size: 15px;")
        layout.addWidget(text)

        hint = QLabel(DROP_ZONE_HINT)
        hint.setProperty("role", "muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.setToolTip(DROP_ZONE_TEXT)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        csv_paths = [p for p in paths if p.lower().endswith(".csv")]
        if not csv_paths:
            self.invalid_drop.emit()
            return
        self.files_dropped.emit(csv_paths)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _FileCard(QFrame):
    """A single imported-file row showing parse status and a remove button."""

    remove_requested = pyqtSignal(str)

    def __init__(self, result: ImportResult, parent: QWidget | None = None):
        super().__init__(parent)
        self.path = result.path
        self.setProperty("card", "true")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        info_layout = QVBoxLayout()
        filename = Path(result.path).name

        if result.error:
            self.setStyleSheet(f"QFrame {{ border: 1px solid {COLOR_ERROR}; border-radius: 12px; }}")
            name_label = QLabel(f"⚠ {filename}")
            name_label.setStyleSheet(f"color: {COLOR_ERROR}; font-weight: 600;")
            info_layout.addWidget(name_label)
            error_label = QLabel(result.error)
            error_label.setWordWrap(True)
            error_label.setProperty("role", "muted")
            info_layout.addWidget(error_label)
        else:
            data = result.data
            assert data is not None
            name_label = QLabel(filename)
            name_label.setStyleSheet("font-weight: 600;")
            info_layout.addWidget(name_label)
            detail_label = QLabel(f"Section: {data.boiler_section}  •  {len(data.elevations)} elevations")
            detail_label.setProperty("role", "muted")
            info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, 1)

        remove_button = QPushButton("×")
        remove_button.setProperty("flat", "true")
        remove_button.setFixedSize(32, 32)
        remove_button.setToolTip(f"Remove {filename}")
        remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_button.clicked.connect(lambda: self.remove_requested.emit(self.path))
        layout.addWidget(remove_button)


class ImportPage(QWidget):
    """Step 1 page: drag-and-drop import and parsing of TRACE export CSVs."""

    files_ready = pyqtSignal(list)  # list[TraceFileData]
    project_load_requested = pyqtSignal(object)  # Path

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._results: list[ImportResult] = []
        self._project_check_done = False
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        header_row = QHBoxLayout()
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(32, 32)
        self.help_button.setToolTip("Show help for this step")
        self.help_button.setProperty("flat", "true")
        self.help_button.clicked.connect(self._toggle_help)
        header_row.addWidget(self.help_button)
        content_layout.addLayout(header_row)

        self.warning_banner = QLabel(WARNING_BANNER_TEXT)
        self.warning_banner.setWordWrap(True)
        self.warning_banner.setStyleSheet(
            f"background-color: {COLOR_WARNING}; color: #1a1a2e; border-radius: 8px; padding: 10px;"
        )
        self.warning_banner.setVisible(False)
        content_layout.addWidget(self.warning_banner)

        self.drop_zone = _DropZone()
        self.drop_zone.files_dropped.connect(self.add_files)
        self.drop_zone.invalid_drop.connect(self._show_invalid_drop_message)
        self.drop_zone.clicked.connect(self._browse_files)
        content_layout.addWidget(self.drop_zone)

        self.file_list_area = QScrollArea()
        self.file_list_area.setWidgetResizable(True)
        self.file_list_container = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_container)
        self.file_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.file_list_area.setWidget(self.file_list_container)
        content_layout.addWidget(self.file_list_area, 1)

        button_row = QHBoxLayout()
        self.clear_all_button = QPushButton(CLEAR_ALL_TEXT)
        self.clear_all_button.setProperty("flat", "true")
        self.clear_all_button.setToolTip("Remove all imported files")
        self.clear_all_button.clicked.connect(self.clear_all)
        button_row.addWidget(self.clear_all_button)
        button_row.addStretch(1)
        self.continue_button = QPushButton(CONTINUE_TEXT)
        self.continue_button.setProperty("accent", "true")
        self.continue_button.setEnabled(False)
        self.continue_button.setToolTip("Proceed to arrange sections")
        self.continue_button.clicked.connect(self._emit_files_ready)
        button_row.addWidget(self.continue_button)
        content_layout.addLayout(button_row)

        outer.addWidget(content, 1)

        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

    def _toggle_help(self) -> None:
        self.help_panel.toggle()

    def _show_invalid_drop_message(self) -> None:
        QMessageBox.warning(self, "Unsupported File Type", INVALID_FILE_TYPE_MESSAGE)

    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select TRACE export files", "", "CSV Files (*.csv)")
        if paths:
            self.add_files(paths)

    def add_files(self, paths: list[str]) -> None:
        for path in paths:
            if any(r.path == path for r in self._results):
                continue
            try:
                data = parse_trace_csv(path)
                self._results.append(ImportResult(path=path, data=data))
            except TraceParseError as exc:
                logger.warning("Failed to parse %s: %s", path, exc)
                self._results.append(ImportResult(path=path, error=str(exc)))
        self._refresh()
        self._maybe_check_for_saved_project()

    def remove_file(self, path: str) -> None:
        self._results = [r for r in self._results if r.path != path]
        self._refresh()

    def clear_all(self) -> None:
        self._results = []
        self._project_check_done = False
        self._refresh()

    def _refresh(self) -> None:
        while self.file_list_layout.count():
            item = self.file_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for result in self._results:
            card = _FileCard(result)
            apply_card_shadow(card)
            card.remove_requested.connect(self.remove_file)
            self.file_list_layout.addWidget(card)

        valid_results = [r for r in self._results if r.data is not None]
        self.continue_button.setEnabled(bool(valid_results))
        self._update_warning_banner(valid_results)

    def _update_warning_banner(self, valid_results: list[ImportResult]) -> None:
        if len(valid_results) < 2:
            self.warning_banner.setVisible(False)
            return

        def key(result: ImportResult) -> tuple:
            data = result.data
            assert data is not None
            return (data.company_name, data.mill_location, data.boiler_name, data.inspection_date)

        keys = {key(r) for r in valid_results}
        self.warning_banner.setVisible(len(keys) > 1)

    def _maybe_check_for_saved_project(self) -> None:
        if self._project_check_done:
            return
        valid_results = [r for r in self._results if r.data is not None]
        if not valid_results:
            return
        self._project_check_done = True

        data = valid_results[0].data
        assert data is not None
        project_path = find_project_for_metadata(
            data.company_name, data.mill_location, data.boiler_name, data.inspection_date
        )
        if project_path is None:
            return

        title = project_path.stem
        reply = QMessageBox.question(
            self,
            PROJECT_FOUND_TITLE,
            PROJECT_FOUND_TEXT.format(title=title),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.project_load_requested.emit(project_path)

    def _emit_files_ready(self) -> None:
        valid_results = [r.data for r in self._results if r.data is not None]
        self.files_ready.emit(valid_results)
