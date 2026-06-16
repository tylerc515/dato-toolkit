"""Step 3: review the summary, choose output options, and generate the tracker."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.builder import TrackerData, TrackerItem, TrackerSection, build_tracker
from app.history import HistoryEntry, add_history_entry
from app.logo import get_pixmap
from app.pdf_export import export_tracker_pdf
from app.project import ProjectConfig, sanitize_filename
from app.styles import apply_card_shadow, color
from app.validation import validate_tracker_output
from app.widgets import HelpPanel

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Step 3: Generate Tracker"
SUMMARY_TITLE = "Summary"
OUTPUT_FOLDER_LABEL = "Output Folder"
OUTPUT_FILENAME_LABEL = "Output Filename"
BROWSE_TEXT = "Browse…"
EXPORT_PDF_LABEL = "Also export a PDF copy"
GENERATE_TEXT = "Generate Tracker"
BACK_TEXT = "← Back"
GENERATING_TEXT = "Generating tracker…"
SUCCESS_TITLE = "Tracker Generated"
SUCCESS_TEXT = "Your tracker was generated successfully."
OPEN_FILE_TEXT = "Open File"
OPEN_FOLDER_TEXT = "Open Folder"
EMAIL_TEXT = "Email Tracker"
NEW_PROJECT_TEXT = "Start New Project"
EMAIL_SUBJECT_TEXT = "Tracker: {title}"
EMAIL_BODY_TEXT = 'The tracker "{title}" has been generated and is saved at:\n{xlsx_path}\n'
EMAIL_BODY_PDF_LINE = "\nA PDF copy is also available at:\n{pdf_path}\n"
EMAIL_BODY_ATTACH_HINT = "\nPlease attach the file(s) above before sending."
MISSING_OUTPUT_FOLDER_TITLE = "Output Folder Required"
MISSING_OUTPUT_FOLDER_TEXT = "Please choose an output folder before generating the tracker."
MISSING_OUTPUT_FILENAME_TITLE = "Output Filename Required"
MISSING_OUTPUT_FILENAME_TEXT = "Please enter a filename for the generated tracker."
GENERATION_FAILED_TITLE = "Generation Failed"
VALIDATION_WARNING_PREFIX = "⚠ The generated file may be incomplete:<br>"
HELP_TITLE = "Generating Your Tracker"
HELP_BODY = """
<p>Review the summary, then choose where to save the generated tracker and
what to name it.</p>
<p>Enable <b>Also export a PDF copy</b> if you'd like a PDF version alongside
the Excel file.</p>
<p>Click <b>Generate Tracker</b> to create the file. When it's done, you can
open it directly, open its folder, or start a new project.</p>
"""

XLSX_SUFFIX = ".xlsx"
PDF_SUFFIX = ".pdf"
STATUS_HINT = "Tip: Choose an output folder and filename, then click Generate Tracker."
SUCCESS_FADE_DURATION_MS = 300

logger = logging.getLogger(__name__)


class GenerateWorker(QThread):
    """Builds the Excel tracker (and optionally a PDF) on a background thread."""

    finished_ok = pyqtSignal(Path, object, list)  # xlsx_path, Optional[Path] pdf_path, warnings
    failed = pyqtSignal(str)

    def __init__(self, data: TrackerData, xlsx_path: Path, pdf_path: Optional[Path], parent=None):
        super().__init__(parent)
        self._data = data
        self._xlsx_path = xlsx_path
        self._pdf_path = pdf_path

    def run(self) -> None:
        try:
            build_tracker(self._data, self._xlsx_path)
            pdf_result: Optional[Path] = None
            if self._pdf_path is not None:
                pdf_result = export_tracker_pdf(self._xlsx_path, self._pdf_path, self._data)
        except OSError as exc:
            logger.exception("Tracker generation failed")
            self.failed.emit(str(exc))
            return
        warnings = validate_tracker_output(self._data, self._xlsx_path, pdf_result)
        self.finished_ok.emit(self._xlsx_path, pdf_result, warnings)


class GeneratePage(QWidget):
    """Step 3 page: summary, output options, generation, and success actions."""

    back_requested = pyqtSignal()
    new_project_requested = pyqtSignal()
    tracker_generated = pyqtSignal(str)  # title

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._config: Optional[ProjectConfig] = None
        self._worker: Optional[GenerateWorker] = None
        self._last_xlsx_path: Optional[Path] = None
        self._last_pdf_path: Optional[Path] = None
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

        self.summary_card = QFrame()
        self.summary_card.setProperty("card", "true")
        apply_card_shadow(self.summary_card)
        summary_layout = QVBoxLayout(self.summary_card)
        summary_heading = QLabel(SUMMARY_TITLE)
        summary_heading.setProperty("role", "heading")
        summary_layout.addWidget(summary_heading)
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        content_layout.addWidget(self.summary_card)

        folder_label = QLabel(OUTPUT_FOLDER_LABEL)
        content_layout.addWidget(folder_label)
        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setToolTip("Folder where the generated tracker will be saved")
        folder_row.addWidget(self.folder_edit, 1)
        self.browse_button = QPushButton(BROWSE_TEXT)
        self.browse_button.setProperty("flat", "true")
        self.browse_button.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.browse_button)
        content_layout.addLayout(folder_row)

        filename_label = QLabel(OUTPUT_FILENAME_LABEL)
        content_layout.addWidget(filename_label)
        self.filename_edit = QLineEdit()
        self.filename_edit.setToolTip("Name of the generated Excel file")
        content_layout.addWidget(self.filename_edit)

        self.pdf_checkbox = QCheckBox(EXPORT_PDF_LABEL)
        self.pdf_checkbox.setToolTip("Also save a PDF copy of the generated tracker")
        content_layout.addWidget(self.pdf_checkbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        content_layout.addWidget(self.progress_bar)

        self.success_card = QFrame()
        self.success_card.setProperty("card", "true")
        apply_card_shadow(self.success_card)
        success_layout = QVBoxLayout(self.success_card)
        success_heading = QLabel(SUCCESS_TITLE)
        success_heading.setProperty("role", "heading")
        success_layout.addWidget(success_heading)
        success_logo = QLabel()
        success_logo.setPixmap(get_pixmap(180, 105))
        success_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(success_logo)
        success_text = QLabel(SUCCESS_TEXT)
        success_layout.addWidget(success_text)
        self.validation_warning_label = QLabel("")
        self.validation_warning_label.setWordWrap(True)
        self.validation_warning_label.setStyleSheet(f"color: {color('warning')};")
        self.validation_warning_label.setVisible(False)
        success_layout.addWidget(self.validation_warning_label)
        success_buttons = QHBoxLayout()
        self.open_file_button = QPushButton(OPEN_FILE_TEXT)
        self.open_file_button.clicked.connect(self._open_file)
        success_buttons.addWidget(self.open_file_button)
        self.open_folder_button = QPushButton(OPEN_FOLDER_TEXT)
        self.open_folder_button.setProperty("flat", "true")
        self.open_folder_button.clicked.connect(self._open_folder)
        success_buttons.addWidget(self.open_folder_button)
        self.email_button = QPushButton(EMAIL_TEXT)
        self.email_button.setProperty("flat", "true")
        self.email_button.setToolTip("Open your email client with the tracker details")
        self.email_button.clicked.connect(self._email_tracker)
        success_buttons.addWidget(self.email_button)
        self.new_project_button = QPushButton(NEW_PROJECT_TEXT)
        self.new_project_button.setProperty("flat", "true")
        self.new_project_button.clicked.connect(self.new_project_requested.emit)
        success_buttons.addWidget(self.new_project_button)
        success_layout.addLayout(success_buttons)
        self.success_card.setVisible(False)
        content_layout.addWidget(self.success_card)

        self._success_opacity_effect = QGraphicsOpacityEffect(self.success_card)
        self._success_opacity_effect.setOpacity(1.0)
        self.success_card.setGraphicsEffect(self._success_opacity_effect)
        self._success_animation = QPropertyAnimation(self._success_opacity_effect, b"opacity", self)
        self._success_animation.setDuration(SUCCESS_FADE_DURATION_MS)
        self._success_animation.setStartValue(0.0)
        self._success_animation.setEndValue(1.0)
        self._success_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        content_layout.addStretch(1)

        button_row = QHBoxLayout()
        self.back_button = QPushButton(BACK_TEXT)
        self.back_button.setProperty("flat", "true")
        self.back_button.clicked.connect(self.back_requested.emit)
        button_row.addWidget(self.back_button)
        button_row.addStretch(1)
        self.generate_button = QPushButton(GENERATE_TEXT)
        self.generate_button.setProperty("accent", "true")
        self.generate_button.setToolTip("Create the formatted Excel tracker")
        self.generate_button.clicked.connect(self._on_generate)
        button_row.addWidget(self.generate_button)
        content_layout.addLayout(button_row)

        outer.addWidget(content, 1)

        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

    def _toggle_help(self) -> None:
        self.help_panel.toggle()

    def set_project(self, config: ProjectConfig) -> None:
        """Populate the page from the project assembled in Step 2."""
        self._config = config
        self.success_card.setVisible(False)

        section_count = len(config.sections)
        elevation_count = sum(len(section.elevations) for section in config.sections)
        self.summary_label.setText(
            f"<b>Title:</b> {config.title}<br>"
            f"<b>Customer:</b> {config.customer}<br>"
            f"<b>Location:</b> {config.location}<br>"
            f"<b>Equipment:</b> {config.equipment}<br>"
            f"<b>Project Date:</b> {config.date}<br>"
            f"<b>Sections:</b> {section_count}<br>"
            f"<b>Elevations:</b> {elevation_count}"
        )

        self.folder_edit.setText(config.output_directory or str(Path.home() / "Documents"))
        self.filename_edit.setText(config.output_filename or sanitize_filename(config.title) + XLSX_SUFFIX)
        self.pdf_checkbox.setChecked(config.export_pdf)

    def _browse_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output folder", self.folder_edit.text())
        if directory:
            self.folder_edit.setText(directory)

    def _on_generate(self) -> None:
        if self._config is None:
            return

        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, MISSING_OUTPUT_FOLDER_TITLE, MISSING_OUTPUT_FOLDER_TEXT)
            return

        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(self, MISSING_OUTPUT_FILENAME_TITLE, MISSING_OUTPUT_FILENAME_TEXT)
            return
        if not filename.lower().endswith(XLSX_SUFFIX):
            filename += XLSX_SUFFIX

        export_pdf = self.pdf_checkbox.isChecked()

        self._config.output_directory = folder
        self._config.output_filename = filename
        self._config.export_pdf = export_pdf
        if self._config.title.strip():
            self._config.save()

        xlsx_path = Path(folder) / filename
        pdf_path = xlsx_path.with_suffix(PDF_SUFFIX) if export_pdf else None

        data = TrackerData(
            title=self._config.title,
            customer=self._config.customer,
            location=self._config.location,
            equipment=self._config.equipment,
            date=self._config.date,
            sections=[
                TrackerSection(name=section.display_name, elevations=list(section.elevations))
                for section in self._config.sections
            ],
            auxiliary_items=[
                TrackerItem(description=i.description, notes=i.notes)
                for i in self._config.auxiliary_items
            ],
            punchlist_items=[
                TrackerItem(description=i.description, notes=i.notes)
                for i in self._config.punchlist_items
            ],
        )

        self.success_card.setVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.generate_button.setEnabled(False)
        self.back_button.setEnabled(False)

        self._worker = GenerateWorker(data, xlsx_path, pdf_path)
        self._worker.finished_ok.connect(self._on_generate_finished)
        self._worker.failed.connect(self._on_generate_failed)
        self._worker.start()

    def _on_generate_finished(self, xlsx_path: Path, pdf_path: Optional[Path], warnings: list[str]) -> None:
        self._last_xlsx_path = xlsx_path
        self._last_pdf_path = pdf_path
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.back_button.setEnabled(True)
        self.success_card.setVisible(True)
        self._success_animation.stop()
        self._success_animation.start()

        if warnings:
            self.validation_warning_label.setText(
                VALIDATION_WARNING_PREFIX + "<br>".join(f"• {message}" for message in warnings)
            )
            self.validation_warning_label.setVisible(True)
        else:
            self.validation_warning_label.setVisible(False)

        if self._config is not None:
            elevation_count = sum(len(section.elevations) for section in self._config.sections)
            add_history_entry(
                HistoryEntry(
                    title=self._config.title,
                    customer=self._config.customer,
                    location=self._config.location,
                    equipment=self._config.equipment,
                    date=self._config.date,
                    elevation_count=elevation_count,
                    output_path=str(xlsx_path),
                    pdf_path=str(pdf_path) if pdf_path else "",
                    generated_at=datetime.now().isoformat(),
                )
            )
            self.tracker_generated.emit(self._config.title)

    def _on_generate_failed(self, message: str) -> None:
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.back_button.setEnabled(True)
        QMessageBox.critical(self, GENERATION_FAILED_TITLE, message)

    def _open_file(self) -> None:
        if self._last_xlsx_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_xlsx_path)))

    def _open_folder(self) -> None:
        if self._last_xlsx_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_xlsx_path.parent)))

    def _email_tracker(self) -> None:
        if self._last_xlsx_path is None or self._config is None:
            return
        title = self._config.title
        body = EMAIL_BODY_TEXT.format(title=title, xlsx_path=self._last_xlsx_path)
        if self._last_pdf_path is not None:
            body += EMAIL_BODY_PDF_LINE.format(pdf_path=self._last_pdf_path)
        body += EMAIL_BODY_ATTACH_HINT
        subject = EMAIL_SUBJECT_TEXT.format(title=title)
        QDesktopServices.openUrl(QUrl(f"mailto:?subject={quote(subject)}&body={quote(body)}"))
