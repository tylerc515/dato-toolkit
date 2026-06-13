"""Checks GitHub Releases for newer versions of the app."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests
from PyQt6.QtCore import QThread, pyqtSignal

GITHUB_RELEASES_API_URL = "https://api.github.com/repos/tylerc515/trace-tracker-builder/releases/latest"
GITHUB_RELEASES_PAGE_URL = "https://github.com/tylerc515/trace-tracker-builder/releases"
REQUEST_TIMEOUT_SECONDS = 5

logger = logging.getLogger(__name__)


@dataclass
class UpdateCheckResult:
    """Outcome of checking GitHub Releases for a newer version."""

    update_available: bool
    latest_version: Optional[str] = None
    error: bool = False


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
    """Compare the latest GitHub release tag against current_version.

    Network or parsing errors are logged and reported as UpdateCheckResult(error=True)
    so the caller can fail silently.
    """
    try:
        response = requests.get(GITHUB_RELEASES_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        tag = response.json().get("tag_name", "")
    except (requests.RequestException, ValueError) as exc:
        logger.info("Update check failed: %s", exc)
        return UpdateCheckResult(update_available=False, error=True)

    if not tag:
        return UpdateCheckResult(update_available=False, error=True)

    latest_version = tag.lstrip("vV")
    if _parse_version(tag) > _parse_version(current_version):
        return UpdateCheckResult(update_available=True, latest_version=latest_version)
    return UpdateCheckResult(update_available=False, latest_version=latest_version)


class UpdateCheckWorker(QThread):
    """Runs check_for_update on a background thread so it never blocks the UI."""

    check_finished = pyqtSignal(object)  # UpdateCheckResult

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current_version = current_version

    def run(self) -> None:
        self.check_finished.emit(check_for_update(self._current_version))
