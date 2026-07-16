"""ATS Data Converter page: import ATS xlsx files and export Standard Format CSVs."""
from __future__ import annotations

import html
import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.converters.ats_parser import ATSParseError, ATSParseResult, parse_ats_file
from app.converters.flag_mapper import (
    FlagMappingResult,
    build_flag_mapping,
    confirm_session_mappings,
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

ATS_TAB_TEXT = "ATS Files"
TEAM_TAB_TEXT = "TEAM Files"
TDS_TAB_TEXT = "TDS Files"
COMING_SOON_TOOLTIP = "Coming soon"


def _output_filename(result: ATSParseResult) -> str:
    section = result.boiler_section.replace("/", "-").replace("\\", "-")
    return f"{section}_Standard_Format.csv"


class _AtsDropZone(QFrame):
    """Drop target for ATS xlsx files."""

    files_dropped = pyqtSignal(list)  # list of .xlsx file paths
    clicked = pyqtSignal()

    def __init__(self, parent=None):
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
        lbl = QLabel(DROP_ZONE_TEXT)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {Color.TEXT_MUTED};")
        layout.addWidget(lbl)

        self.setToolTip(
            "Drop one or more ATS inspection .xlsx files here, or click to "
            "open a file browser. You can import several files at once."
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

        # Sub-navigation tabs (pill-style)
        tab_row = QHBoxLayout()
        ats_tab = QPushButton(ATS_TAB_TEXT)
        ats_tab.setStyleSheet(
            f"QPushButton {{ background-color: {Color.ACCENT}; color: {Color.TEXT_PRIMARY}; "
            f"font-weight: 600; border: none; border-radius: {Radius.PILL}px; "
            f"padding: {Spacing.SM}px {Spacing.LG}px; }}"
        )
        tab_row.addWidget(ats_tab)
        for tab_text in (TEAM_TAB_TEXT, TDS_TAB_TEXT):
            btn = QPushButton(tab_text)
            btn.setEnabled(False)
            btn.setToolTip(COMING_SOON_TOOLTIP)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {Color.TEXT_MUTED}; "
                f"border: 1px solid {Color.BORDER}; border-radius: {Radius.PILL}px; "
                f"padding: {Spacing.SM}px {Spacing.LG}px; }}"
            )
            tab_row.addWidget(btn)
        tab_row.addStretch(1)
        main_layout.addLayout(tab_row)

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
        main_layout.addLayout(stats_row)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(Spacing.MD)
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

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

    def _existing_output_paths(self, output_dir: Path) -> list[Path]:
        """Return output paths that already exist on disk for the current batch."""
        conflicts = []
        for result in self._imported.values():
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
