"""Responsive layout guards: the window never shrinks below its minimum, and
no page compresses or clips its content at that minimum.
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_window():
    from app.window import MainWindow

    with patch("app.window.QSettings") as MockSettings, \
            patch.object(MainWindow, "_maybe_show_onboarding"), \
            patch.object(MainWindow, "_run_update_check"):
        MockSettings.return_value.value.return_value = None
        window = MainWindow()
    window.resize(1200, 800)
    window.show()
    _qapp.processEvents()
    return window


def _dispose(window) -> None:
    window.close()
    window.deleteLater()
    _qapp.processEvents()


# --- Minimum size enforcement --------------------------------------------------

@pytest.mark.parametrize("direction", ["bottom-right", "top-left", "right", "bottom"])
def test_frameless_resize_drag_clamps_exactly_at_minimum_size(direction):
    """The custom edge-drag resize path must stop at minimumSize(), not near it."""
    window = _make_window()
    try:
        window._resize_direction = direction
        window._resize_start_geometry = QRect(window.geometry())
        window._resize_start_pos = QPoint(0, 0)
        # Drag far past the minimum in the shrinking direction for every edge.
        dx = 2000 if "left" in direction else -2000
        dy = 2000 if "top" in direction else -2000
        window._perform_resize(QPoint(dx, dy))
        _qapp.processEvents()
        if "left" in direction or "right" in direction:
            assert window.width() == window.minimumWidth()
        if "top" in direction or "bottom" in direction:
            assert window.height() == window.minimumHeight()
    finally:
        window._resize_direction = None
        _dispose(window)
