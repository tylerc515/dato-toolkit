"""Track generated-tracker history as JSON in the user's app-data directory."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from app.project import get_app_data_dir

HISTORY_FILENAME = "history.json"
MAX_HISTORY_ENTRIES = 200
NEVER_TEXT = "—"

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """A record of one tracker generation."""

    title: str
    customer: str
    location: str
    equipment: str
    date: str
    elevation_count: int
    output_path: str
    pdf_path: str = ""
    generated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            title=data.get("title", ""),
            customer=data.get("customer", ""),
            location=data.get("location", ""),
            equipment=data.get("equipment", ""),
            date=data.get("date", ""),
            elevation_count=int(data.get("elevation_count", 0)),
            output_path=data.get("output_path", ""),
            pdf_path=data.get("pdf_path", ""),
            generated_at=data.get("generated_at", ""),
        )


def format_timestamp(value: str) -> str:
    """Format an ISO timestamp for display, or return a placeholder if empty/invalid."""
    if not value:
        return NEVER_TEXT
    try:
        return datetime.fromisoformat(value).strftime("%b %d, %Y %I:%M %p")
    except ValueError:
        return value


def _history_path() -> Path:
    return get_app_data_dir() / HISTORY_FILENAME


def load_history() -> list[HistoryEntry]:
    """Return all history entries, most recent first."""
    path = _history_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read history file at %s", path)
        return []
    return [HistoryEntry.from_dict(item) for item in data.get("entries", [])]


def add_history_entry(entry: HistoryEntry) -> None:
    """Prepend a new entry to the history log and persist it to disk."""
    entries = load_history()
    entries.insert(0, entry)
    del entries[MAX_HISTORY_ENTRIES:]
    path = _history_path()
    try:
        path.write_text(
            json.dumps({"entries": [e.to_dict() for e in entries]}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        logger.warning("Could not write history file at %s", path)
