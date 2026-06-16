"""Update dialog: release notes viewer, install options, background download."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.logo import get_pixmap
from app.project import APP_DIR_NAME
from app.updater import (
    GITHUB_RELEASES_PAGE_URL,
    DownloadWorker,
    UpdateCheckResult,
    format_published_at,
    launch_update_bat,
    write_update_bat,
)

logger = logging.getLogger(__name__)

IS_FROZEN = getattr(sys, "frozen", False)

_BG = "#1a1a2e"
_SURFACE = "#16213e"
_BORDER = "#2c3759"
_NOTES_BG = "#0d1117"
_NOTES_TEXT = "#eaeaea"
_MUTED = "#9aa0b4"
_ACCENT_RED = "#e94560"
_ACCENT_GREEN = "#00B050"

PENDING_KEY_TEMP = "pending_update/temp_path"
PENDING_KEY_DEST = "pending_update/dest_path"

_DEV_MODE_MSG = (
    "Auto-update is only available when running the installed .exe. "
    "Download manually from GitHub."
)
_NO_ASSET_MSG = (
    "No installer found for this release. "
    "Visit GitHub to download manually."
)
_NOT_WRITABLE_MSG = (
    "Cannot write to that folder. "
    "Choose a different location or run as administrator."
)


class _MarkdownConverter:
    """Converts a subset of Markdown to HTML for QTextBrowser display."""

    @staticmethod
    def to_html(text: str) -> str:
        lines = text.splitlines()
        parts: list[str] = []
        in_ul = False

        for line in lines:
            stripped = line.rstrip()
            if stripped.startswith("## "):
                if in_ul:
                    parts.append("</ul>")
                    in_ul = False
                heading = _MarkdownConverter._inline(stripped[3:].strip())
                parts.append(
                    f'<h3 style="color:{_NOTES_TEXT};font-size:12pt;'
                    f'font-weight:bold;margin-top:8px;margin-bottom:4px;">'
                    f"{heading}</h3>"
                )
            elif stripped.startswith("- "):
                if not in_ul:
                    parts.append('<ul style="padding-left:20px;margin:0;padding-top:4px;">')
                    in_ul = True
                item = _MarkdownConverter._inline(stripped[2:].strip())
                parts.append(f"<li>{item}</li>")
            elif stripped == "":
                if in_ul:
                    parts.append("</ul>")
                    in_ul = False
                parts.append("<br>")
            else:
                if in_ul:
                    parts.append("</ul>")
                    in_ul = False
                parts.append(
                    f'<p style="margin:2px 0;">{_MarkdownConverter._inline(stripped)}</p>'
                )

        if in_ul:
            parts.append("</ul>")

        return "\n".join(parts)

    @staticmethod
    def _inline(text: str) -> str:
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


class UpdateDialog(QDialog):
    """Modal dialog showing release notes, install options, and download progress."""

    def __init__(self, update_info: UpdateCheckResult, parent=None):
        super().__init__(parent)
        self._info = update_info
        self._worker: Optional[DownloadWorker] = None
        self._downloaded_path: Optional[Path] = None
        self._install_dir: Optional[Path] = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(620, 520)
        self.setStyleSheet(f"QDialog {{ background-color: {_BG}; }}")
        self.setModal(True)

        if parent is not None:
            g = parent.geometry()
            self.move(g.x() + (g.width() - 620) // 2, g.y() + (g.height() - 520) // 2)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        root.addWidget(self._build_notes_section(), 1)
        root.addWidget(self._build_install_section())
        root.addWidget(self._build_progress_section())
        root.addWidget(self._build_action_section())

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setStyleSheet(
            f"QFrame {{ background-color: {_SURFACE}; "
            f"border-bottom: 1px solid {_BORDER}; }}"
        )
        header.setFixedHeight(80)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)

        logo = QLabel()
        logo.setPixmap(get_pixmap(48, 28))
        layout.addWidget(logo)
        layout.addSpacing(12)

        info_col = QVBoxLayout()
        title_lbl = QLabel("DATO Toolkit Update Available")
        title_lbl.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {_NOTES_TEXT};")
        info_col.addWidget(title_lbl)

        current = self._info.current_version or "?"
        latest = self._info.latest_version or "?"
        ver_lbl = QLabel(f"{current} → {latest}")
        ver_lbl.setStyleSheet(f"font-size: 12pt; color: {_MUTED};")
        info_col.addWidget(ver_lbl)

        if self._info.published_at:
            date_lbl = QLabel(f"Released {format_published_at(self._info.published_at)}")
            date_lbl.setStyleSheet(f"font-size: 11pt; color: {_MUTED};")
            info_col.addWidget(date_lbl)

        layout.addLayout(info_col, 1)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"color: {_MUTED}; font-size: 18pt; }}"
            f"QPushButton:hover {{ color: {_ACCENT_RED}; }}"
        )
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        return header

    def _build_notes_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(6)

        latest = self._info.latest_version or "?"
        label = QLabel(f"What's New in {latest}")
        label.setStyleSheet(f"font-size: 10pt; font-weight: bold; color: {_MUTED};")
        layout.addWidget(label)

        self._notes_browser = QTextBrowser()
        self._notes_browser.setOpenExternalLinks(True)
        self._notes_browser.setStyleSheet(
            f"QTextBrowser {{ background: {_NOTES_BG}; color: {_NOTES_TEXT}; "
            f"border: none; padding: 12px; font-family: 'Segoe UI'; font-size: 11pt; }}"
            f"QScrollBar:vertical {{ background: {_BG}; width: 8px; }}"
            f"QScrollBar::handle:vertical {{ background: {_BORDER}; border-radius: 4px; }}"
        )
        notes = self._info.release_notes or "No release notes provided for this version."
        self._notes_browser.setHtml(_MarkdownConverter.to_html(notes))
        layout.addWidget(self._notes_browser)
        return container

    def _build_install_section(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {_SURFACE}; "
            f"border-top: 1px solid {_BORDER}; border-bottom: 1px solid {_BORDER}; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        loc_row = QHBoxLayout()
        loc_lbl = QLabel("Install Location")
        loc_lbl.setStyleSheet(f"color: {_NOTES_TEXT};")
        loc_row.addWidget(loc_lbl)
        self._folder_edit = QLineEdit(self._default_install_dir())
        loc_row.addWidget(self._folder_edit, 1)
        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(36)
        browse_btn.setToolTip("Choose install folder")
        browse_btn.clicked.connect(self._browse_folder)
        loc_row.addWidget(browse_btn)
        layout.addLayout(loc_row)

        fn_row = QHBoxLayout()
        fn_lbl = QLabel("New filename")
        fn_lbl.setStyleSheet(f"color: {_NOTES_TEXT};")
        fn_row.addWidget(fn_lbl)
        new_name = f"DATOToolkit_{self._info.latest_version or 'update'}.exe"
        self._filename_edit = QLineEdit(new_name)
        self._filename_edit.setReadOnly(True)
        self._filename_edit.setStyleSheet(f"color: {_MUTED};")
        fn_row.addWidget(self._filename_edit, 1)
        layout.addLayout(fn_row)

        current_name = Path(sys.executable).name if IS_FROZEN else "DATOToolkit.exe"
        self._remove_checkbox = QCheckBox(
            f"Delete {current_name} after installing new version"
        )
        self._remove_checkbox.setChecked(True)
        self._remove_checkbox.setStyleSheet(f"color: {_NOTES_TEXT};")
        layout.addWidget(self._remove_checkbox)

        helper = QLabel(
            "The old file will only be removed after the new version launches successfully."
        )
        helper.setStyleSheet(f"font-size: 9pt; font-style: italic; color: {_MUTED};")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        return card

    def _build_progress_section(self) -> QWidget:
        self._progress_container = QWidget()
        self._progress_container.setVisible(False)
        layout = QVBoxLayout(self._progress_container)
        layout.setContentsMargins(16, 8, 16, 4)
        layout.setSpacing(4)

        self._progress_label = QLabel("Preparing download…")
        self._progress_label.setStyleSheet(f"color: {_NOTES_TEXT};")
        layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{ background: {_NOTES_BG}; border-radius: 4px; height: 12px; text-align: center; }}"
            "QProgressBar::chunk { background: #2f80ed; border-radius: 4px; }"
        )
        layout.addWidget(self._progress_bar)

        self._speed_label = QLabel("")
        self._speed_label.setStyleSheet(f"font-size: 9pt; color: {_MUTED};")
        layout.addWidget(self._speed_label)

        cancel_row = QHBoxLayout()
        cancel_row.addStretch(1)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("flat", "true")
        self._cancel_btn.setStyleSheet(f"color: {_MUTED};")
        self._cancel_btn.clicked.connect(self._on_cancel_download)
        cancel_row.addWidget(self._cancel_btn)
        layout.addLayout(cancel_row)

        return self._progress_container

    def _build_action_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        self._download_btn = QPushButton("Download & Install")
        self._download_btn.setStyleSheet(
            f"QPushButton {{ background: {_ACCENT_RED}; color: white; font-weight: bold; "
            f"border-radius: 6px; padding: 10px; font-size: 12pt; }}"
            f"QPushButton:hover {{ background: #ff5c75; }}"
            f"QPushButton:disabled {{ background: #5b3641; color: {_MUTED}; }}"
        )
        self._download_btn.clicked.connect(self._on_download_clicked)
        layout.addWidget(self._download_btn)

        self._install_btn = QPushButton("Install Now & Restart")
        self._install_btn.setStyleSheet(
            f"QPushButton {{ background: {_ACCENT_GREEN}; color: white; font-weight: bold; "
            f"border-radius: 6px; padding: 10px; font-size: 12pt; }}"
            f"QPushButton:hover {{ background: #00c85a; }}"
        )
        self._install_btn.clicked.connect(self._on_install_now)
        self._install_btn.setVisible(False)
        layout.addWidget(self._install_btn)

        bottom_row = QHBoxLayout()
        view_btn = QPushButton("View on GitHub")
        view_btn.setProperty("flat", "true")
        view_btn.setStyleSheet(f"color: {_MUTED};")
        view_btn.clicked.connect(self._open_github)
        bottom_row.addWidget(view_btn)
        bottom_row.addStretch(1)
        self._later_btn = QPushButton("Install Later")
        self._later_btn.setProperty("flat", "true")
        self._later_btn.setStyleSheet(f"color: {_MUTED};")
        self._later_btn.clicked.connect(self._on_install_later)
        self._later_btn.setVisible(False)
        bottom_row.addWidget(self._later_btn)
        layout.addLayout(bottom_row)

        if not IS_FROZEN:
            self._download_btn.setEnabled(False)
            self._download_btn.setToolTip(_DEV_MODE_MSG)
        elif not self._info.download_url:
            self._download_btn.setEnabled(False)
            self._download_btn.setToolTip(_NO_ASSET_MSG)

        return container

    def _default_install_dir(self) -> str:
        if IS_FROZEN:
            return str(Path(sys.executable).parent)
        return str(Path.home() / "Downloads")

    def _browse_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Choose install folder", self._folder_edit.text()
        )
        if directory:
            self._folder_edit.setText(directory)

    def _open_github(self) -> None:
        url = self._info.release_url or GITHUB_RELEASES_PAGE_URL
        QDesktopServices.openUrl(QUrl(url))

    def _on_download_clicked(self) -> None:
        install_dir = Path(self._folder_edit.text().strip())

        if not os.access(str(install_dir), os.W_OK):
            QMessageBox.warning(self, "Cannot Write to Folder", _NOT_WRITABLE_MSG)
            return

        stat = shutil.disk_usage(str(install_dir))
        if stat.free < 200 * 1024 * 1024:
            avail_mb = stat.free // (1024 * 1024)
            QMessageBox.warning(
                self, "Low Disk Space",
                f"Not enough disk space available in {install_dir}.\n"
                f"Available: {avail_mb} MB. At least 200 MB is needed."
            )
            return

        self._install_dir = install_dir
        self._download_btn.setVisible(False)
        self._progress_container.setVisible(True)
        self._progress_label.setText(f"Downloading {self._filename_edit.text()}…")

        self._worker = DownloadWorker(self._info.download_url)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_download_finished)
        self._worker.failed.connect(self._on_download_failed)
        self._worker.cancelled.connect(self._on_download_cancelled)
        self._worker.start()
        logger.info("Download started: %s", self._info.download_url)

    def _on_progress(self, downloaded: int, total: int, speed: float) -> None:
        if total > 0:
            pct = int(downloaded * 100 / total)
            self._progress_bar.setValue(pct)
            dl_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            speed_mb = speed / (1024 * 1024)
            self._speed_label.setText(
                f"{dl_mb:.1f} MB of {total_mb:.1f} MB — {speed_mb:.2f} MB/s"
            )
        else:
            dl_mb = downloaded / (1024 * 1024)
            self._speed_label.setText(f"{dl_mb:.1f} MB downloaded")

    def _on_download_finished(self, local_path: str) -> None:
        self._downloaded_path = Path(local_path)
        logger.info("Download complete: %s (%d bytes)", local_path, self._downloaded_path.stat().st_size)
        self._progress_container.setVisible(False)
        self._install_btn.setVisible(True)
        self._later_btn.setVisible(True)

    def _on_download_failed(self, message: str) -> None:
        logger.error("Download failed: %s", message)
        self._progress_container.setVisible(False)
        self._download_btn.setVisible(True)
        QMessageBox.critical(self, "Download Failed", f"Download failed:\n{message}")

    def _on_download_cancelled(self) -> None:
        self._progress_container.setVisible(False)
        self._download_btn.setVisible(True)

    def _on_cancel_download(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _on_install_now(self) -> None:
        if self._downloaded_path is None or self._install_dir is None:
            return

        new_name = self._filename_edit.text().strip()
        new_exe_dest = self._install_dir / new_name
        remove_old = self._remove_checkbox.isChecked()
        current_exe = Path(sys.executable) if IS_FROZEN else Path.cwd() / "main.exe"

        if new_exe_dest.resolve() == current_exe.resolve() and remove_old:
            reply = QMessageBox.question(
                self, "Confirm Update",
                "The new version will replace the current file. "
                "The old version cannot be separately removed in this case. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            remove_old = False

        try:
            bat_path = write_update_bat(
                temp_download=self._downloaded_path,
                new_exe_dest=new_exe_dest,
                current_exe=current_exe,
                remove_old=remove_old,
            )
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Could not write update launcher:\n{exc}")
            return

        logger.info(
            "Launching update bat: %s → %s (remove_old=%s)", self._downloaded_path, new_exe_dest, remove_old
        )
        launch_update_bat(bat_path)
        QApplication.quit()

    def _on_install_later(self) -> None:
        if self._downloaded_path is None or self._install_dir is None:
            return
        new_exe_dest = self._install_dir / self._filename_edit.text().strip()
        settings = QSettings(APP_DIR_NAME, APP_DIR_NAME)
        settings.setValue(PENDING_KEY_TEMP, str(self._downloaded_path))
        settings.setValue(PENDING_KEY_DEST, str(new_exe_dest))
        logger.info("Install Later: pending update saved to QSettings")
        self.accept()
