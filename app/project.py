"""Save/load project configuration as JSON in the user's app-data directory."""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

APP_DIR_NAME = "DATOToolkit"
_LEGACY_DIR_NAME = "TraceTrackerBuilder"
PROJECT_CONFIG_VERSION = "1.0"
FUZZY_MATCH_THRESHOLD = 0.6

logger = logging.getLogger(__name__)


class ProjectError(Exception):
    """Raised when a project config cannot be read or written."""


def _migrate_legacy_data() -> None:
    """Copy data from the old TraceTrackerBuilder directory to DATOToolkit on first run."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path.home() / ".config"

    old_path = base / _LEGACY_DIR_NAME
    new_path = base / APP_DIR_NAME

    if old_path.exists() and not new_path.exists():
        try:
            shutil.copytree(old_path, new_path)
            logger.info("Migrated app data from %s to %s", old_path, new_path)
        except OSError:
            logger.warning("Could not migrate data from %s to %s", old_path, new_path)


def get_app_data_dir() -> Path:
    """Return the per-user application data directory, creating it if needed."""
    _migrate_legacy_data()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
        path = base / APP_DIR_NAME
    else:
        path = Path.home() / ".config" / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_projects_dir() -> Path:
    path = get_app_data_dir() / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str) -> str:
    """Make a string safe to use as a filename, e.g. for project configs."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name)
    cleaned = re.sub(r"\s+", "_", cleaned.strip())
    return cleaned or "project"


@dataclass
class ProjectSection:
    """A single section's source file, display name, and elevation list."""

    name: str
    file_path: str
    display_name: str
    elevations: list[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    """Persisted state for one tracker project."""

    version: str = PROJECT_CONFIG_VERSION
    title: str = ""
    customer: str = ""
    location: str = ""
    equipment: str = ""
    date: str = ""
    sections: list[ProjectSection] = field(default_factory=list)
    output_directory: str = ""
    output_filename: str = ""
    export_pdf: bool = False
    last_modified: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        sections = [
            ProjectSection(
                name=s.get("name", ""),
                file_path=s.get("file_path", ""),
                display_name=s.get("display_name", s.get("name", "")),
                elevations=list(s.get("elevations", [])),
            )
            for s in data.get("sections", [])
        ]
        return cls(
            version=data.get("version", PROJECT_CONFIG_VERSION),
            title=data.get("title", ""),
            customer=data.get("customer", ""),
            location=data.get("location", ""),
            equipment=data.get("equipment", ""),
            date=data.get("date", ""),
            sections=sections,
            output_directory=data.get("output_directory", ""),
            output_filename=data.get("output_filename", ""),
            export_pdf=bool(data.get("export_pdf", False)),
            last_modified=data.get("last_modified", ""),
        )

    def save(self, path: Optional[Path] = None) -> Path:
        """Write this config to disk, defaulting to a path derived from the title."""
        if path is None:
            path = get_projects_dir() / f"{sanitize_filename(self.title)}.json"
        self.last_modified = datetime.now().isoformat()
        try:
            path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        except OSError as exc:
            raise ProjectError(f"Could not save project file '{path}': {exc}") from exc
        return path


def load_project(path: Path) -> ProjectConfig:
    """Load a project config from disk."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectError(f"Could not load project file '{path}': {exc}") from exc
    return ProjectConfig.from_dict(data)


def list_projects() -> list[tuple[Path, "ProjectConfig"]]:
    """Return all saved projects with their file paths, most recently modified first."""
    results: list[tuple[Path, ProjectConfig]] = []
    for path in get_projects_dir().glob("*.json"):
        try:
            config = load_project(path)
        except ProjectError:
            continue
        results.append((path, config))
    results.sort(key=lambda item: item[1].last_modified, reverse=True)
    return results


def find_project_for_metadata(customer: str, location: str, equipment: str, date: str) -> Optional[Path]:
    """Return the path of a saved project matching the given metadata, if any."""
    for path in get_projects_dir().glob("*.json"):
        try:
            config = load_project(path)
        except ProjectError:
            continue
        if (config.customer, config.location, config.equipment, config.date) == (customer, location, equipment, date):
            return path
    return None


def _metadata_key(customer: str, location: str, equipment: str, date: str) -> str:
    return "|".join((customer, location, equipment, date)).strip().lower()


def find_similar_project_for_metadata(customer: str, location: str, equipment: str, date: str) -> Optional[Path]:
    """Return the path of a saved project with similar (but not identical) metadata, if any.

    Useful when a TRACE export has minor differences from a previous run (e.g. a typo
    fix or reformatted date) but is otherwise the same project.
    """
    target = _metadata_key(customer, location, equipment, date)
    best_path: Optional[Path] = None
    best_ratio = 0.0
    for path in get_projects_dir().glob("*.json"):
        try:
            config = load_project(path)
        except ProjectError:
            continue
        key = _metadata_key(config.customer, config.location, config.equipment, config.date)
        if key == target:
            continue
        ratio = difflib.SequenceMatcher(None, target, key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_path = path
    if best_ratio >= FUZZY_MATCH_THRESHOLD:
        return best_path
    return None
