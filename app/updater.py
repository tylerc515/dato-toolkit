"""Checks GitHub Releases for newer versions of the app, and manages update downloads."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from PyQt6.QtCore import QThread, pyqtSignal

GITHUB_RELEASES_API_URL = "https://api.github.com/repos/tylerc515/dato-toolkit/releases/latest"
GITHUB_RELEASES_PAGE_URL = "https://github.com/tylerc515/dato-toolkit/releases"
REQUEST_TIMEOUT_SECONDS = 5
DOWNLOAD_TIMEOUT_SECONDS = 30
DOWNLOAD_CHUNK_SIZE = 65536

logger = logging.getLogger(__name__)


@dataclass
class UpdateCheckResult:
    """Outcome of checking GitHub Releases for a newer version."""

    update_available: bool
    latest_version: Optional[str] = None
    current_version: Optional[str] = None
    error: bool = False
    release_notes: str = ""
    download_url: Optional[str] = None
    release_url: Optional[str] = None
    published_at: Optional[str] = None


def format_published_at(published_at: str) -> str:
    """Format an ISO8601 timestamp as 'Month D, YYYY'. Returns original string on failure."""
    if not published_at:
        return ""
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return f"{dt.strftime('%B')} {dt.day}, {dt.year}"
    except ValueError:
        return published_at


def _parse_version(tag: str) -> tuple[int, ...]:
    cleaned = tag.strip().lstrip("vV")
    parts: list[int] = []
    for part in cleaned.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update(current_version: str) -> UpdateCheckResult:
    """Compare the latest GitHub release against current_version.

    Network or parsing errors are logged and returned as error=True so
    callers can fail silently.
    """
    try:
        response = requests.get(GITHUB_RELEASES_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        tag = data.get("tag_name", "")
    except (requests.RequestException, ValueError) as exc:
        logger.info("Update check failed: %s", exc)
        return UpdateCheckResult(update_available=False, error=True, current_version=current_version)

    if not tag:
        return UpdateCheckResult(update_available=False, error=True, current_version=current_version)

    latest_version = tag.lstrip("vV")

    download_url: Optional[str] = None
    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(".exe"):
            download_url = asset.get("browser_download_url")
            break

    body = (data.get("body") or "").strip()
    release_notes = body if body else "No release notes provided for this version."

    published_at = data.get("published_at", "")
    release_url = data.get("html_url", "")

    available = _parse_version(tag) > _parse_version(current_version)
    logger.info(
        "Update check: current=%s latest=%s available=%s",
        current_version, latest_version, available,
    )
    return UpdateCheckResult(
        update_available=available,
        latest_version=latest_version,
        current_version=current_version,
        release_notes=release_notes,
        download_url=download_url,
        release_url=release_url,
        published_at=published_at,
    )


def write_update_bat(
    temp_download: Path,
    new_exe_dest: Path,
    current_exe: Path,
    remove_old: bool,
) -> Path:
    """Write a launcher .bat that moves the downloaded exe into place after the app exits.

    Uses `ping -n 3` as a 3-second sleep (works in hidden console; `timeout` does not).
    All paths are double-quoted so spaces are safe.
    Returns the path to the written .bat file.
    """
    fd, bat_path_str = tempfile.mkstemp(suffix=".bat", prefix="dato_update_")
    os.close(fd)
    bat_path = Path(bat_path_str)

    if remove_old and new_exe_dest.resolve() != current_exe.resolve():
        remove_line = f'del /F /Q "{current_exe}"'
    else:
        remove_line = "rem No removal requested"

    content = (
        "@echo off\n"
        "ping -n 3 127.0.0.1 > nul\n"
        f'move /Y "{temp_download}" "{new_exe_dest}"\n'
        "if errorlevel 1 (\n"
        "  echo Failed to move update file. 1>&2\n"
        "  exit /b 1\n"
        ")\n"
        f"{remove_line}\n"
        f'start "" "{new_exe_dest}"\n'
        'del "%~f0"\n'
    )
    bat_path.write_text(content, encoding="utf-8")
    return bat_path


def launch_update_bat(bat_path: Path) -> None:
    """Launch the installer batch file detached with no console window."""
    subprocess.Popen(
        ["cmd", "/C", str(bat_path)],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )


class DownloadWorker(QThread):
    """Downloads an update .exe to a temp file in the background."""

    progress = pyqtSignal(int, int, float)  # bytes_downloaded, total_bytes, speed_bps
    finished = pyqtSignal(str)              # local_path
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        fd, dest = tempfile.mkstemp(suffix=".exe", prefix="DATOToolkit_update_")
        os.close(fd)
        try:
            response = requests.get(self._url, stream=True, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            start_time = time.monotonic()

            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if self._cancel.is_set():
                        try:
                            Path(dest).unlink(missing_ok=True)
                        except OSError:
                            pass
                        self.cancelled.emit()
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.monotonic() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0.0
                        self.progress.emit(downloaded, total, speed)

            logger.info("Download complete: %s (%d bytes)", dest, downloaded)
            self.finished.emit(dest)
        except Exception as exc:
            logger.exception("Download failed: %s", exc)
            try:
                Path(dest).unlink(missing_ok=True)
            except OSError:
                pass
            self.failed.emit(str(exc))


class UpdateCheckWorker(QThread):
    """Runs check_for_update on a background thread so it never blocks the UI."""

    check_finished = pyqtSignal(object)  # UpdateCheckResult

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current_version = current_version

    def run(self) -> None:
        self.check_finished.emit(check_for_update(self._current_version))
