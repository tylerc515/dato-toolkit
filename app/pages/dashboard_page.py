"""Dashboard: landing page with quick stats, recent projects, and recent exports."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QVBoxLayout, QWidget

from app.history import HistoryEntry, NEVER_TEXT, format_timestamp, load_history
from app.project import ProjectConfig, ProjectError, get_projects_dir, load_project
from app.styles import apply_card_shadow, color

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Dashboard"
SUBTITLE_TEXT = "Pick up a recent project or start a new tracker."
NEW_TRACKER_TEXT = "+ New Tracker"
STAT_PROJECTS_LABEL = "Saved Projects"
STAT_GENERATED_LABEL = "Trackers Generated"
STAT_ELEVATIONS_LABEL = "Elevations Tracked"
STAT_LAST_LABEL = "Last Generated"
RECENT_PROJECTS_TITLE = "Recent Projects"
RECENT_EXPORTS_TITLE = "Recent Exports"
NO_PROJECTS_TEXT = "No saved projects yet."
NO_HISTORY_TEXT = "No trackers generated yet."
OPEN_TEXT = "Open"
OPEN_FILE_TEXT = "Open File"
OPEN_FOLDER_TEXT = "Open Folder"
VIEW_ALL_TEXT = "View All"
STATUS_HINT = "Tip: Start a new tracker, or pick up where you left off below."

RECENT_PROJECTS_LIMIT = 5
RECENT_EXPORTS_LIMIT = 5


def _clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        sub_layout = item.layout()
        if sub_layout is not None:
            _clear_layout(sub_layout)


class DashboardPage(QWidget):
    """Landing page: quick stats, recent projects, and recent exports."""

    new_tracker_requested = pyqtSignal()
    project_selected = pyqtSignal(Path)
    view_history_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        header_row = QHBoxLayout()
        title_column = QVBoxLayout()
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        title_column.addWidget(title)
        subtitle = QLabel(SUBTITLE_TEXT)
        subtitle.setProperty("role", "muted")
        title_column.addWidget(subtitle)
        header_row.addLayout(title_column)
        header_row.addStretch(1)

        self.new_tracker_button = QPushButton(NEW_TRACKER_TEXT)
        self.new_tracker_button.setProperty("accent", "true")
        self.new_tracker_button.clicked.connect(self.new_tracker_requested.emit)
        header_row.addWidget(self.new_tracker_button)
        outer.addLayout(header_row)

        self.stats_row = QHBoxLayout()
        outer.addLayout(self.stats_row)

        lists_row = QHBoxLayout()
        self.recent_projects_card, self.recent_projects_layout = self._build_list_card(RECENT_PROJECTS_TITLE)
        lists_row.addWidget(self.recent_projects_card, 1)

        self.view_history_button = QPushButton(VIEW_ALL_TEXT)
        self.view_history_button.setProperty("flat", "true")
        self.view_history_button.clicked.connect(self.view_history_requested.emit)
        self.recent_exports_card, self.recent_exports_layout = self._build_list_card(
            RECENT_EXPORTS_TITLE, action_button=self.view_history_button
        )
        lists_row.addWidget(self.recent_exports_card, 1)
        outer.addLayout(lists_row, 1)

    def _build_list_card(self, title_text: str, action_button: QPushButton | None = None) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("card", "true")
        apply_card_shadow(card)

        outer_layout = QVBoxLayout(card)
        heading_row = QHBoxLayout()
        heading = QLabel(title_text)
        heading.setProperty("role", "heading")
        heading_row.addWidget(heading)
        heading_row.addStretch(1)
        if action_button is not None:
            heading_row.addWidget(action_button)
        outer_layout.addLayout(heading_row)

        rows_layout = QVBoxLayout()
        rows_layout.setSpacing(6)
        outer_layout.addLayout(rows_layout)
        outer_layout.addStretch(1)

        return card, rows_layout

    def _make_stat_card(self, value: str, label: str) -> QFrame:
        card = QFrame()
        card.setProperty("card", "true")
        apply_card_shadow(card)

        layout = QVBoxLayout(card)
        value_label = QLabel(value)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {color('highlight')};")
        layout.addWidget(value_label)

        text_label = QLabel(label)
        text_label.setProperty("role", "muted")
        layout.addWidget(text_label)

        return card

    # --- Data loading ------------------------------------------------------

    def _load_recent_projects(self) -> tuple[list[tuple[Path, ProjectConfig]], int]:
        results: list[tuple[Path, ProjectConfig]] = []
        for path in get_projects_dir().glob("*.json"):
            try:
                config = load_project(path)
            except ProjectError:
                continue
            results.append((path, config))
        results.sort(key=lambda item: item[1].last_modified, reverse=True)
        return results[:RECENT_PROJECTS_LIMIT], len(results)

    # --- Refresh -------------------------------------------------------------

    def refresh(self) -> None:
        """Reload stats, recent projects, and recent exports from disk."""
        recent_projects, total_projects = self._load_recent_projects()
        history = load_history()

        self._refresh_stats(total_projects, history)
        self._refresh_recent_projects(recent_projects)
        self._refresh_recent_exports(history[:RECENT_EXPORTS_LIMIT])

    def _refresh_stats(self, total_projects: int, history: list[HistoryEntry]) -> None:
        _clear_layout(self.stats_row)

        total_elevations = sum(entry.elevation_count for entry in history)
        last_generated = format_timestamp(history[0].generated_at) if history else NEVER_TEXT

        stats = [
            (str(total_projects), STAT_PROJECTS_LABEL),
            (str(len(history)), STAT_GENERATED_LABEL),
            (str(total_elevations), STAT_ELEVATIONS_LABEL),
            (last_generated, STAT_LAST_LABEL),
        ]
        for value, label in stats:
            self.stats_row.addWidget(self._make_stat_card(value, label), 1)

    def _refresh_recent_projects(self, recent_projects: list[tuple[Path, ProjectConfig]]) -> None:
        _clear_layout(self.recent_projects_layout)

        if not recent_projects:
            empty_label = QLabel(NO_PROJECTS_TEXT)
            empty_label.setProperty("role", "muted")
            self.recent_projects_layout.addWidget(empty_label)
            return

        for path, config in recent_projects:
            self.recent_projects_layout.addWidget(self._make_project_row(path, config))

    def _make_project_row(self, path: Path, config: ProjectConfig) -> QWidget:
        row = QFrame()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        subtitle = " — ".join(part for part in (config.customer, config.location) if part)
        info = QLabel(
            f"<b>{config.title or '(Untitled)'}</b><br>"
            f"<span style='color:{color('muted_text')};'>{subtitle}</span>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info, 1)

        open_button = QPushButton(OPEN_TEXT)
        open_button.setProperty("flat", "true")
        open_button.clicked.connect(lambda: self.project_selected.emit(path))
        layout.addWidget(open_button)

        return row

    def _refresh_recent_exports(self, recent_exports: list[HistoryEntry]) -> None:
        _clear_layout(self.recent_exports_layout)

        if not recent_exports:
            empty_label = QLabel(NO_HISTORY_TEXT)
            empty_label.setProperty("role", "muted")
            self.recent_exports_layout.addWidget(empty_label)
            return

        for entry in recent_exports:
            self.recent_exports_layout.addWidget(self._make_export_row(entry))

    def _make_export_row(self, entry: HistoryEntry) -> QWidget:
        row = QFrame()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QLabel(
            f"<b>{entry.title or '(Untitled)'}</b><br>"
            f"<span style='color:{color('muted_text')};'>{format_timestamp(entry.generated_at)}</span>"
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
