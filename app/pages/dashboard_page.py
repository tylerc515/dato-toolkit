"""Dashboard: landing page with quick stats, recent projects, and recent exports."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLayout, QVBoxLayout, QWidget

from app.design.icons import icon
from app.design.tokens import Color, Spacing
from app.design.tooltip import set_tooltip
from app.history import HistoryEntry, format_timestamp, load_history
from app.project import ProjectConfig, list_projects
from app.widgets.components import (
    Card,
    FlowLayout,
    PageScrollArea,
    PrimaryButton,
    ResponsiveColumns,
    SecondaryButton,
    StatCard,
    keep_content_height,
)

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "Dashboard"
SUBTITLE_TEXT = "Pick up a recent project or start a new tracker."
NEW_TRACKER_TEXT = "New Tracker"
BATCH_GENERATE_TEXT = "Batch Generate"
STAT_PROJECTS_LABEL = "Saved Projects"
STAT_GENERATED_LABEL = "Trackers Generated"
STAT_ELEVATIONS_LABEL = "Elevations Tracked"
STAT_LAST_LABEL = "Last Generated"
STAT_EMAILS_LABEL = "Update Emails"
GENERATE_EMAIL_TEXT = "Generate Update Email"
CONVERT_DATA_TEXT = "Convert Data Files"
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

# Thresholds are content-column widths (window minus sidebar and page margins).
# Title block | action buttons stay on one row while the subtitle and all four
# buttons fit side by side (about 1080 px); below that the buttons drop under
# the title so they get the full width instead of wrapping one per line.
HEADER_STACK_BELOW = 1080
# Recent Projects | Recent Exports sit side by side until the content column
# is narrower than this, then stack. Below it an export row cannot hold its
# title plus both buttons legibly.
LISTS_STACK_BELOW = 960


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
    view_projects_requested = pyqtSignal()
    batch_requested = pyqtSignal()
    email_requested = pyqtSignal()
    converter_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        page_layout.addWidget(PageScrollArea(content))

        outer = QVBoxLayout(content)
        outer.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        outer.setSpacing(Spacing.LG)

        # Title block | action buttons. When the content column is too narrow
        # for the title and all four buttons on one line, the buttons drop
        # below the title (full width) instead of wrapping one per line beside
        # it; within their row they wrap right-aligned and never truncate.
        self.header = ResponsiveColumns(stack_below=HEADER_STACK_BELOW, spacing=Spacing.SM)
        title_block = QWidget()
        title_column = QVBoxLayout(title_block)
        title_column.setContentsMargins(0, 0, 0, 0)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        title_column.addWidget(title)
        subtitle = QLabel(SUBTITLE_TEXT)
        subtitle.setProperty("role", "muted")
        title_column.addWidget(subtitle)
        self.header.add_column(title_block, stretch=0)

        self.actions = QWidget()
        actions_flow = FlowLayout(self.actions, h_spacing=Spacing.SM, v_spacing=Spacing.SM, align_right=True)
        actions_flow.setContentsMargins(0, 0, 0, 0)
        self.header.add_column(self.actions, stretch=1)

        self.new_tracker_button = PrimaryButton(NEW_TRACKER_TEXT)
        self.new_tracker_button.setIcon(icon("plus", color=Color.TEXT_PRIMARY))
        self.new_tracker_button.clicked.connect(self.new_tracker_requested.emit)
        actions_flow.addWidget(self.new_tracker_button)

        self.batch_button = SecondaryButton(BATCH_GENERATE_TEXT)
        self.batch_button.setIcon(icon("table"))
        set_tooltip(self.batch_button, "Generate trackers for multiple projects from a folder of CSVs")
        self.batch_button.clicked.connect(self.batch_requested.emit)
        actions_flow.addWidget(self.batch_button)

        self.email_button = SecondaryButton(GENERATE_EMAIL_TEXT)
        self.email_button.setIcon(icon("paper-plane-tilt"))
        set_tooltip(self.email_button, "Generate a formatted NDE status update email document")
        self.email_button.clicked.connect(self.email_requested.emit)
        actions_flow.addWidget(self.email_button)

        self.converter_button = SecondaryButton(CONVERT_DATA_TEXT)
        self.converter_button.setIcon(icon("arrows-left-right"))
        set_tooltip(self.converter_button, "Convert ATS, TEAM, or TDS inspection files to Standard Format CSV")
        self.converter_button.clicked.connect(self.converter_requested.emit)
        actions_flow.addWidget(self.converter_button)
        outer.addWidget(self.header)

        # Stat cards: 4 across, then 2x2, then one column as the width shrinks.
        self.stats_grid = QWidget()
        self.stats_row = FlowLayout(self.stats_grid, h_spacing=Spacing.MD, v_spacing=Spacing.MD, equal_widths=True)
        self.stats_row.setContentsMargins(0, 0, 0, 0)
        self._stat_projects = StatCard(
            STAT_PROJECTS_LABEL, "0",
            tooltip="Tracker projects you've saved, including drafts you haven't generated yet.",
        )
        self._stat_generated = StatCard(
            STAT_GENERATED_LABEL, "0",
            tooltip="Excel trackers you've generated so far (update emails are counted separately).",
        )
        self._stat_elevations = StatCard(
            STAT_ELEVATIONS_LABEL, "0",
            tooltip="Total inspection elevations recorded across every tracker you've generated.",
        )
        self._stat_emails = StatCard(
            STAT_EMAILS_LABEL, "0",
            tooltip="NDE status update email documents you've generated.",
        )
        for stat_card in (self._stat_projects, self._stat_generated, self._stat_elevations, self._stat_emails):
            keep_content_height(stat_card)
            self.stats_row.addWidget(stat_card)
        outer.addWidget(self.stats_grid)

        self.lists = ResponsiveColumns(stack_below=LISTS_STACK_BELOW, spacing=Spacing.MD)
        self.view_projects_button = SecondaryButton(VIEW_ALL_TEXT)
        self.view_projects_button.clicked.connect(self.view_projects_requested.emit)
        self.recent_projects_card, self.recent_projects_layout = self._build_list_card(
            RECENT_PROJECTS_TITLE, action_button=self.view_projects_button
        )
        self.lists.add_column(self.recent_projects_card)

        self.view_history_button = SecondaryButton(VIEW_ALL_TEXT)
        self.view_history_button.clicked.connect(self.view_history_requested.emit)
        self.recent_exports_card, self.recent_exports_layout = self._build_list_card(
            RECENT_EXPORTS_TITLE, action_button=self.view_history_button
        )
        self.lists.add_column(self.recent_exports_card)
        outer.addWidget(self.lists, 1)

    def _build_list_card(self, title_text: str, action_button: SecondaryButton | None = None) -> tuple[Card, QVBoxLayout]:
        card = Card()
        outer_layout = card.layout()

        heading_row = QHBoxLayout()
        heading = QLabel(title_text)
        heading.setProperty("role", "heading")
        heading_row.addWidget(heading)
        heading_row.addStretch(1)
        if action_button is not None:
            heading_row.addWidget(action_button)
        outer_layout.addLayout(heading_row)

        # Rows keep their natural (word-wrapped) height and a trailing stretch
        # absorbs the spare space; the page scrolls when the window is short.
        # An aligned layout (setAlignment(AlignTop)) must NOT be used here: it
        # lays rows out at their unwrapped sizeHint, cutting wrapped titles.
        rows_layout = QVBoxLayout()
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(Spacing.SM)
        rows_layout.addStretch(1)
        outer_layout.addLayout(rows_layout, 1)

        return card, rows_layout

    # --- Data loading ------------------------------------------------------

    def _load_recent_projects(self) -> tuple[list[tuple[Path, ProjectConfig]], int]:
        results = list_projects()
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
        tracker_history = [e for e in history if e.entry_type != "update_email"]
        email_count = sum(1 for e in history if e.entry_type == "update_email")
        total_elevations = sum(entry.elevation_count for entry in tracker_history)

        self._stat_projects.set_value(str(total_projects))
        self._stat_generated.set_value(str(len(tracker_history)))
        self._stat_elevations.set_value(str(total_elevations))
        self._stat_emails.set_value(str(email_count))

    def _refresh_recent_projects(self, recent_projects: list[tuple[Path, ProjectConfig]]) -> None:
        _clear_layout(self.recent_projects_layout)

        if not recent_projects:
            empty_label = QLabel(NO_PROJECTS_TEXT)
            empty_label.setProperty("role", "muted")
            self.recent_projects_layout.addWidget(empty_label)
        for path, config in recent_projects:
            self.recent_projects_layout.addWidget(self._make_project_row(path, config))
        self.recent_projects_layout.addStretch(1)

    def _make_project_row(self, path: Path, config: ProjectConfig) -> QWidget:
        row = Card()
        keep_content_height(row)
        inner_layout = QHBoxLayout()
        row.layout().addLayout(inner_layout)

        subtitle = " — ".join(part for part in (config.customer, config.location) if part)
        info = QLabel(
            f"<b>{config.title or '(Untitled)'}</b><br>"
            f"<span style='color:{Color.TEXT_MUTED};'>{subtitle}</span>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        inner_layout.addWidget(info, 1)

        open_button = SecondaryButton(OPEN_TEXT)
        open_button.clicked.connect(lambda: self.project_selected.emit(path))
        inner_layout.addWidget(open_button)

        return row

    def _refresh_recent_exports(self, recent_exports: list[HistoryEntry]) -> None:
        _clear_layout(self.recent_exports_layout)

        if not recent_exports:
            empty_label = QLabel(NO_HISTORY_TEXT)
            empty_label.setProperty("role", "muted")
            self.recent_exports_layout.addWidget(empty_label)
        for entry in recent_exports:
            self.recent_exports_layout.addWidget(self._make_export_row(entry))
        self.recent_exports_layout.addStretch(1)

    def _make_export_row(self, entry: HistoryEntry) -> QWidget:
        row = Card()
        keep_content_height(row)
        inner_layout = QHBoxLayout()
        row.layout().addLayout(inner_layout)

        info = QLabel(
            f"<b>{entry.title or '(Untitled)'}</b><br>"
            f"<span style='color:{Color.TEXT_MUTED};'>{format_timestamp(entry.generated_at)}</span>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        inner_layout.addWidget(info, 1)

        open_file_button = SecondaryButton(OPEN_FILE_TEXT)
        open_file_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(entry.output_path)))
        inner_layout.addWidget(open_file_button)

        open_folder_button = SecondaryButton(OPEN_FOLDER_TEXT)
        open_folder_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(entry.output_path).parent)))
        )
        inner_layout.addWidget(open_folder_button)

        return row
