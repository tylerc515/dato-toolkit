"""Rotating file logging setup for TRACE Tracker Builder."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app import __version__
from app.project import get_logs_dir

LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3


def setup_logging() -> None:
    """Configure the root logger to write to a rotating log file in app data."""
    log_path = get_logs_dir() / "app.log"
    handler = RotatingFileHandler(log_path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(f"%(asctime)s [%(levelname)s] (v{__version__}) %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
