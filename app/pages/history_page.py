"""Full export history log: every generated tracker, most recent first."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.design.icons import icon
from app.history import HistoryEntry, format_timestamp, load_history
from app.search import matches_search
from app.widgets import HelpPanel
from app.widgets.components import FixedGridTable, SecondaryButton, StatusBadge

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Export History"
BACK_TEXT = "← Back"
NO_HISTORY_TEXT = "No trackers generated yet."
NO_MATCHES_TEXT = "No exports match your search."
OPEN_FILE_TOOLTIP = "Open the generated tracker file"
OPEN_FOLDER_TOOLTIP = "Open the folder containing the generated file"
SEARCH_PLACEHOLDER = "Search by title, customer, location, equipment, or date…"
STATUS_HINT = "Tip: Search or browse every tracker you've generated, then reopen its file or folder."
UNTITLED_TEXT = "(Untitled)"
PDF_BADGE_TEXT = "PDF"
PDF_NONE_TEXT = "—"
PDF_PRESENT_TOOLTIP = "A PDF copy was also generated alongside the Excel tracker."
PDF_ABSENT_TOOLTIP = "No PDF copy was generated for this tracker."
EQUIPMENT_COLUMN_TOOLTIP = "The equipment name recorded on the tracker (e.g. 'Recovery Boiler #2')."
HELP_TITLE = "Export History"
HELP_BODY = """
<p>Every tracker you generate is logged here automatically, most recent
first, so you can find and reopen it later even after closing the app.</p>
<p>Use the search box to filter by title, customer, location, equipment,
or date.</p>
<p>The <b>Output File</b> column lets you reopen the generated Excel file
or jump straight to its folder. The <b>PDF</b> column shows whether a PDF
copy was also generated alongside it.</p>
<p>This log only tracks generated trackers — it does not affect the saved
project files themselves, which you can manage from the dashboard.</p>
"""

_ACTION_BUTTON_SIZE = 28

# NOTE on the "Equipment" column: the original task brief called for a
# "Sections" column here, but HistoryEntry has no per-entry section *count*
# (ProjectConfig.sections is only known at generation time and is never
# persisted to history.json - only the summed elevation_count is). The
# closest real, already-collected field is `equipment` (e.g. "Recovery
# Boiler #2"), which the pre-redesign row layout silently dropped from
# display entirely. Labeling the column "Equipment" (what the data actually
# is) instead of "Sections" (what it isn't) avoids showing a misleading
# header - this is a net gain over the old UI, which showed this field
# nowhere at all.
_COLUMNS = [
    {"label": "Date", "width": 150},
    {"label": "Title", "stretch": True},
    {"label": "Customer", "width": 160},
    {"label": "Location", "width": 130},
    {"label": "Equipment", "width": 150, "tooltip": EQUIPMENT_COLUMN_TOOLTIP},
    {"label": "Elevations", "width": 80},
    {"label": "Output File", "width": 90},
    {"label": "PDF", "width": 70},
]


def _cell(widget: QWidget, alignment: Qt.AlignmentFlag) -> QWidget:
    """Wrap widget in a plain QWidget so FixedGridTable.add_row's automatic
    QLabel restyling never touches it, and so it can be given an explicit
    alignment inside its fixed-width grid cell instead of stretching to
    fill the whole column. Mirrors app.widgets.comment_code_review_widget._cell."""
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    layout.setAlignment(widget, alignment)
    return wrapper


def _text_cell(text: str) -> QLabel:
    """Plain-text QLabel for file-derived data (titles, customer names, etc.).
    Explicit PlainText format prevents Qt's default AutoText detection from
    misinterpreting "<", "&", etc. in free-typed project data as markup -
    same durable pattern used elsewhere in this redesign (see email_page.py)."""
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


def _icon_button(icon_name: str, tooltip: str) -> SecondaryButton:
    button = SecondaryButton("")
    button.setIcon(icon(icon_name))
    button.setToolTip(tooltip)
    button.setFixedSize(_ACTION_BUTTON_SIZE, _ACTION_BUTTON_SIZE)
    return button


class HistoryPage(QWidget):
    """Full export history log: every generated tracker, most recent first."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._entries: list[HistoryEntry] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        header_row = QHBoxLayout()
        self.back_button = SecondaryButton(BACK_TEXT)
        self.back_button.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.back_button)
        header_row.addSpacing(12)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(32, 32)
        self.help_button.setProperty("flat", "true")
        self.help_button.setToolTip("Show or hide help for this page")
        self.help_button.clicked.connect(self._toggle_help)
        header_row.addWidget(self.help_button)
        content_layout.addLayout(header_row)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(SEARCH_PLACEHOLDER)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        content_layout.addWidget(self.search_edit)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self._table = FixedGridTable(_COLUMNS)
        scroll_layout.addWidget(self._table)

        self._empty_label = QLabel(NO_HISTORY_TEXT)
        self._empty_label.setProperty("role", "muted")
        self._empty_label.setVisible(False)
        scroll_layout.addWidget(self._empty_label)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)

        content_layout.addWidget(scroll_area, 1)

        outer.addWidget(content, 1)

        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

    def _toggle_help(self) -> None:
        self.help_panel.toggle()

    def refresh(self) -> None:
        """Reload the full history list from disk."""
        self._entries = load_history()
        self._apply_filter()

    def _apply_filter(self) -> None:
        self._table.clear_rows()

        query = self.search_edit.text()
        entries = [
            entry
            for entry in self._entries
            if matches_search(query, entry.title, entry.customer, entry.location, entry.equipment, entry.date)
        ]

        if not entries:
            self._table.setVisible(False)
            self._empty_label.setText(NO_HISTORY_TEXT if not self._entries else NO_MATCHES_TEXT)
            self._empty_label.setVisible(True)
            return

        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        for entry in entries:
            self._table.add_row(self._make_row(entry))

    def _make_row(self, entry: HistoryEntry) -> list[QWidget]:
        open_file_btn = _icon_button("file-text", OPEN_FILE_TOOLTIP)
        open_file_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(entry.output_path))
        )

        open_folder_btn = _icon_button("folder-open", OPEN_FOLDER_TOOLTIP)
        open_folder_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(entry.output_path).parent)))
        )

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)
        actions_layout.addWidget(open_file_btn)
        actions_layout.addWidget(open_folder_btn)

        if entry.pdf_path:
            pdf_widget: QWidget = _cell(
                StatusBadge(PDF_BADGE_TEXT, "success", tooltip=PDF_PRESENT_TOOLTIP),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )
        else:
            pdf_widget = _text_cell(PDF_NONE_TEXT)
            pdf_widget.setToolTip(PDF_ABSENT_TOOLTIP)

        return [
            _text_cell(format_timestamp(entry.generated_at)),
            _text_cell(entry.title or UNTITLED_TEXT),
            _text_cell(entry.customer),
            _text_cell(entry.location),
            _text_cell(entry.equipment),
            _text_cell(str(entry.elevation_count)),
            _cell(actions, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            pdf_widget,
        ]
