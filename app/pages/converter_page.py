"""ATS Data Converter page: import ATS xlsx files and export Standard Format CSVs."""
from __future__ import annotations

import datetime
import html
import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.converters.ats_parser import ATSParseError, ATSParseResult, parse_ats_file
from app.converters.flag_mapper import (
    FlagMappingResult,
    build_flag_mapping,
    check_team_flags,
    confirm_session_mappings,
)
from app.converters.team_parser import (
    TEAMConversionInput,
    TEAMParseError,
    TEAMParseResult,
    parse_team_file,
)
from app.converters.standard_format_writer import write_standard_format
from app.design.icons import icon
from app.design.tokens import Color, Radius, Spacing
from app.widgets import HelpPanel
from app.widgets.components import Card, PrimaryButton, SecondaryButton, StatCard
from app.widgets.flag_review_widget import FlagReviewWidget

logger = logging.getLogger(__name__)

TITLE_TEXT = "Data Converter"
BACK_TEXT = "← Back"
STATUS_HINT = "Tip: Import ATS inspection files to convert them to Standard Format CSV for TRACE."
HELP_TITLE = "Data Converter"
HELP_BODY = """
<p>The Data Converter transforms ATS inspection files into the Standard
Format CSV that TRACE accepts for data import.</p>
<p>Import one or more ATS <b>.xlsx</b> files. The converter reads all
inspection data, metadata, and flag codes automatically from each file.</p>
<p>If your files contain flag codes that are not in the auto-mapping list,
a review screen will appear so you can confirm or adjust the mapping
before converting.</p>
<p>One Standard Format CSV is produced per ATS file. Output files are
saved to your chosen output folder.</p>
<p><b>Keyboard shortcut:</b> Ctrl+T opens this page.</p>
"""

DROP_ZONE_TEXT = "Drop ATS .xlsx files here, or click to browse"
TEAM_DROP_ZONE_TEXT = (
    "Drop TEAM .xlsx files here, or click to browse. One batch = one "
    "inspection on one piece of equipment - company, mill, boiler, and "
    "date will apply to every file in this batch."
)
TEAM_DROP_ZONE_TOOLTIP = (
    "Drop one or more TEAM inspection .xlsx files here, or click to open a "
    "file browser. Every file in a batch shares the same company, mill, "
    "boiler, and inspection date."
)
CLEAR_ALL_TEXT = "Clear All"
OUTPUT_FOLDER_LABEL = "Output Folder"
BROWSE_TEXT = "Browse..."
CONVERT_ALL_TEXT = "Convert All"
OPEN_FOLDER_TEXT = "Open Output Folder"
CONVERT_MORE_TEXT = "Convert More Files"

OVERWRITE_TITLE = "Files Already Exist"
OVERWRITE_MESSAGE = (
    "The following file(s) already exist in the output folder:\n\n"
    "{names}\n\nOverwrite them?"
)
PERMISSION_ERROR_MESSAGE = (
    "Could not save {name} — it may be open in another program "
    "(such as Excel). Close it and try converting again."
)
OS_ERROR_MESSAGE = "Could not save {name}: {reason}"

_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

ATS_TAB_TEXT = "ATS Files"
TEAM_TAB_TEXT = "TEAM Files"
TDS_TAB_TEXT = "TDS Files"
COMING_SOON_TOOLTIP = "Coming soon"


def _output_filename(result: ATSParseResult) -> str:
    section = result.boiler_section.replace("/", "-").replace("\\", "-")
    return f"{section}_Standard_Format.csv"


def _default_section_name(filename: str) -> str:
    """Default per-file section name from a TEAM filename: drop the extension
    and turn underscores into spaces (the real files already use spaces, so
    that step is a no-op for them)."""
    return Path(filename).stem.replace("_", " ").strip()


