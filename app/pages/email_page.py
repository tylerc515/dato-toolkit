"""Update Email Generator page."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.email_export import EmailData, OtherItem, ScopeSection, build_email_doc
from app.history import HistoryEntry, add_history_entry
from app.project import ProjectConfig, sanitize_filename
from app.styles import apply_card_shadow, color
from app.widgets import HelpPanel

logger = logging.getLogger(__name__)

# --- UI text ------------------------------------------------------------------

TITLE_TEXT = "Update Email Generator"
BACK_TEXT = "← Back"
GENERATE_TEXT = "Generate Email Document"
SUCCESS_TITLE = "Document Generated"
SUCCESS_TEXT = "Your update email document was generated successfully."
OPEN_DOC_TEXT = "Open Document"
OPEN_FOLDER_TEXT = "Open Folder"
GENERATE_ANOTHER_TEXT = "Generate Another"
BROWSE_TEXT = "Browse…"
DOCX_SUFFIX = ".docx"
STATUS_HINT = "Tip: Load a tracker project first so sections are pre-filled automatically."

STATUS_OPTIONS = [
    "No initial data received.",
    "In progress.",
    "100% of initial data received. Verifications complete. No issues noted.",
    "100% of initial data received. Verifications complete. Issues noted — see below.",
    "Custom...",
]

HELP_TITLE = "Update Email Generator"
HELP_BODY = """
<p>The Update Email Generator creates a formatted Word document (.docx)
with the standard BSI NDE status update structure.</p>
<p>If you have already generated a tracker for this project, load it first
and the sections and auxiliary items will be pre-filled automatically.</p>
<p>Fill in the discovery findings and adjust each section status as data
comes in during the outage. Generate a new email at any time — each
generation creates a new file.</p>
<p><b>Tip:</b> Use the status dropdown on each scope section to quickly
update from "No initial data received" to "100% complete" as work progresses.</p>
"""


# --- Worker -------------------------------------------------------------------

class _EmailWorker(QThread):
    finished_ok = pyqtSignal(Path)
    failed = pyqtSignal(str)

    def __init__(self, data: EmailData, output_path: Path, parent=None):
        super().__init__(parent)
        self._data = data
        self._output_path = output_path

    def run(self) -> None:
        try:
            result = build_email_doc(self._data, self._output_path)
            self.finished_ok.emit(result)
        except Exception as exc:
            logger.exception("Email generation failed")
            self.failed.emit(str(exc))


# --- Sub-widgets --------------------------------------------------------------

class _FindingList(QWidget):
    """Simple add/remove list for free-text findings."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._list = QListWidget()
        self._list.setFixedHeight(100)
        layout.addWidget(self._list)

        entry_row = QHBoxLayout()
        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Enter finding and press Add")
        self._entry.returnPressed.connect(self._add)
        entry_row.addWidget(self._entry, 1)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add)
        entry_row.addWidget(add_btn)
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("flat", "true")
        remove_btn.clicked.connect(self._remove)
        entry_row.addWidget(remove_btn)
        layout.addLayout(entry_row)

    def _add(self) -> None:
        text = self._entry.text().strip()
        if text:
            self._list.addItem(text)
            self._entry.clear()
            self.changed.emit()

    def _remove(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self.changed.emit()

    def get_findings(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]

    def set_findings(self, findings: list[str]) -> None:
        self._list.clear()
        for f in findings:
            self._list.addItem(f)


class _SectionStatusRow(QWidget):
    """One row: section name label + status dropdown + optional custom text."""

    changed = pyqtSignal()

    def __init__(self, section_name: str, initial_status: str = STATUS_OPTIONS[0], parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        name_label = QLabel(section_name)
        name_label.setMinimumWidth(200)
        name_label.setWordWrap(False)
        layout.addWidget(name_label, 1)

        self._combo = QComboBox()
        for opt in STATUS_OPTIONS:
            self._combo.addItem(opt)
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self._combo, 2)

        self._custom = QLineEdit()
        self._custom.setPlaceholderText("Custom status text…")
        self._custom.setVisible(False)
        self._custom.textChanged.connect(self.changed)
        layout.addWidget(self._custom, 2)

        self._name = section_name
        self._set_status(initial_status)

    def _set_status(self, status: str) -> None:
        if status in STATUS_OPTIONS[:-1]:
            idx = STATUS_OPTIONS.index(status)
            self._combo.setCurrentIndex(idx)
            self._custom.setVisible(False)
        else:
            self._combo.setCurrentIndex(len(STATUS_OPTIONS) - 1)
            self._custom.setText(status)
            self._custom.setVisible(True)

    def _on_combo_changed(self, idx: int) -> None:
        is_custom = (idx == len(STATUS_OPTIONS) - 1)
        self._custom.setVisible(is_custom)
        self.changed.emit()

    def get_status(self) -> str:
        if self._combo.currentIndex() == len(STATUS_OPTIONS) - 1:
            return self._custom.text().strip() or STATUS_OPTIONS[0]
        return self._combo.currentText()

    def get_name(self) -> str:
        return self._name


class _OtherItemRow(QWidget):
    """One row: description label + status text field."""

    changed = pyqtSignal()

    def __init__(self, description: str, initial_status: str = "no report received", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        label = QLabel(description[:80] + ("…" if len(description) > 80 else ""))
        label.setWordWrap(False)
        label.setToolTip(description)
        layout.addWidget(label, 1)

        self._status = QLineEdit(initial_status)
        self._status.setMinimumWidth(220)
        self._status.textChanged.connect(self.changed)
        layout.addWidget(self._status, 1)

        self._description = description

    def get_status(self) -> str:
        return self._status.text().strip() or "no report received"

    def get_description(self) -> str:
        return self._description


# --- Main page ----------------------------------------------------------------

class EmailPage(QWidget):
    """Standalone Update Email Generator page."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: Optional[_EmailWorker] = None
        self._last_output: Optional[Path] = None
        self._section_rows: list[_SectionStatusRow] = []
        self._aux_rows: list[_OtherItemRow] = []
        self._punch_rows: list[_OtherItemRow] = []
        self._build_ui()

    # --- UI construction ------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        content_wrapper = QWidget()
        content_wrapper_layout = QVBoxLayout(content_wrapper)
        content_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_row = QHBoxLayout()
        back_btn = QPushButton(BACK_TEXT)
        back_btn.setProperty("flat", "true")
        back_btn.clicked.connect(self.back_requested.emit)
        header_row.addWidget(back_btn)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        help_btn = QPushButton("?")
        help_btn.setFixedSize(32, 32)
        help_btn.setProperty("flat", "true")
        help_btn.clicked.connect(self._toggle_help)
        header_row.addWidget(help_btn)
        content_wrapper_layout.addLayout(header_row)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        self._form_layout = QVBoxLayout(scroll_content)
        self._form_layout.setSpacing(16)
        scroll.setWidget(scroll_content)
        content_wrapper_layout.addWidget(scroll, 1)

        self._build_project_info()
        self._build_overall_status()
        self._build_findings_section("Discovery Based on Scope Work", "scope_work")
        self._build_findings_section("Discovery Based on Visual Inspection", "visual")
        self._build_scope_section()
        self._build_other_items_section()
        self._build_punchlist_section()
        self._build_output_section()
        self._form_layout.addStretch(1)

        outer.addWidget(content_wrapper, 1)
        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

    def _section_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("card", "true")
        apply_card_shadow(card)
        layout = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setProperty("role", "heading")
        layout.addWidget(heading)
        return card, layout

    def _build_project_info(self) -> None:
        card, layout = self._section_card("Project Info")
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Boiler Name"))
        self._boiler_edit = QLineEdit()
        self._boiler_edit.setPlaceholderText("e.g. RECOVERY BOILER #2")
        self._boiler_edit.textChanged.connect(self._update_filename)
        row1.addWidget(self._boiler_edit, 1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Status Date"))
        try:
            date_str = date.today().strftime("%-m/%-d/%Y")
        except ValueError:
            date_str = date.today().isoformat()
        self._date_edit = QLineEdit(date_str)
        row2.addWidget(self._date_edit, 1)
        row2.addWidget(QLabel("Status Time"))
        self._time_edit = QLineEdit(datetime.now().strftime("%I:%M %p").lstrip("0"))
        row2.addWidget(self._time_edit, 1)
        layout.addLayout(row2)
        self._form_layout.addWidget(card)

    def _build_overall_status(self) -> None:
        card, layout = self._section_card("Overall Status")
        layout.addWidget(QLabel("Summary text (auto-filled, editable):"))
        self._summary_edit = QPlainTextEdit()
        self._summary_edit.setFixedHeight(80)
        self._summary_edit.setPlainText("No initial data received.")
        layout.addWidget(self._summary_edit)
        self._form_layout.addWidget(card)

    def _build_findings_section(self, title: str, key: str) -> None:
        card, layout = self._section_card(title)
        finder = _FindingList()
        if key == "scope_work":
            self._scope_work_list = finder
        else:
            self._visual_list = finder
        layout.addWidget(finder)
        self._form_layout.addWidget(card)

    def _build_scope_section(self) -> None:
        card, layout = self._section_card("Scope of Work")
        self._scope_container = QVBoxLayout()
        self._scope_container.setSpacing(4)
        layout.addLayout(self._scope_container)
        no_lbl = QLabel("No sections loaded. Load a tracker project to pre-fill.")
        no_lbl.setProperty("role", "muted")
        self._scope_container.addWidget(no_lbl)
        self._form_layout.addWidget(card)

    def _build_other_items_section(self) -> None:
        card, layout = self._section_card("Other Scope Items")
        self._aux_container = QVBoxLayout()
        self._aux_container.setSpacing(4)
        layout.addLayout(self._aux_container)
        no_lbl = QLabel("No auxiliary items. Load a tracker project with auxiliary items.")
        no_lbl.setProperty("role", "muted")
        self._aux_container.addWidget(no_lbl)
        self._form_layout.addWidget(card)

    def _build_punchlist_section(self) -> None:
        card, layout = self._section_card("Punchlist")
        self._punch_container = QVBoxLayout()
        self._punch_container.setSpacing(4)
        layout.addLayout(self._punch_container)
        no_lbl = QLabel("No punchlist items.")
        no_lbl.setProperty("role", "muted")
        self._punch_container.addWidget(no_lbl)
        self._form_layout.addWidget(card)

    def _build_output_section(self) -> None:
        card, layout = self._section_card("Output")

        fn_row = QHBoxLayout()
        fn_row.addWidget(QLabel("Filename"))
        self._filename_edit = QLineEdit()
        fn_row.addWidget(self._filename_edit, 1)
        layout.addLayout(fn_row)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder"))
        self._folder_edit = QLineEdit(str(Path.home() / "Documents"))
        folder_row.addWidget(self._folder_edit, 1)
        browse_btn = QPushButton(BROWSE_TEXT)
        browse_btn.setProperty("flat", "true")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._success_card = QFrame()
        self._success_card.setProperty("card", "true")
        success_layout = QVBoxLayout(self._success_card)
        success_heading = QLabel(SUCCESS_TITLE)
        success_heading.setProperty("role", "heading")
        success_layout.addWidget(success_heading)
        success_text = QLabel(SUCCESS_TEXT)
        success_layout.addWidget(success_text)
        success_btns = QHBoxLayout()
        self._open_doc_btn = QPushButton(OPEN_DOC_TEXT)
        self._open_doc_btn.setProperty("accent", "true")
        self._open_doc_btn.clicked.connect(self._open_document)
        success_btns.addWidget(self._open_doc_btn)
        self._open_folder_btn = QPushButton(OPEN_FOLDER_TEXT)
        self._open_folder_btn.setProperty("flat", "true")
        self._open_folder_btn.clicked.connect(self._open_folder)
        success_btns.addWidget(self._open_folder_btn)
        self._again_btn = QPushButton(GENERATE_ANOTHER_TEXT)
        self._again_btn.setProperty("flat", "true")
        self._again_btn.clicked.connect(self._reset)
        success_btns.addWidget(self._again_btn)
        success_layout.addLayout(success_btns)
        self._success_card.setVisible(False)
        layout.addWidget(self._success_card)

        self._generate_btn = QPushButton(GENERATE_TEXT)
        self._generate_btn.setProperty("accent", "true")
        self._generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(self._generate_btn)

        self._form_layout.addWidget(card)
        self._update_filename()

    # --- Public API -----------------------------------------------------------

    def set_project(self, config: ProjectConfig) -> None:
        """Pre-fill from a loaded ProjectConfig (linked mode)."""
        self._boiler_edit.setText(config.equipment or config.title)
        self._populate_scope_sections(config.sections)
        self._populate_aux_items(config.auxiliary_items)
        self._populate_punchlist_items(config.punchlist_items)
        self._update_filename()

    def clear_project(self) -> None:
        """Reset to standalone (blank) mode."""
        self._boiler_edit.clear()
        self._populate_scope_sections([])
        self._populate_aux_items([])
        self._populate_punchlist_items([])
        self._update_filename()

    # --- Internals ------------------------------------------------------------

    def _toggle_help(self) -> None:
        self.help_panel.toggle()

    def _populate_scope_sections(self, sections) -> None:
        self._section_rows.clear()
        while self._scope_container.count():
            item = self._scope_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not sections:
            no_lbl = QLabel("No sections loaded. Load a tracker project to pre-fill.")
            no_lbl.setProperty("role", "muted")
            self._scope_container.addWidget(no_lbl)
            return

        for section in sections:
            name = getattr(section, "display_name", None) or getattr(section, "name", str(section))
            row = _SectionStatusRow(name)
            self._section_rows.append(row)
            self._scope_container.addWidget(row)

    def _populate_aux_items(self, items) -> None:
        self._aux_rows.clear()
        while self._aux_container.count():
            item = self._aux_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            no_lbl = QLabel("No auxiliary items. Load a tracker project with auxiliary items.")
            no_lbl.setProperty("role", "muted")
            self._aux_container.addWidget(no_lbl)
            return

        for item in items:
            desc = getattr(item, "description", str(item))
            row = _OtherItemRow(desc)
            self._aux_rows.append(row)
            self._aux_container.addWidget(row)

    def _populate_punchlist_items(self, items) -> None:
        self._punch_rows.clear()
        while self._punch_container.count():
            item = self._punch_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            no_lbl = QLabel("No punchlist items.")
            no_lbl.setProperty("role", "muted")
            self._punch_container.addWidget(no_lbl)
            return

        for item in items:
            desc = getattr(item, "description", str(item))
            row = _OtherItemRow(desc)
            self._punch_rows.append(row)
            self._punch_container.addWidget(row)

    def _update_filename(self) -> None:
        boiler = self._boiler_edit.text() if hasattr(self, "_boiler_edit") else ""
        today = date.today().strftime("%Y%m%d")
        name = sanitize_filename(boiler) if boiler else "UpdateEmail"
        if hasattr(self, "_filename_edit"):
            self._filename_edit.setText(f"{name}_Update_Email_{today}{DOCX_SUFFIX}")

    def _browse_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output folder", self._folder_edit.text())
        if directory:
            self._folder_edit.setText(directory)

    def _build_email_data(self) -> EmailData:
        return EmailData(
            boiler_name=self._boiler_edit.text() or "BOILER",
            status_date=self._date_edit.text(),
            status_time=self._time_edit.text(),
            overall_summary=self._summary_edit.toPlainText(),
            scope_work_findings=self._scope_work_list.get_findings(),
            visual_findings=self._visual_list.get_findings(),
            scope_sections=[
                ScopeSection(name=r.get_name(), status=r.get_status())
                for r in self._section_rows
            ],
            other_scope_items=[
                OtherItem(description=r.get_description(), status=r.get_status())
                for r in self._aux_rows
            ],
            punchlist_items=[
                OtherItem(description=r.get_description(), status=r.get_status())
                for r in self._punch_rows
            ],
        )

    def _on_generate(self) -> None:
        filename = self._filename_edit.text().strip()
        folder = self._folder_edit.text().strip()
        if not filename or not folder:
            return

        output_path = Path(folder) / filename
        data = self._build_email_data()

        self._success_card.setVisible(False)
        self._progress_bar.setVisible(True)
        self._generate_btn.setEnabled(False)

        self._worker = _EmailWorker(data, output_path)
        self._worker.finished_ok.connect(self._on_generate_finished)
        self._worker.failed.connect(self._on_generate_failed)
        self._worker.start()

    def _on_generate_finished(self, output_path: Path) -> None:
        self._last_output = output_path
        self._progress_bar.setVisible(False)
        self._generate_btn.setEnabled(True)
        self._success_card.setVisible(True)

        entry = HistoryEntry(
            title=self._boiler_edit.text() or "Update Email",
            customer="",
            location="",
            equipment=self._boiler_edit.text() or "",
            date=self._date_edit.text(),
            elevation_count=0,
            output_path=str(output_path),
            entry_type="update_email",
        )
        add_history_entry(entry)

    def _on_generate_failed(self, message: str) -> None:
        self._progress_bar.setVisible(False)
        self._generate_btn.setEnabled(True)
        logger.error("Email generation failed: %s", message)

    def _open_document(self) -> None:
        if self._last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output)))

    def _open_folder(self) -> None:
        if self._last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output.parent)))

    def _reset(self) -> None:
        self._success_card.setVisible(False)
        self._last_output = None
