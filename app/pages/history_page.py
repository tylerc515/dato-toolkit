"""Full export history log: every generated tracker, most recent first."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.history import HistoryEntry, format_timestamp, load_history
from app.styles import COLOR_MUTED_TEXT, apply_card_shadow

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Export History"
BACK_TEXT = "← Back"
NO_HISTORY_TEXT = "No trackers generated yet."
OPEN_FILE_TEXT = "Open File"
OPEN_FOLDER_TEXT = "Open Folder"
STATUS_HINT = "Tip: Browse every tracker you've generated and reopen its file or folder."


class HistoryPage(QWidget):
    """Full export history log: every generated tracker, most recent first."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        header_row = QHBoxLayout()
        self.back_button = QPushButton(BACK_TEXT)
        self.back_button.setProperty("flat", "true")
        self.back_button.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.back_button)
        header_row.addSpacing(12)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        outer.addLayout(header_row)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch(1)
        scroll_area.setWidget(self._list_container)

        outer.addWidget(scroll_area, 1)

    def refresh(self) -> None:
        """Reload the full history list from disk."""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        entries = load_history()
        if not entries:
            empty_label = QLabel(NO_HISTORY_TEXT)
            empty_label.setProperty("role", "muted")
            self._list_layout.addWidget(empty_label)
        else:
            for entry in entries:
                self._list_layout.addWidget(self._make_export_row(entry))

        self._list_layout.addStretch(1)

    def _make_export_row(self, entry: HistoryEntry) -> QWidget:
        row = QFrame()
        row.setProperty("card", "true")
        apply_card_shadow(row)
        layout = QHBoxLayout(row)

        info = QLabel(
            f"<b>{entry.title or '(Untitled)'}</b><br>"
            f"<span style='color:{COLOR_MUTED_TEXT};'>"
            f"{entry.customer} — {entry.location} &nbsp;&middot;&nbsp; "
            f"{entry.elevation_count} elevations &nbsp;&middot;&nbsp; "
            f"{format_timestamp(entry.generated_at)}</span>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info, 1)

        open_file_button = QPushButton(OPEN_FILE_TEXT)
        open_file_button.setProperty("flat", "true")
        open_file_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(entry.output_path)))
        layout.addWidget(open_file_button)

        open_folder_button = QPushButton(OPEN_FOLDER_TEXT)
        open_folder_button.setProperty("flat", "true")
        open_folder_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(entry.output_path).parent)))
        )
        layout.addWidget(open_folder_button)

        return row
