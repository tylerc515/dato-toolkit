"""Step 2: arrange sections, rename them, and edit the tracker title."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from app.design.tokens import Color, Spacing
from app.parser import TraceFileData
from app.project import AuxItem, ProjectConfig, ProjectSection
from app.titlegen import generate_title
from app.widgets import HelpPanel
from app.widgets.item_editor import ItemEditorWidget
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
ADDITIONAL_SECTIONS_LABEL = "Additional Sections"
AUX_EDITOR_TITLE = "Auxiliary Scope Items"
PUNCH_EDITOR_TITLE = "Punchlist Items"
HELP_TITLE = "Arranging Sections"
HELP_BODY = """
<p>Drag sections in the list to change the order they'll appear in the
generated tracker.</p>
<p>Double-click a section name to rename it.</p>
<p>The <b>Tracker Title</b> is generated automatically from your TRACE export
files, but you can edit it to match how your company names trackers.</p>
<p>The preview on the right updates as you make changes. Your progress is
saved automatically.</p>
<p><b>Auxiliary Scope Items</b> are additional inspection tasks not part of
the standard tube sections (e.g. RT of economizer, SWUT sootblower welds).
<b>Punchlist Items</b> are carry-over action items from previous inspections.
Both sections are optional and will only appear in the tracker if you add items.</p>
"""

_COUNT_COLOR = QColor(Color.TEXT_MUTED)


class _SectionCountDelegate(QStyledItemDelegate):
    """Paints a muted elevation count to the right of each section list item."""

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        section = index.data(Qt.ItemDataRole.UserRole)
        if not section or not hasattr(section, "elevations"):
            return
        count = len(section.elevations)
        painter.save()
        painter.setPen(_COUNT_COLOR)
        small_font = painter.font()
        small_font.setPointSize(max(7, small_font.pointSize() - 1))
        painter.setFont(small_font)
        painter.drawText(
            option.rect.adjusted(0, 0, -6, 0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"({count})",
        )
        painter.restore()


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

        self._auxiliary_items: list[dict] = []
        self._punchlist_items: list[dict] = []

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
        title_label.setProperty("role", "label")
        content_layout.addWidget(title_label)
        self.title_edit = QLineEdit()
        self.title_edit.setToolTip("Edit the title that appears at the top of the generated tracker")
        self.title_edit.textChanged.connect(self._on_changed)
        content_layout.addWidget(self.title_edit)

        split_row = QHBoxLayout()

        list_column = QVBoxLayout()
        list_label = QLabel(SECTION_LIST_LABEL)
        list_label.setProperty("role", "label")
        list_column.addWidget(list_label)
        self.section_list = QListWidget()
        self.section_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.section_list.setToolTip("Drag to reorder, double-click to rename")
        self.section_list.setItemDelegate(_SectionCountDelegate(self.section_list))
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

        content_layout.addWidget(self._build_additional_panel())

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

    def _build_additional_panel(self) -> QWidget:
        container = QFrame()
        container.setProperty("card", "true")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        toggle_row = QHBoxLayout()
        self._additional_toggle = QPushButton(f"▶  {ADDITIONAL_SECTIONS_LABEL}")
        self._additional_toggle.setProperty("flat", "true")
        self._additional_toggle.setCheckable(True)
        self._additional_toggle.toggled.connect(self._on_additional_toggle)
        toggle_row.addWidget(self._additional_toggle)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        self._additional_body = QWidget()
        body_layout = QVBoxLayout(self._additional_body)
        body_layout.setContentsMargins(Spacing.MD, Spacing.SM, 0, Spacing.SM)
        body_layout.setSpacing(Spacing.LG)

        self._aux_editor = ItemEditorWidget(AUX_EDITOR_TITLE)
        self._aux_editor.items_changed.connect(self._on_aux_changed)
        body_layout.addWidget(self._aux_editor)

        self._punch_editor = ItemEditorWidget(PUNCH_EDITOR_TITLE)
        self._punch_editor.items_changed.connect(self._on_punch_changed)
        body_layout.addWidget(self._punch_editor)

        self._additional_body.setVisible(False)
        layout.addWidget(self._additional_body)
        return container

    def _on_additional_toggle(self, checked: bool) -> None:
        self._additional_body.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self._additional_toggle.setText(f"{arrow}  {ADDITIONAL_SECTIONS_LABEL}")

    def _on_aux_changed(self, items: list[dict]) -> None:
        self._auxiliary_items = items
        self._on_changed()

    def _on_punch_changed(self, items: list[dict]) -> None:
        self._punchlist_items = items
        self._on_changed()

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
        self._auxiliary_items = []
        self._punchlist_items = []
        self._aux_editor.set_items([])
        self._punch_editor.set_items([])

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
        self._auxiliary_items = [{"id": i.id, "description": i.description, "notes": i.notes} for i in config.auxiliary_items]
        self._punchlist_items = [{"id": i.id, "description": i.description, "notes": i.notes} for i in config.punchlist_items]
        self._aux_editor.set_items(self._auxiliary_items)
        self._punch_editor.set_items(self._punchlist_items)

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
            auxiliary_items=[
                AuxItem(id=i["id"], description=i["description"], notes=i.get("notes", ""))
                for i in self._auxiliary_items
            ],
            punchlist_items=[
                AuxItem(id=i["id"], description=i["description"], notes=i.get("notes", ""))
                for i in self._punchlist_items
            ],
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
