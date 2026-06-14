"""Live Excel-style preview of the generated tracker, mirroring app/builder.py."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.builder import COLUMN_WIDTHS
from app.constants import TRACKER_COLUMNS
from app.project import ProjectSection

# Colors approximate the fills/fonts used by app/builder.py when generating the workbook.
SECTION_FILL_COLOR = QColor("#bfbfbf")
LEGEND_STARTED_COLOR = QColor("#ffff00")
LEGEND_COMPLETE_COLOR = QColor("#00b050")
SHEET_TEXT_COLOR = QColor("#1a1a2e")

TITLE_ROW_HEIGHT = 30
SECTION_ROW_HEIGHT = 26
ELEVATION_ROW_HEIGHT = 20

LEGEND_STARTED_TEXT = "Started"
LEGEND_COMPLETE_TEXT = "Complete"
UNTITLED_TEXT = "(Untitled Tracker)"
EMPTY_VALUE_TEXT = "—"

COLUMN_LETTERS = "ABCDEFGHIJ"
EXCEL_WIDTH_TO_PIXELS = 6

TABLE_STYLESHEET = """
QTableWidget {
    background-color: #ffffff;
    color: #1a1a2e;
    gridline-color: #c8c8c8;
    border: 1px solid #555a73;
}
QHeaderView::section {
    background-color: #d6dce5;
    color: #1a1a2e;
    padding: 4px;
    border: 1px solid #aab2c0;
    font-weight: 600;
}
"""


class TrackerPreview(QWidget):
    """Renders a live, Excel-style preview of the tracker layout."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.meta_label = QLabel()
        self.meta_label.setTextFormat(Qt.TextFormat.RichText)
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(TRACKER_COLUMNS))
        self.table.setHorizontalHeaderLabels(TRACKER_COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setStyleSheet(TABLE_STYLESHEET)

        for column_index, letter in enumerate(COLUMN_LETTERS):
            width = COLUMN_WIDTHS.get(letter, 20.71)
            self.table.setColumnWidth(column_index, int(width * EXCEL_WIDTH_TO_PIXELS))

        layout.addWidget(self.table, 1)

    def set_data(
        self,
        title: str,
        customer: str,
        location: str,
        equipment: str,
        date: str,
        sections: list[ProjectSection],
    ) -> None:
        """Rebuild the preview table from the current title/sections."""
        self.meta_label.setText(
            f"<b>Customer:</b> {customer or EMPTY_VALUE_TEXT} &nbsp;&nbsp; "
            f"<b>Location:</b> {location or EMPTY_VALUE_TEXT} &nbsp;&nbsp; "
            f"<b>Equipment:</b> {equipment or EMPTY_VALUE_TEXT} &nbsp;&nbsp; "
            f"<b>Date:</b> {date or EMPTY_VALUE_TEXT} &nbsp;&nbsp; "
            f"<span style='background-color:{LEGEND_STARTED_COLOR.name()}; color:#000; padding:1px 6px;'>"
            f"{LEGEND_STARTED_TEXT}</span> "
            f"<span style='background-color:{LEGEND_COMPLETE_COLOR.name()}; color:#000; padding:1px 6px;'>"
            f"{LEGEND_COMPLETE_TEXT}</span>"
        )

        column_count = len(TRACKER_COLUMNS)
        rows: list[tuple[str, str]] = [("title", title or UNTITLED_TEXT)]
        for section in sections:
            rows.append(("section", section.display_name))
            for elevation in section.elevations:
                rows.append(("elevation", elevation))

        self.table.setRowCount(len(rows))

        for row_index, (kind, label) in enumerate(rows):
            if kind == "title":
                self._fill_spanned_row(row_index, label, point_size=14, fill=None)
                self.table.setRowHeight(row_index, TITLE_ROW_HEIGHT)
            elif kind == "section":
                self._fill_spanned_row(row_index, label, point_size=13, fill=SECTION_FILL_COLOR)
                self.table.setRowHeight(row_index, SECTION_ROW_HEIGHT)
            else:
                item = self._make_item(label, align_center=True)
                self.table.setItem(row_index, 0, item)
                for column_index in range(1, column_count):
                    self.table.setItem(row_index, column_index, QTableWidgetItem(""))
                self.table.setRowHeight(row_index, ELEVATION_ROW_HEIGHT)

    def _fill_spanned_row(self, row_index: int, label: str, *, point_size: int, fill: QColor | None) -> None:
        column_count = len(TRACKER_COLUMNS)
        self.table.setSpan(row_index, 0, 1, column_count)
        item = self._make_item(label, bold=True, point_size=point_size, fill=fill)
        self.table.setItem(row_index, 0, item)
        for column_index in range(1, column_count):
            empty = QTableWidgetItem("")
            if fill is not None:
                empty.setBackground(fill)
            self.table.setItem(row_index, column_index, empty)

    def _make_item(
        self,
        text: str,
        *,
        bold: bool = False,
        point_size: int | None = None,
        align_center: bool = False,
        fill: QColor | None = None,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        font = QFont("Calibri")
        if point_size:
            font.setPointSize(point_size)
        font.setBold(bold)
        item.setFont(font)
        if align_center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if fill is not None:
            item.setBackground(fill)
        item.setForeground(SHEET_TEXT_COLOR)
        return item
