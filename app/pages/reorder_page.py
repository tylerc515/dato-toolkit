"""Step 2: arrange sections, rename them, and edit the tracker title."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.parser import TraceFileData
from app.project import ProjectConfig, ProjectSection
from app.titlegen import generate_title
from app.widgets import HelpPanel
from app.widgets.tracker_preview import TrackerPreview

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Step 2: Arrange Sections"
TITLE_FIELD_LABEL = "Tracker Title"
SECTION_LIST_LABEL = "Sections (drag to reorder, double-click to rename)"
PREVIEW_LABEL = "Preview"
BACK_TEXT = "← Back"
CONTINUE_TEXT = "Continue →"
AUTOSAVE_DELAY_MS = 600
STATUS_HINT = "Tip: Drag sections to reorder them, or double-click to rename."
HELP_TITLE = "Arranging Sections"
HELP_BODY = """
<p>Drag sections in the list to change the order they'll appear in the
generated tracker.</p>
<p>Double-click a section name to rename it.</p>
<p>The <b>Tracker Title</b> is generated automatically from your TRACE export
files, but you can edit it to match how your company names trackers.</p>
<p>The preview on the right updates as you make changes. Your progress is
saved automatically.</p>
"""


class ReorderPage(QWidget):
    """Step 2 page: reorder/rename sections and edit the tracker title."""

    back_requested = pyqtSignal()
    continue_requested = pyqtSignal(object)  # ProjectConfig

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._customer = ""
        self._location = ""
        self._equipment = ""
        self._date = ""
        self._output_directory = ""
        self._output_filename = ""
        self._export_pdf = False

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DELAY_MS)
        self._autosave_timer.timeout.connect(self._autosave)

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

        title_label = QLabel(TITLE_FIELD_LABEL)
        content_layout.addWidget(title_label)
        self.title_edit = QLineEdit()
        self.title_edit.setToolTip("Edit the title that appears at the top of the generated tracker")
        self.title_edit.textChanged.connect(self._on_changed)
        content_layout.addWidget(self.title_edit)

        split_row = QHBoxLayout()

        list_column = QVBoxLayout()
        list_label = QLabel(SECTION_LIST_LABEL)
        list_column.addWidget(list_label)
        self.section_list = QListWidget()
        self.section_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.section_list.setToolTip("Drag to reorder, double-click to rename")
        self.section_list.model().rowsMoved.connect(self._on_changed)
        self.section_list.itemChanged.connect(self._on_changed)
        list_column.addWidget(self.section_list, 1)
        split_row.addLayout(list_column, 1)

        preview_column = QVBoxLayout()
        preview_label = QLabel(PREVIEW_LABEL)
        preview_column.addWidget(preview_label)
        self.preview = TrackerPreview()
        preview_column.addWidget(self.preview, 1)
        split_row.addLayout(preview_column, 1)

        content_layout.addLayout(split_row, 1)

        button_row = QHBoxLayout()
        self.back_button = QPushButton(BACK_TEXT)
        self.back_button.setProperty("flat", "true")
        self.back_button.clicked.connect(self._on_back)
        button_row.addWidget(self.back_button)
        button_row.addStretch(1)
        self.continue_button = QPushButton(CONTINUE_TEXT)
        self.continue_button.setProperty("accent", "true")
        self.continue_button.setToolTip("Proceed to generate the tracker")
        self.continue_button.clicked.connect(self._on_continue)
        button_row.addWidget(self.continue_button)
        content_layout.addLayout(button_row)

        outer.addWidget(content, 1)

        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

    def _toggle_help(self) -> None:
        self.help_panel.toggle()

    def set_files(self, files: list[TraceFileData]) -> None:
        """Populate the page from freshly imported TRACE files."""
        if not files:
            return
        first = files[0]
        self._customer = first.company_name
        self._location = first.mill_location
        self._equipment = first.boiler_name
        self._date = first.inspection_date
        self._output_directory = ""
        self._output_filename = ""
        self._export_pdf = False

        sections = [
            ProjectSection(
                name=file.boiler_section,
                file_path=file.source_path,
                display_name=file.boiler_section,
                elevations=[elevation.label for elevation in file.elevations],
            )
            for file in files
        ]

        self.title_edit.blockSignals(True)
        self.title_edit.setText(generate_title(self._customer, self._location, self._equipment, self._date))
        self.title_edit.blockSignals(False)

        self._populate_sections(sections)
        self._refresh_preview()

    def load_project(self, config: ProjectConfig) -> None:
        """Populate the page from a previously saved project."""
        self._customer = config.customer
        self._location = config.location
        self._equipment = config.equipment
        self._date = config.date
        self._output_directory = config.output_directory
        self._output_filename = config.output_filename
        self._export_pdf = config.export_pdf

        self.title_edit.blockSignals(True)
        self.title_edit.setText(config.title)
        self.title_edit.blockSignals(False)

        self._populate_sections(list(config.sections))
        self._refresh_preview()

    def _populate_sections(self, sections: list[ProjectSection]) -> None:
        self.section_list.blockSignals(True)
        self.section_list.clear()
        for section in sections:
            item = QListWidgetItem(section.display_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            item.setData(Qt.ItemDataRole.UserRole, section)
            item.setToolTip("Drag to reorder, double-click to rename")
            self.section_list.addItem(item)
        self.section_list.blockSignals(False)

    def _on_changed(self, *_args) -> None:
        self._refresh_preview()
        self._autosave_timer.start()

    def _refresh_preview(self) -> None:
        sections = [section for section, _item in self._iter_sections()]
        self.preview.set_data(
            self.title_edit.text(),
            self._customer,
            self._location,
            self._equipment,
            self._date,
            sections,
        )

    def _iter_sections(self) -> list[tuple[ProjectSection, QListWidgetItem]]:
        result = []
        for row in range(self.section_list.count()):
            item = self.section_list.item(row)
            section: ProjectSection = item.data(Qt.ItemDataRole.UserRole)
            section.display_name = item.text()
            result.append((section, item))
        return result

    def _build_project_config(self) -> ProjectConfig:
        sections = [section for section, _item in self._iter_sections()]
        return ProjectConfig(
            title=self.title_edit.text(),
            customer=self._customer,
            location=self._location,
            equipment=self._equipment,
            date=self._date,
            sections=sections,
            output_directory=self._output_directory,
            output_filename=self._output_filename,
            export_pdf=self._export_pdf,
        )

    def _autosave(self) -> None:
        config = self._build_project_config()
        if config.title.strip():
            config.save()

    def _on_back(self) -> None:
        self._autosave_timer.stop()
        self._autosave()
        self.back_requested.emit()

    def _on_continue(self) -> None:
        self._autosave_timer.stop()
        config = self._build_project_config()
        if config.title.strip():
            config.save()
        self.continue_requested.emit(config)
