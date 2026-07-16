"""Batch generation: scan a folder of TRACE export CSVs and generate one tracker per project."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.batch import BatchGenerateResult, BatchProjectGroup, BatchScanResult, generate_group, scan_folder
from app.design.tokens import Color
from app.styles import apply_card_shadow
from app.widgets import HelpPanel

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Batch Generate"
INPUT_FOLDER_LABEL = "Input Folder"
OUTPUT_FOLDER_LABEL = "Output Folder"
BROWSE_TEXT = "Browse…"
SCAN_BUTTON_TEXT = "Scan Folder"
EXPORT_PDF_LABEL = "Also export PDF copies"
GENERATE_TEXT = "Generate All"
BACK_TEXT = "← Back to Dashboard"
NO_FOLDER_TEXT = "Choose an input folder and click Scan Folder to find TRACE export CSVs."
NO_GROUPS_TEXT = "No valid TRACE export CSVs were found in this folder."
SCAN_ERRORS_LABEL = "Files that could not be read:"
GROUPS_FOUND_LABEL = "Projects found:"
GENERATING_TEXT = "Generating trackers…"
STATUS_PENDING = ""
STATUS_OK = "✓ Generated"
STATUS_WARNING = "⚠ Generated with warnings"
STATUS_ERROR = "✗ Failed"
HELP_TITLE = "Batch Generation"
HELP_BODY = """
<p>Point this at a folder containing TRACE export <b>.csv</b> files for one or
more projects, then click <b>Scan Folder</b>.</p>
<p>Files are grouped into projects automatically by customer, location,
equipment, and date. Within a project, sections are ordered by file name.</p>
<p>Uncheck any projects you don't want to generate, choose an output folder,
and click <b>Generate All</b>. Each project is saved like a normal tracker and
appears in your recent projects and export history.</p>
"""
STATUS_HINT = "Tip: Scan a folder of TRACE exports to generate trackers for multiple projects at once."

logger = logging.getLogger(__name__)


def _summary_text(group: BatchProjectGroup) -> str:
    section_count = len(group.files)
    elevation_count = sum(len(file.elevations) for file in group.files)
    subtitle = " — ".join(part for part in (group.customer, group.location) if part)
    return (
        f"<b>{group.title}</b><br>"
        f"<span style='color:{Color.TEXT_MUTED};'>{subtitle} • "
        f"{section_count} section{'s' if section_count != 1 else ''}, "
        f"{elevation_count} elevation{'s' if elevation_count != 1 else ''}</span>"
    )


class _GroupCard(QFrame):
    """One detected project: a checkbox, summary, and generation status."""

    def __init__(self, group: BatchProjectGroup, parent: QWidget | None = None):
        super().__init__(parent)
        self.group = group
        self.setProperty("card", "true")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.setToolTip("Include this project in the batch")
        layout.addWidget(self.checkbox)

        info = QLabel(_summary_text(group))
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        layout.addWidget(info, 1)

        self.status_label = QLabel(STATUS_PENDING)
        self.status_label.setProperty("role", "muted")
        layout.addWidget(self.status_label)

    def set_result(self, result: BatchGenerateResult) -> None:
        if result.error:
            self.status_label.setText(STATUS_ERROR)
            self.status_label.setStyleSheet(f"color: {Color.DANGER};")
            self.setToolTip(result.error)
        elif result.warnings:
            self.status_label.setText(STATUS_WARNING)
            self.status_label.setStyleSheet(f"color: {Color.WARNING};")
            self.setToolTip("\n".join(result.warnings))
        else:
            self.status_label.setText(STATUS_OK)
            self.status_label.setStyleSheet(f"color: {Color.SUCCESS};")


class _ErrorCard(QFrame):
    """A file that failed to parse during the folder scan."""

    def __init__(self, path: str, error: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self.setStyleSheet(f"QFrame {{ border: 1px solid {Color.DANGER}; border-radius: 12px; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        name_label = QLabel(f"⚠ {Path(path).name}")
        name_label.setStyleSheet(f"color: {Color.DANGER}; font-weight: 600;")
        layout.addWidget(name_label)

        error_label = QLabel(error)
        error_label.setWordWrap(True)
        error_label.setProperty("role", "muted")
        layout.addWidget(error_label)


class BatchGenerateWorker(QThread):
    """Generates trackers for a list of project groups on a background thread."""

    progress = pyqtSignal(int, object)  # group index, BatchGenerateResult
    finished_all = pyqtSignal()

    def __init__(self, groups: list[BatchProjectGroup], output_dir: Path, export_pdf: bool, parent=None):
        super().__init__(parent)
        self._groups = groups
        self._output_dir = output_dir
        self._export_pdf = export_pdf

    def run(self) -> None:
        for index, group in enumerate(self._groups):
            result = generate_group(group, self._output_dir, self._export_pdf)
            self.progress.emit(index, result)
        self.finished_all.emit()


class BatchPage(QWidget):
    """Batch generation page: scan a folder, then generate trackers for each project found."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._scan_result: Optional[BatchScanResult] = None
        self._cards: list[_GroupCard] = []
        self._worker: Optional[BatchGenerateWorker] = None
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
        self.help_button.setToolTip("Show help for batch generation")
        self.help_button.setProperty("flat", "true")
        self.help_button.clicked.connect(self._toggle_help)
        header_row.addWidget(self.help_button)
        content_layout.addLayout(header_row)

        input_label = QLabel(INPUT_FOLDER_LABEL)
        content_layout.addWidget(input_label)
        input_row = QHBoxLayout()
        self.input_folder_edit = QLineEdit()
        self.input_folder_edit.setToolTip("Folder containing TRACE export CSV files")
        input_row.addWidget(self.input_folder_edit, 1)
        self.input_browse_button = QPushButton(BROWSE_TEXT)
        self.input_browse_button.setProperty("flat", "true")
        self.input_browse_button.clicked.connect(self._browse_input_folder)
        input_row.addWidget(self.input_browse_button)
        self.scan_button = QPushButton(SCAN_BUTTON_TEXT)
        self.scan_button.setProperty("accent", "true")
        self.scan_button.clicked.connect(self._scan)
        input_row.addWidget(self.scan_button)
        content_layout.addLayout(input_row)

        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_area.setWidget(self.results_container)
        content_layout.addWidget(self.results_area, 1)

        output_label = QLabel(OUTPUT_FOLDER_LABEL)
        content_layout.addWidget(output_label)
        output_row = QHBoxLayout()
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setToolTip("Folder where generated trackers will be saved")
        output_row.addWidget(self.output_folder_edit, 1)
        self.output_browse_button = QPushButton(BROWSE_TEXT)
        self.output_browse_button.setProperty("flat", "true")
        self.output_browse_button.clicked.connect(self._browse_output_folder)
        output_row.addWidget(self.output_browse_button)
        content_layout.addLayout(output_row)

        self.pdf_checkbox = QCheckBox(EXPORT_PDF_LABEL)
        content_layout.addWidget(self.pdf_checkbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        content_layout.addWidget(self.progress_bar)

        button_row = QHBoxLayout()
        self.back_button = QPushButton(BACK_TEXT)
        self.back_button.setProperty("flat", "true")
        self.back_button.clicked.connect(self.back_requested.emit)
        button_row.addWidget(self.back_button)
        button_row.addStretch(1)
        self.generate_button = QPushButton(GENERATE_TEXT)
        self.generate_button.setProperty("accent", "true")
        self.generate_button.setEnabled(False)
        self.generate_button.setToolTip("Generate a tracker for each checked project")
        self.generate_button.clicked.connect(self._on_generate)
        button_row.addWidget(self.generate_button)
        content_layout.addLayout(button_row)

        outer.addWidget(content, 1)

        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

        self._show_placeholder(NO_FOLDER_TEXT)

    def _toggle_help(self) -> None:
        self.help_panel.toggle()

    # --- Folder selection --------------------------------------------------

    def _browse_input_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose input folder", self.input_folder_edit.text())
        if directory:
            self.input_folder_edit.setText(directory)

    def _browse_output_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_folder_edit.text())
        if directory:
            self.output_folder_edit.setText(directory)

    # --- Scanning ------------------------------------------------------------

    def _clear_results(self) -> None:
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._cards = []

    def _show_placeholder(self, text: str) -> None:
        self._clear_results()
        label = QLabel(text)
        label.setProperty("role", "muted")
        self.results_layout.addWidget(label)

    def _scan(self) -> None:
        folder = self.input_folder_edit.text().strip()
        if not folder or not Path(folder).is_dir():
            self._show_placeholder(NO_FOLDER_TEXT)
            self._scan_result = None
            self.generate_button.setEnabled(False)
            return

        self._scan_result = scan_folder(folder)
        if not self.output_folder_edit.text().strip():
            self.output_folder_edit.setText(folder)
        self._refresh_results()

    def _refresh_results(self) -> None:
        self._clear_results()
        result = self._scan_result
        if result is None:
            self._show_placeholder(NO_FOLDER_TEXT)
            self.generate_button.setEnabled(False)
            return

        if result.errors:
            errors_label = QLabel(SCAN_ERRORS_LABEL)
            errors_label.setProperty("role", "muted")
            self.results_layout.addWidget(errors_label)
            for file_error in result.errors:
                card = _ErrorCard(file_error.path, file_error.error)
                apply_card_shadow(card)
                self.results_layout.addWidget(card)

        if result.groups:
            groups_label = QLabel(GROUPS_FOUND_LABEL)
            groups_label.setProperty("role", "muted")
            self.results_layout.addWidget(groups_label)
            for group in result.groups:
                card = _GroupCard(group)
                apply_card_shadow(card)
                self.results_layout.addWidget(card)
                self._cards.append(card)
        elif not result.errors:
            self._show_placeholder(NO_GROUPS_TEXT)

        self.generate_button.setEnabled(bool(result.groups))

    # --- Generation ----------------------------------------------------------

    def _on_generate(self) -> None:
        if self._scan_result is None:
            return

        output_folder = self.output_folder_edit.text().strip()
        if not output_folder:
            return

        selected: list[tuple[int, BatchProjectGroup]] = [
            (index, card.group) for index, card in enumerate(self._cards) if card.checkbox.isChecked()
        ]
        if not selected:
            return

        for card in self._cards:
            card.status_label.setText(STATUS_PENDING)
            card.status_label.setStyleSheet("")
            card.checkbox.setEnabled(False)

        self.generate_button.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.progress_bar.setRange(0, len(selected))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self._selected_indices = [index for index, _group in selected]
        groups = [group for _index, group in selected]

        self._worker = BatchGenerateWorker(groups, Path(output_folder), self.pdf_checkbox.isChecked())
        self._worker.progress.connect(self._on_group_finished)
        self._worker.finished_all.connect(self._on_all_finished)
        self._worker.start()

    def _on_group_finished(self, index: int, result: BatchGenerateResult) -> None:
        card_index = self._selected_indices[index]
        self._cards[card_index].set_result(result)
        self.progress_bar.setValue(index + 1)

    def _on_all_finished(self) -> None:
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.scan_button.setEnabled(True)
        for card in self._cards:
            card.checkbox.setEnabled(True)
