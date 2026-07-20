"""Tests for the Update Email page's Recent Projects picker dialog.

Regression guard for dialog text overflow at the current (larger) font
size: a long, real-world project title must not force a horizontal
scrollbar - it elides and exposes the full text via a tooltip instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from app.pages.email_page import EmailPage
from app.project import ProjectConfig

_qapp = QApplication.instance() or QApplication(sys.argv)

# A realistic, long title in the format actually used in the field:
# "{CUSTOMER} {EQUIPMENT} — {YEAR} OUTAGE NDE TRACKSHEET"
LONG_TITLE = "EXAMPLE PAPER RB2 — 2026 OUTAGE NDE TRACKSHEET"


def test_recent_projects_dialog_elides_long_title_with_tooltip_and_no_hscroll():
    page = EmailPage()
    config = ProjectConfig(title=LONG_TITLE, date="2026")
    projects = [(Path("dummy.json"), config)]

    dialog, list_widget = page._build_recent_projects_dialog(projects)
    # Lay it out at the dialog's minimum width so a long title would overflow
    # if elision were not applied.
    dialog.resize(460, 260)
    dialog.show()
    _qapp.processEvents()

    expected_display = f"{LONG_TITLE}  —  2026"

    # A horizontal scrollbar must never appear for text overflow.
    assert (
        list_widget.horizontalScrollBarPolicy()
        == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    assert not list_widget.horizontalScrollBar().isVisible()

    # Long items elide (ellipsis) rather than overflow...
    assert list_widget.textElideMode() == Qt.TextElideMode.ElideRight

    # ...and the full, untruncated title stays available on hover and in data.
    item = list_widget.item(0)
    assert item.toolTip() == expected_display
    assert item.text() == expected_display

    dialog.close()
