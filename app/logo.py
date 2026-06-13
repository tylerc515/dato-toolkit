"""Loads the app logo (assets/logo.svg) as a QPixmap/QIcon."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

LOGO_FILENAME = "logo.svg"
ICON_PIXMAP_SIZE = (256, 150)


def _logo_path() -> Path:
    """Return the path to assets/logo.svg, whether running from source or frozen."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "assets" / LOGO_FILENAME


def get_pixmap(width: int, height: int) -> QPixmap:
    """Render assets/logo.svg to a transparent QPixmap at the given size."""
    renderer = QSvgRenderer(str(_logo_path()))

    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap


def get_icon() -> QIcon:
    """Return a QIcon built from the logo, suitable for use as the window icon."""
    width, height = ICON_PIXMAP_SIZE
    return QIcon(get_pixmap(width, height))
