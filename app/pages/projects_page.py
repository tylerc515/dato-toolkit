"""Full list of saved projects, most recently modified first."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.history import format_timestamp
from app.project import ProjectConfig, list_projects
from app.search import matches_search
from app.styles import apply_card_shadow, color

# --- UI text -------------------------------------------------------------

TITLE_TEXT = "All Projects"
BACK_TEXT = "← Back"
NO_PROJECTS_TEXT = "No saved projects yet."
NO_MATCHES_TEXT = "No projects match your search."
OPEN_TEXT = "Open"
SEARCH_PLACEHOLDER = "Search by title, customer, location, or equipment…"
STATUS_HINT = "Tip: Search your saved projects and reopen one to continue editing."


class ProjectsPage(QWidget):
    """Full list of saved projects, most recently modified first."""

    back_requested = pyqtSignal()
    project_selected = pyqtSignal(Path)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._projects: list[tuple[Path, ProjectConfig]] = []
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

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(SEARCH_PLACEHOLDER)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        outer.addWidget(self.search_edit)

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
        """Reload the full project list from disk."""
        self._projects = list_projects()
        self._apply_filter()

    def _apply_filter(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        query = self.search_edit.text()
        projects = [
            (path, config)
            for path, config in self._projects
            if matches_search(query, config.title, config.customer, config.location, config.equipment, config.date)
        ]

        if not projects:
            empty_label = QLabel(NO_PROJECTS_TEXT if not self._projects else NO_MATCHES_TEXT)
            empty_label.setProperty("role", "muted")
            self._list_layout.addWidget(empty_label)
        else:
            for path, config in projects:
                self._list_layout.addWidget(self._make_project_row(path, config))

        self._list_layout.addStretch(1)

    def _make_project_row(self, path: Path, config: ProjectConfig) -> QWidget:
        row = QFrame()
        row.setProperty("card", "true")
        apply_card_shadow(row)
        layout = QHBoxLayout(row)

        subtitle = " — ".join(part for part in (config.customer, config.location, config.equipment, config.date) if part)
        info = QLabel(
            f"<b>{config.title or '(Untitled)'}</b><br>"
            f"<span style='color:{color('muted_text')};'>"
            f"{subtitle} &nbsp;&middot;&nbsp; "
            f"Last modified {format_timestamp(config.last_modified)}</span>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info, 1)

        open_button = QPushButton(OPEN_TEXT)
        open_button.setProperty("flat", "true")
        open_button.clicked.connect(lambda: self.project_selected.emit(path))
        layout.addWidget(open_button)

        return row
