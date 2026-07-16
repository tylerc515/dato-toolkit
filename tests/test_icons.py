"""Tests for the qtawesome-based icon helper."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_icon_returns_non_null_qicon_for_known_names():
    from app.design.icons import icon
    # Every name actually used by the sidebar/components in this redesign,
    # confirmed to resolve under the ph. prefix (see plan Global Constraints
    # for the two substitutions: mail -> envelope-simple, file-spreadsheet -> table).
    names = [
        "house", "table", "envelope-simple", "arrows-left-right",
        "clock-counter-clockwise", "gear", "caret-down", "caret-right",
        "play", "folder", "upload-simple", "download-simple", "trash",
        "pencil-simple", "check", "x", "plus", "magnifying-glass",
        "warning-circle", "user-circle",
    ]
    for name in names:
        result = icon(name)
        assert not result.isNull(), f"icon({name!r}) returned a null QIcon"


def test_icon_accepts_custom_color():
    from app.design.icons import icon
    from app.design.tokens import Color
    result = icon("house", color=Color.ACCENT_TEXT)
    assert not result.isNull()


def test_icon_default_color_is_text_muted():
    import inspect
    from app.design.icons import icon
    from app.design.tokens import Color
    sig = inspect.signature(icon)
    assert sig.parameters["color"].default == Color.TEXT_MUTED