class _AtsDropZone(QFrame):
    """Drop target for xlsx files. The default copy targets ATS; the TEAM view
    passes its own text/tooltip so the same widget serves both flows."""

    files_dropped = pyqtSignal(list)  # list of .xlsx file paths
    clicked = pyqtSignal()

    def __init__(
        self,
        parent=None,
        text: str = DROP_ZONE_TEXT,
        tooltip: str | None = None,
    ):
        super().__init__(parent)
        self._base_style = (
            f"QFrame {{ border: 2px dashed {Color.BORDER}; border-radius: 8px; "
            f"background: transparent; }}"
            f"QFrame:hover {{ border-color: {Color.ACCENT}; }}"
        )
        self._drag_style = (
            f"QFrame {{ border: 2px dashed {Color.ACCENT}; border-radius: 8px; "
            f"background: transparent; }}"
        )
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.setStyleSheet(self._base_style)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {Color.TEXT_MUTED};")
        layout.addWidget(lbl)

        self.setToolTip(
            tooltip
            if tooltip is not None
            else (
                "Drop one or more ATS inspection .xlsx files here, or click to "
                "open a file browser. You can import several files at once."
            )
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._drag_style)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._base_style)

    def dropEvent(self, event):
        self.setStyleSheet(self._base_style)
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        xlsx_paths = [p for p in paths if p.lower().endswith(".xlsx")]
        if xlsx_paths:
            self.files_dropped.emit(xlsx_paths)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _ConvertWorker(QThread):
    """Runs conversions on a background thread."""

    file_done = pyqtSignal(str, bool, str)  # path, success, error_message
    all_done = pyqtSignal()

    def __init__(
        self,
        jobs: list[tuple[str, ATSParseResult]],
        flag_mapping: dict[str, str],
        output_dir: Path,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._jobs = jobs
        self._flag_mapping = flag_mapping
        self._output_dir = output_dir

    def run(self) -> None:
        for source_path, result in self._jobs:
            out_name = _output_filename(result)
            out_path = self._output_dir / out_name
            try:
                write_standard_format(result, self._flag_mapping, out_path)
                self.file_done.emit(source_path, True, "")
            except PermissionError:
                message = PERMISSION_ERROR_MESSAGE.format(name=out_name)
                self.file_done.emit(source_path, False, message)
            except OSError as exc:
                message = OS_ERROR_MESSAGE.format(name=out_name, reason=exc.strerror or str(exc))
                self.file_done.emit(source_path, False, message)
            except Exception as exc:
                self.file_done.emit(source_path, False, str(exc))
        self.all_done.emit()


class _FileCard(Card):
    """One imported file shown in the file list."""

    remove_requested = pyqtSignal(str)  # path

    def __init__(self, path: str, result: ATSParseResult, parent: QWidget | None = None):
        super().__init__(parent)
        self._path = path
        self.layout().setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)

        row = QHBoxLayout()
        self.layout().addLayout(row)

        info = QVBoxLayout()
        name_lbl = QLabel(Path(path).name)
        name_lbl.setStyleSheet("font-weight: 600;")
        info.addWidget(name_lbl)
        detail = QLabel(
            f"{result.boiler_section} - "
            f"{result.num_tubes} tubes, "
            f"{len(result.elevations)} elevation{'s' if len(result.elevations) != 1 else ''}"
        )
        detail.setProperty("role", "muted")
        info.addWidget(detail)
        row.addLayout(info, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setProperty("flat", "true")
        remove_btn.setToolTip("Remove this file")
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._path))
        row.addWidget(remove_btn)


class _TeamFileCard(Card):
    """One imported TEAM file with an editable per-file section name."""

    remove_requested = pyqtSignal(str)           # path
    section_changed = pyqtSignal(str, str)       # path, new section name

    def __init__(
        self,
        path: str,
        result: TEAMParseResult,
        section_name: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._path = path
        self.layout().setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)

        row = QHBoxLayout()
        self.layout().addLayout(row)

        info = QVBoxLayout()
        name_lbl = QLabel(Path(path).name)
        name_lbl.setStyleSheet("font-weight: 600;")
        info.addWidget(name_lbl)

        flags = ", ".join(sorted(result.flags_found)) if result.flags_found else "none"
        elev_count = len(result.elevations)
        detail = QLabel(
            f"{result.num_tubes} tubes, {result.numbering_direction}, "
            f"{elev_count} elevation{'s' if elev_count != 1 else ''} - "
            f"flags: {flags}"
        )
        detail.setProperty("role", "muted")
        info.addWidget(detail)

        section_row = QHBoxLayout()
        section_lbl = QLabel("Section name:")
        section_lbl.setStyleSheet(f"color: {Color.TEXT_MUTED};")
        section_row.addWidget(section_lbl)
        self._section_edit = QLineEdit(section_name)
        self._section_edit.setToolTip(
            "Boiler section for this file. Used for the header and the output "
            "filename ({section}_Standard_Format.csv). Must not be empty."
        )
        self._section_edit.textChanged.connect(
            lambda text: self.section_changed.emit(self._path, text)
        )
        section_row.addWidget(self._section_edit, 1)
        info.addLayout(section_row)

        row.addLayout(info, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setProperty("flat", "true")
        remove_btn.setToolTip("Remove this file")
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._path))
        row.addWidget(remove_btn)


class _ErrorCard(QFrame):
    """An import error shown inline in the file list."""

    def __init__(self, path: str, error: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: {Color.CARD_BG}; border: 1px solid {Color.DANGER}; "
            f"border-radius: {Radius.CARD}px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        lbl = QLabel(f"<b>{html.escape(Path(path).name)}</b>: {html.escape(error)}")
        lbl.setStyleSheet(f"color: {Color.DANGER};")
        lbl.setWordWrap(True)
        layout.addWidget(lbl, 1)


class ConverterPage(QWidget):
    """ATS Data Converter page."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._imported: dict[str, ATSParseResult] = {}  # path -> result
        self._errors: dict[str, str] = {}               # path -> error message
        self._flag_mapping: dict[str, str] = {}
        self._flags_confirmed = False
        self._worker: Optional[_ConvertWorker] = None

        # TEAM flow state (kept fully separate from the ATS state above).
        self._team_imported: dict[str, TEAMParseResult] = {}
        self._team_errors: dict[str, str] = {}
        self._team_section_names: dict[str, str] = {}
        self._team_flag_mapping: dict[str, str] = {}
        self._team_flags_confirmed = False
        self._team_worker: Optional[_ConvertWorker] = None

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(main, 1)

        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

        # Header
        header_row = QHBoxLayout()
        back_btn = SecondaryButton(BACK_TEXT)
        back_btn.clicked.connect(self.back_requested.emit)
        header_row.addWidget(back_btn)
        header_row.addSpacing(Spacing.MD)
        title_icon = QLabel()
        title_icon.setPixmap(icon("arrows-left-right", color=Color.TEXT_PRIMARY).pixmap(20, 20))
        header_row.addWidget(title_icon)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        help_btn = QPushButton("?")
        help_btn.setFixedSize(28, 28)
        help_btn.setToolTip("Toggle help (F1)")
        help_btn.clicked.connect(self.help_panel.toggle)
        header_row.addWidget(help_btn)
        main_layout.addLayout(header_row)

        # Sub-navigation tabs (pill-style). The active/inactive stylesheet
        # strings are stored so tab switching can restyle the pills without
        # changing the ATS tab's original active appearance.
        self._active_tab_style = (
            f"QPushButton {{ background-color: {Color.ACCENT}; color: {Color.TEXT_PRIMARY}; "
            f"font-weight: 600; border: none; border-radius: {Radius.PILL}px; "
            f"padding: {Spacing.SM}px {Spacing.LG}px; }}"
        )
        self._inactive_tab_style = (
            f"QPushButton {{ background-color: transparent; color: {Color.TEXT_MUTED}; "
            f"border: 1px solid {Color.BORDER}; border-radius: {Radius.PILL}px; "
            f"padding: {Spacing.SM}px {Spacing.LG}px; }}"
        )

        tab_row = QHBoxLayout()
        self._ats_tab_btn = QPushButton(ATS_TAB_TEXT)
        self._ats_tab_btn.setStyleSheet(self._active_tab_style)
        self._ats_tab_btn.clicked.connect(self._show_ats_tab)
        tab_row.addWidget(self._ats_tab_btn)

        self._team_tab_btn = QPushButton(TEAM_TAB_TEXT)
        self._team_tab_btn.setStyleSheet(self._inactive_tab_style)
        self._team_tab_btn.clicked.connect(self._show_team_tab)
        tab_row.addWidget(self._team_tab_btn)

        self._tds_tab_btn = QPushButton(TDS_TAB_TEXT)
        self._tds_tab_btn.setEnabled(False)
        self._tds_tab_btn.setToolTip(COMING_SOON_TOOLTIP)
        self._tds_tab_btn.setStyleSheet(self._inactive_tab_style)
        tab_row.addWidget(self._tds_tab_btn)

        tab_row.addStretch(1)
        main_layout.addLayout(tab_row)

        # Stacked views: ATS flow (index 0) and TEAM placeholder (index 1).
        self._tab_stack = QStackedWidget()
        main_layout.addWidget(self._tab_stack, 1)

        # --- ATS view (index 0) ---
        ats_view = QWidget()
        ats_view_layout = QVBoxLayout(ats_view)
        ats_view_layout.setContentsMargins(0, 0, 0, 0)

        # Stat card row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(Spacing.MD)
        self._stat_files = StatCard(
            "Files loaded", "0",
            tooltip="Number of ATS files currently imported and ready to convert.",
        )
        self._stat_elevations = StatCard(
            "Elevations", "0",
            tooltip="Total inspection elevations found across all imported files.",
        )
        self._stat_flags = StatCard(
            "Flags needing review", "0",
            tooltip=(
                "ATS flag codes that could not be automatically matched to a "
                "Standard Format code and need your confirmation before converting."
            ),
        )
        stats_row.addWidget(self._stat_files)
        stats_row.addWidget(self._stat_elevations)
        stats_row.addWidget(self._stat_flags)
        ats_view_layout.addLayout(stats_row)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(Spacing.MD)
        scroll.setWidget(content)
        ats_view_layout.addWidget(scroll, 1)

        # Section 1: Import
        import_card = Card()
        import_layout = import_card.layout()

        import_header = QHBoxLayout()
        import_header.addWidget(QLabel("<b>Import ATS Files</b>"))
        import_header.addStretch(1)
        self._clear_all_btn = QPushButton(CLEAR_ALL_TEXT)
        self._clear_all_btn.setProperty("flat", "true")
        self._clear_all_btn.setToolTip("Remove every imported file and start over.")
        self._clear_all_btn.setEnabled(False)
        self._clear_all_btn.clicked.connect(self._on_clear_all)
        import_header.addWidget(self._clear_all_btn)
        import_layout.addLayout(import_header)

        self._drop_zone = _AtsDropZone(self)
        self._drop_zone.clicked.connect(self._on_browse_files)
        self._drop_zone.files_dropped.connect(
            lambda paths: [self._import_file(p) for p in paths]
        )
        import_layout.addWidget(self._drop_zone)

        self._file_list_layout = QVBoxLayout()
        self._file_list_layout.setSpacing(Spacing.SM)
        import_layout.addLayout(self._file_list_layout)

        self._content_layout.addWidget(import_card)

        # Section 2: Flag Review
        self._flag_widget_container = QWidget()
        self._flag_widget_layout = QVBoxLayout(self._flag_widget_container)
        self._flag_widget_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.addWidget(self._flag_widget_container)

        # Section 3: Output
        output_card = Card()
        output_layout = output_card.layout()
        output_layout.addWidget(QLabel("<b>Output</b>"))

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel(OUTPUT_FOLDER_LABEL))
        self._output_folder_edit = QLineEdit()
        self._output_folder_edit.setPlaceholderText("Choose output folder...")
        self._output_folder_edit.setReadOnly(True)
        self._output_folder_edit.setToolTip(
            "Where the converted Standard Format CSV files will be saved. "
            "Defaults to the folder of the first file you import; use Browse to change it."
        )
        saved = self._load_output_folder()
        self._output_folder_edit.setText(saved if saved else "")
        folder_row.addWidget(self._output_folder_edit, 1)
        browse_btn = SecondaryButton(BROWSE_TEXT)
        browse_btn.clicked.connect(self._on_browse_output)
        folder_row.addWidget(browse_btn)
        output_layout.addLayout(folder_row)

        self._convert_btn = PrimaryButton(CONVERT_ALL_TEXT)
        self._convert_btn.setIcon(icon("play", color=Color.TEXT_PRIMARY))
        self._convert_btn.setToolTip(
            "Convert every imported file to Standard Format CSV. Enabled once "
            "all flag codes above have been reviewed and confirmed."
        )
        self._convert_btn.setEnabled(False)
        self._convert_btn.clicked.connect(self._on_convert)
        output_layout.addWidget(self._convert_btn)

        self._content_layout.addWidget(output_card)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._content_layout.addWidget(self._progress_bar)

        # Results area
        self._results_layout = QVBoxLayout()
        self._content_layout.addLayout(self._results_layout)

        # Post-convert action buttons
        self._post_btn_row = QHBoxLayout()
        self._open_folder_btn = QPushButton(OPEN_FOLDER_TEXT)
        self._open_folder_btn.setProperty("flat", "true")
        self._open_folder_btn.setVisible(False)
        self._open_folder_btn.clicked.connect(self._on_open_output_folder)
        self._post_btn_row.addWidget(self._open_folder_btn)
        self._convert_more_btn = QPushButton(CONVERT_MORE_TEXT)
        self._convert_more_btn.setProperty("flat", "true")
        self._convert_more_btn.setVisible(False)
        self._convert_more_btn.clicked.connect(self._reset)
        self._post_btn_row.addWidget(self._convert_more_btn)
        self._post_btn_row.addStretch(1)
        self._content_layout.addLayout(self._post_btn_row)

        self._content_layout.addStretch(1)

        # Add the assembled ATS view as stack index 0.
        self._tab_stack.addWidget(ats_view)

        # --- TEAM view (index 1) ---
        self._team_view = QWidget()
        self._team_view_layout = QVBoxLayout(self._team_view)
        self._team_view_layout.setContentsMargins(0, 0, 0, 0)
        self._build_team_view()
        self._tab_stack.addWidget(self._team_view)

        # Start on the ATS tab (index 0, ATS pill active) - matches prior appearance.
        self._tab_stack.setCurrentIndex(0)

    # --- Sub-tab switching ---

    def _style_active_tab(self, active_btn: QPushButton, inactive_btns: list[QPushButton]) -> None:
        active_btn.setStyleSheet(self._active_tab_style)
        for btn in inactive_btns:
            btn.setStyleSheet(self._inactive_tab_style)

    def _show_ats_tab(self) -> None:
        self._tab_stack.setCurrentIndex(0)
        self._style_active_tab(self._ats_tab_btn, [self._team_tab_btn])

    def _show_team_tab(self) -> None:
        self._tab_stack.setCurrentIndex(1)
        self._style_active_tab(self._team_tab_btn, [self._ats_tab_btn])

    # --- Import ---

    def _on_browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import ATS Files", "", "ATS Inspection Files (*.xlsx)"
        )
        for path in paths:
            self._import_file(path)

    def _import_file(self, path: str) -> None:
        if path in self._imported or path in self._errors:
            return
        try:
            result = parse_ats_file(path)
            self._imported[path] = result
            # Set output folder to input file's parent on first import (if not already set)
            if len(self._imported) == 1 and not self._output_folder_edit.text():
                self._output_folder_edit.setText(str(Path(path).parent))
            card = _FileCard(path, result, self)
            card.remove_requested.connect(self._on_remove_file)
            self._file_list_layout.addWidget(card)
        except ATSParseError as exc:
            self._errors[path] = str(exc)
            self._file_list_layout.addWidget(_ErrorCard(path, str(exc), self))
        self._clear_all_btn.setEnabled(bool(self._imported) or bool(self._errors))
        self._flags_confirmed = False
        self._flag_mapping = {}
        self._update_file_stats()
        self._refresh_flag_widget()
        self._update_convert_button()

    def _on_remove_file(self, path: str) -> None:
        self._imported.pop(path, None)
        self._errors.pop(path, None)
        # Rebuild file list widgets
        while self._file_list_layout.count():
            item = self._file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for p, r in self._imported.items():
            card = _FileCard(p, r, self)
            card.remove_requested.connect(self._on_remove_file)
            self._file_list_layout.addWidget(card)
        for p, e in self._errors.items():
            self._file_list_layout.addWidget(_ErrorCard(p, e, self))
        self._clear_all_btn.setEnabled(bool(self._imported) or bool(self._errors))
        self._update_file_stats()
        self._refresh_flag_widget()
        self._update_convert_button()

    def _on_clear_all(self) -> None:
        self._imported.clear()
        self._errors.clear()
        while self._file_list_layout.count():
            item = self._file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._clear_all_btn.setEnabled(False)
        self._flags_confirmed = False
        self._flag_mapping = {}
        self._update_file_stats()
        self._refresh_flag_widget()
        self._update_convert_button()

    def _update_file_stats(self) -> None:
        self._stat_files.set_value(str(len(self._imported)))
        self._stat_elevations.set_value(
            str(sum(len(r.elevations) for r in self._imported.values()))
        )

    # --- Flag review ---

    def _refresh_flag_widget(self) -> None:
        while self._flag_widget_layout.count():
            item = self._flag_widget_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._imported:
            self._flags_confirmed = False
            self._flag_mapping = {}
            self._set_flags_needing_review(0)
            return

        all_flags: dict[str, str] = {}
        for result in self._imported.values():
            all_flags.update(result.ats_flags)

        mapping_result = build_flag_mapping(all_flags)
        self._set_flags_needing_review(len(mapping_result.unknown) + len(mapping_result.suggested))
        flag_widget = FlagReviewWidget(mapping_result, all_flags, self)
        flag_widget.mappings_confirmed.connect(self._on_flags_confirmed)
        self._flag_widget_layout.addWidget(flag_widget)

    def _set_flags_needing_review(self, count: int) -> None:
        value_color = Color.WARNING if count > 0 else Color.TEXT_PRIMARY
        self._stat_flags.set_value(str(count), color=value_color)

    def _on_flags_confirmed(self, mapping: dict[str, str]) -> None:
        all_flags: dict[str, str] = {}
        for result in self._imported.values():
            all_flags.update(result.ats_flags)
        confirm_session_mappings(mapping, all_flags)
        self._flag_mapping = mapping
        self._flags_confirmed = True
        self._update_convert_button()

    # --- Output ---

    def _on_browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self._output_folder_edit.text()
        )
        if folder:
            self._output_folder_edit.setText(folder)
            self._save_output_folder(folder)

    def _load_output_folder(self) -> str:
        settings = QSettings("BSI", "DATOToolkit")
        return settings.value("converter/last_output_folder", "")

    def _save_output_folder(self, folder: str) -> None:
        settings = QSettings("BSI", "DATOToolkit")
        settings.setValue("converter/last_output_folder", folder)

    def _update_convert_button(self) -> None:
        self._convert_btn.setEnabled(bool(self._imported) and self._flags_confirmed)

    # --- Conversion ---

    def _existing_output_paths(self, output_dir: Path, results=None) -> list[Path]:
        """Return output paths that already exist on disk for a batch.

        Defaults to the ATS imported results; the TEAM flow passes its own
        list of TEAMConversionInput objects (both are duck-typed via
        _output_filename)."""
        if results is None:
            results = self._imported.values()
        conflicts = []
        for result in results:
            out_path = output_dir / _output_filename(result)
            if out_path.exists():
                conflicts.append(out_path)
        return conflicts

    def _confirm_overwrite(self, conflicts: list[Path]) -> bool:
        """Show a single dialog listing all conflicting files. True if user chose to overwrite."""
        names = "\n".join(f"- {p.name}" for p in conflicts)
        box = QMessageBox(self)
        box.setWindowTitle(OVERWRITE_TITLE)
        box.setText(OVERWRITE_MESSAGE.format(names=names))
        overwrite_btn = box.addButton("Overwrite", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is overwrite_btn

    def _on_convert(self) -> None:
        output_dir = Path(self._output_folder_edit.text())
        self._save_output_folder(str(output_dir))
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create output folder: %s", exc)
            return

        conflicts = self._existing_output_paths(output_dir)
        if conflicts and not self._confirm_overwrite(conflicts):
            return

        jobs = list(self._imported.items())
        self._progress_bar.setMaximum(len(jobs))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._convert_btn.setEnabled(False)

        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._worker = _ConvertWorker(
            jobs,
            self._flag_mapping,
            output_dir,
            parent=self,
        )
        self._worker.file_done.connect(self._on_file_done)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_file_done(self, path: str, success: bool, error: str) -> None:
        self._progress_bar.setValue(self._progress_bar.value() + 1)
        status_icon = "✓" if success else "✗"
        style_color = Color.SUCCESS if success else Color.DANGER
        text = f"{status_icon} {Path(path).name}" + (f": {error}" if error else "")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {style_color};")
        self._results_layout.addWidget(lbl)

    def _on_all_done(self) -> None:
        self._progress_bar.setVisible(False)
        self._open_folder_btn.setVisible(True)
        self._convert_more_btn.setVisible(True)

    def _on_open_output_folder(self) -> None:
        folder = self._output_folder_edit.text()
        if folder:
            os.startfile(folder)  # Windows only

    def _reset(self) -> None:
        self._on_clear_all()
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._open_folder_btn.setVisible(False)
        self._convert_more_btn.setVisible(False)

    # ==================================================================
    # TEAM flow
    # ==================================================================

    def _build_team_view(self) -> None:
        """Populate self._team_view_layout with the full TEAM flow, mirroring
        the ATS view's structure and reusing the shared machinery."""
        # Stat card row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(Spacing.MD)
        self._team_stat_files = StatCard(
            "Files loaded", "0",
            tooltip="Number of TEAM files currently imported in this batch.",
        )
        self._team_stat_elevations = StatCard(
            "Elevations", "0",
            tooltip="Total inspection elevations found across all imported files.",
        )
        self._team_stat_flags = StatCard(
            "Flags needing review", "0",
            tooltip=(
                "Flag symbols in these files that are not recognized Standard "
                "Format symbols and need your confirmation before converting."
            ),
        )
        stats_row.addWidget(self._team_stat_files)
        stats_row.addWidget(self._team_stat_elevations)
        stats_row.addWidget(self._team_stat_flags)
        self._team_view_layout.addLayout(stats_row)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._team_content_layout = QVBoxLayout(content)
        self._team_content_layout.setSpacing(Spacing.MD)
        scroll.setWidget(content)
        self._team_view_layout.addWidget(scroll, 1)

        # Section 1: Import
        import_card = Card()
        import_layout = import_card.layout()
        import_header = QHBoxLayout()
        import_header.addWidget(QLabel("<b>Import TEAM Files</b>"))
        import_header.addStretch(1)
        self._team_clear_all_btn = QPushButton(CLEAR_ALL_TEXT)
        self._team_clear_all_btn.setProperty("flat", "true")
        self._team_clear_all_btn.setToolTip("Remove every imported file and start over.")
        self._team_clear_all_btn.setEnabled(False)
        self._team_clear_all_btn.clicked.connect(self._on_team_clear_all)
        import_header.addWidget(self._team_clear_all_btn)
        import_layout.addLayout(import_header)

        self._team_drop_zone = _AtsDropZone(
            self, text=TEAM_DROP_ZONE_TEXT, tooltip=TEAM_DROP_ZONE_TOOLTIP
        )
        self._team_drop_zone.clicked.connect(self._on_browse_team_files)
        self._team_drop_zone.files_dropped.connect(
            lambda paths: [self._import_team_file(p) for p in paths]
        )
        import_layout.addWidget(self._team_drop_zone)

        self._team_file_list_layout = QVBoxLayout()
        self._team_file_list_layout.setSpacing(Spacing.SM)
        import_layout.addLayout(self._team_file_list_layout)

        self._team_content_layout.addWidget(import_card)

        # Section 2: Batch metadata (hidden until >=1 file imported)
        self._team_metadata_card = Card()
        meta_layout = self._team_metadata_card.layout()
        meta_layout.addWidget(QLabel("<b>Inspection Details</b>"))
        meta_hint = QLabel(
            "These apply to every file in this batch."
        )
        meta_hint.setProperty("role", "muted")
        meta_layout.addWidget(meta_hint)

        self._team_company_edit = QLineEdit()
        self._team_company_edit.setPlaceholderText("e.g. Boiler Services and Inspection LLC")
        meta_layout.addLayout(self._team_labeled_field("Company Name", self._team_company_edit))

        self._team_mill_edit = QLineEdit()
        self._team_mill_edit.setPlaceholderText("e.g. Pine Bluff, AR")
        meta_layout.addLayout(self._team_labeled_field("Mill Location", self._team_mill_edit))

        self._team_boiler_edit = QLineEdit()
        self._team_boiler_edit.setPlaceholderText("e.g. No. 4 Recovery Boiler")
        meta_layout.addLayout(self._team_labeled_field("Boiler Name", self._team_boiler_edit))

        # Inspection Date = Month combo + Year combo
        date_row = QHBoxLayout()
        date_lbl = QLabel("Inspection Date")
        date_lbl.setMinimumWidth(120)
        date_row.addWidget(date_lbl)
        self._team_month_combo = QComboBox()
        self._team_month_combo.addItems(list(_MONTHS))
        self._team_month_combo.setToolTip("Month of the inspection.")
        date_row.addWidget(self._team_month_combo)
        self._team_year_combo = QComboBox()
        current_year = datetime.date.today().year
        for year in range(current_year + 1, current_year - 11, -1):
            self._team_year_combo.addItem(str(year))
        self._team_year_combo.setCurrentText(str(current_year))
        self._team_year_combo.setToolTip("Year of the inspection.")
        date_row.addWidget(self._team_year_combo)
        date_row.addStretch(1)
        meta_layout.addLayout(date_row)

        self._team_nde_edit = QLineEdit()
        self._team_nde_edit.setPlaceholderText("e.g. ATS")
        meta_layout.addLayout(self._team_labeled_field("NDE Laboratory", self._team_nde_edit))

        for edit in (
            self._team_company_edit,
            self._team_mill_edit,
            self._team_boiler_edit,
            self._team_nde_edit,
        ):
            edit.textChanged.connect(lambda _text: self._update_team_convert_button())
        self._team_month_combo.currentIndexChanged.connect(
            lambda _i: self._update_team_convert_button()
        )
        self._team_year_combo.currentIndexChanged.connect(
            lambda _i: self._update_team_convert_button()
        )

        self._team_metadata_card.setVisible(False)
        self._team_content_layout.addWidget(self._team_metadata_card)

        # Section 3: Flag review
        self._team_flag_widget_container = QWidget()
        self._team_flag_widget_layout = QVBoxLayout(self._team_flag_widget_container)
        self._team_flag_widget_layout.setContentsMargins(0, 0, 0, 0)
        self._team_content_layout.addWidget(self._team_flag_widget_container)

        # Section 4: Output
        output_card = Card()
        output_layout = output_card.layout()
        output_layout.addWidget(QLabel("<b>Output</b>"))

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel(OUTPUT_FOLDER_LABEL))
        self._team_output_folder_edit = QLineEdit()
        self._team_output_folder_edit.setPlaceholderText("Choose output folder...")
        self._team_output_folder_edit.setReadOnly(True)
        self._team_output_folder_edit.setToolTip(
            "Where the converted Standard Format CSV files will be saved. "
            "Defaults to the folder of the first file you import; use Browse to change it."
        )
        saved = self._load_output_folder()
        self._team_output_folder_edit.setText(saved if saved else "")
        folder_row.addWidget(self._team_output_folder_edit, 1)
        team_browse_btn = SecondaryButton(BROWSE_TEXT)
        team_browse_btn.clicked.connect(self._on_browse_team_output)
        folder_row.addWidget(team_browse_btn)
        output_layout.addLayout(folder_row)

        self._team_convert_btn = PrimaryButton(CONVERT_ALL_TEXT)
        self._team_convert_btn.setIcon(icon("play", color=Color.TEXT_PRIMARY))
        self._team_convert_btn.setToolTip(
            "Convert every imported file to Standard Format CSV. Enabled once "
            "all inspection details and section names are filled in and any "
            "flag codes have been reviewed."
        )
        self._team_convert_btn.setEnabled(False)
        self._team_convert_btn.clicked.connect(self._on_team_convert)
        output_layout.addWidget(self._team_convert_btn)

        self._team_content_layout.addWidget(output_card)

        # Progress
        self._team_progress_bar = QProgressBar()
        self._team_progress_bar.setVisible(False)
        self._team_content_layout.addWidget(self._team_progress_bar)

        # Results
        self._team_results_layout = QVBoxLayout()
        self._team_content_layout.addLayout(self._team_results_layout)

        # Post-convert actions
        self._team_post_btn_row = QHBoxLayout()
        self._team_open_folder_btn = QPushButton(OPEN_FOLDER_TEXT)
        self._team_open_folder_btn.setProperty("flat", "true")
        self._team_open_folder_btn.setVisible(False)
        self._team_open_folder_btn.clicked.connect(self._on_team_open_output_folder)
        self._team_post_btn_row.addWidget(self._team_open_folder_btn)
        self._team_convert_more_btn = QPushButton(CONVERT_MORE_TEXT)
        self._team_convert_more_btn.setProperty("flat", "true")
        self._team_convert_more_btn.setVisible(False)
        self._team_convert_more_btn.clicked.connect(self._team_reset)
        self._team_post_btn_row.addWidget(self._team_convert_more_btn)
        self._team_post_btn_row.addStretch(1)
        self._team_content_layout.addLayout(self._team_post_btn_row)

        self._team_content_layout.addStretch(1)

    def _team_labeled_field(self, label: str, field: QWidget) -> QHBoxLayout:
        """A left-aligned label + field row for the metadata form."""
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setMinimumWidth(120)
        row.addWidget(lbl)
        row.addWidget(field, 1)
        return row

    # --- TEAM import ---

    def _on_browse_team_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import TEAM Files", "", "TEAM Inspection Files (*.xlsx)"
        )
        for path in paths:
            self._import_team_file(path)

    def _import_team_file(self, path: str) -> None:
        if path in self._team_imported or path in self._team_errors:
            return
        try:
            result = parse_team_file(path)
            self._team_imported[path] = result
            section_name = _default_section_name(Path(path).name)
            self._team_section_names[path] = section_name
            if len(self._team_imported) == 1 and not self._team_output_folder_edit.text():
                self._team_output_folder_edit.setText(str(Path(path).parent))
            card = _TeamFileCard(path, result, section_name, self)
            card.remove_requested.connect(self._on_remove_team_file)
            card.section_changed.connect(self._on_team_section_changed)
            self._team_file_list_layout.addWidget(card)
        except TEAMParseError as exc:
            self._team_errors[path] = str(exc)
            self._team_file_list_layout.addWidget(_ErrorCard(path, str(exc), self))
        self._after_team_files_changed()

    def _on_remove_team_file(self, path: str) -> None:
        self._team_imported.pop(path, None)
        self._team_errors.pop(path, None)
        self._team_section_names.pop(path, None)
        self._rebuild_team_file_list()
        self._after_team_files_changed()

    def _on_team_clear_all(self) -> None:
        self._team_imported.clear()
        self._team_errors.clear()
        self._team_section_names.clear()
        self._clear_layout(self._team_file_list_layout)
        self._after_team_files_changed()

    def _rebuild_team_file_list(self) -> None:
        self._clear_layout(self._team_file_list_layout)
        for p, r in self._team_imported.items():
            section = self._team_section_names.get(p, _default_section_name(Path(p).name))
            card = _TeamFileCard(p, r, section, self)
            card.remove_requested.connect(self._on_remove_team_file)
            card.section_changed.connect(self._on_team_section_changed)
            self._team_file_list_layout.addWidget(card)
        for p, e in self._team_errors.items():
            self._team_file_list_layout.addWidget(_ErrorCard(p, e, self))

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _after_team_files_changed(self) -> None:
        """Shared bookkeeping after any change to the imported TEAM files."""
        self._team_clear_all_btn.setEnabled(
            bool(self._team_imported) or bool(self._team_errors)
        )
        self._team_flags_confirmed = False
        self._team_flag_mapping = {}
        self._update_team_file_stats()
        self._refresh_team_flag_widget()
        self._team_metadata_card.setVisible(bool(self._team_imported))
        self._update_team_convert_button()

    def _on_team_section_changed(self, path: str, text: str) -> None:
        self._team_section_names[path] = text
        self._update_team_convert_button()

    def _update_team_file_stats(self) -> None:
        self._team_stat_files.set_value(str(len(self._team_imported)))
        self._team_stat_elevations.set_value(
            str(sum(len(r.elevations) for r in self._team_imported.values()))
        )

    # --- TEAM flag review ---

    def _refresh_team_flag_widget(self) -> None:
        self._clear_layout(self._team_flag_widget_layout)
        if not self._team_imported:
            self._team_flags_confirmed = False
            self._team_flag_mapping = {}
            self._set_team_flags_needing_review(0)
            return

        all_flags: set[str] = set()
        for result in self._team_imported.values():
            all_flags |= result.flags_found

        mapping_result = check_team_flags(all_flags)
        self._set_team_flags_needing_review(
            len(mapping_result.unknown) + len(mapping_result.suggested)
        )
        flag_widget = FlagReviewWidget(mapping_result, None, self)
        flag_widget.mappings_confirmed.connect(self._on_team_flags_confirmed)
        self._team_flag_widget_layout.addWidget(flag_widget)

    def _set_team_flags_needing_review(self, count: int) -> None:
        value_color = Color.WARNING if count > 0 else Color.TEXT_PRIMARY
        self._team_stat_flags.set_value(str(count), color=value_color)

    def _on_team_flags_confirmed(self, mapping: dict[str, str]) -> None:
        self._team_flag_mapping = mapping
        self._team_flags_confirmed = True
        self._update_team_convert_button()

    # --- TEAM metadata / convert-button gating ---

    def _team_metadata_complete(self) -> bool:
        return all(
            (
                self._team_company_edit.text().strip(),
                self._team_mill_edit.text().strip(),
                self._team_boiler_edit.text().strip(),
                self._team_month_combo.currentText().strip(),
                self._team_year_combo.currentText().strip(),
                self._team_nde_edit.text().strip(),
            )
        )

    def _team_sections_complete(self) -> bool:
        if not self._team_imported:
            return False
        return all(
            self._team_section_names.get(path, "").strip()
            for path in self._team_imported
        )

    def _update_team_convert_button(self) -> None:
        ready = (
            bool(self._team_imported)
            and self._team_flags_confirmed
            and self._team_metadata_complete()
            and self._team_sections_complete()
        )
        self._team_convert_btn.setEnabled(ready)

    # --- TEAM output / conversion ---

    def _on_browse_team_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self._team_output_folder_edit.text()
        )
        if folder:
            self._team_output_folder_edit.setText(folder)
            self._save_output_folder(folder)

    def _team_conversion_inputs(self) -> list[tuple[str, TEAMConversionInput]]:
        """Build a (path, TEAMConversionInput) job for every imported file,
        applying the batch metadata to all and the per-file section name."""
        month = self._team_month_combo.currentText().strip()
        year = self._team_year_combo.currentText().strip()
        inspection_date = f"{month} {year}"
        company = self._team_company_edit.text().strip()
        mill = self._team_mill_edit.text().strip()
        boiler = self._team_boiler_edit.text().strip()
        nde = self._team_nde_edit.text().strip()

        jobs: list[tuple[str, TEAMConversionInput]] = []
        for path, result in self._team_imported.items():
            section = self._team_section_names.get(path, "").strip()
            jobs.append(
                (
                    path,
                    TEAMConversionInput(
                        company_name=company,
                        mill_location=mill,
                        boiler_name=boiler,
                        inspection_date=inspection_date,
                        boiler_section=section,
                        nde_laboratory=nde,
                        num_tubes=result.num_tubes,
                        numbering_direction=result.numbering_direction,
                        tube_numbers=result.tube_numbers,
                        elevations=result.elevations,
                    ),
                )
            )
        return jobs

    def _on_team_convert(self) -> None:
        output_dir = Path(self._team_output_folder_edit.text())
        self._save_output_folder(str(output_dir))
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create output folder: %s", exc)
            return

        jobs = self._team_conversion_inputs()
        conflicts = self._existing_output_paths(
            output_dir, [inp for _path, inp in jobs]
        )
        if conflicts and not self._confirm_overwrite(conflicts):
            return

        self._team_progress_bar.setMaximum(len(jobs))
        self._team_progress_bar.setValue(0)
        self._team_progress_bar.setVisible(True)
        self._team_convert_btn.setEnabled(False)

        self._clear_layout(self._team_results_layout)

        self._team_worker = _ConvertWorker(
            jobs,
            self._team_flag_mapping,
            output_dir,
            parent=self,
        )
        self._team_worker.file_done.connect(self._on_team_file_done)
        self._team_worker.all_done.connect(self._on_team_all_done)
        self._team_worker.start()

    def _on_team_file_done(self, path: str, success: bool, error: str) -> None:
        self._team_progress_bar.setValue(self._team_progress_bar.value() + 1)
        status_icon = "✓" if success else "✗"
        style_color = Color.SUCCESS if success else Color.DANGER
        text = f"{status_icon} {Path(path).name}" + (f": {error}" if error else "")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {style_color};")
        self._team_results_layout.addWidget(lbl)

    def _on_team_all_done(self) -> None:
        self._team_progress_bar.setVisible(False)
        self._team_open_folder_btn.setVisible(True)
        self._team_convert_more_btn.setVisible(True)

    def _on_team_open_output_folder(self) -> None:
        folder = self._team_output_folder_edit.text()
        if folder:
            os.startfile(folder)  # Windows only

    def _team_reset(self) -> None:
        self._on_team_clear_all()
        self._clear_layout(self._team_results_layout)
        self._team_open_folder_btn.setVisible(False)
        self._team_convert_more_btn.setVisible(False)
