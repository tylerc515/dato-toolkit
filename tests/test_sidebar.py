"""Tests for the left sidebar navigation widget."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_sidebar_has_expected_nav_items():
    from app.widgets.sidebar import Sidebar
    sidebar = Sidebar()
    assert set(sidebar._nav_buttons.keys()) == {
        "dashboard", "tracksheet", "email", "converter", "history", "settings",
    }


def test_sidebar_fixed_width():
    from app.widgets.sidebar import Sidebar, SIDEBAR_WIDTH
    sidebar = Sidebar()
    assert SIDEBAR_WIDTH == 248
    assert sidebar.minimumWidth() == 248
    assert sidebar.maximumWidth() == 248


def test_clicking_nav_item_emits_signal_with_item_id(qtbot):
    from app.widgets.sidebar import Sidebar
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    with qtbot.waitSignal(sidebar.nav_item_clicked, timeout=1000) as blocker:
        sidebar._nav_buttons["history"].click()
    assert blocker.args[0] == "history"


def test_set_active_marks_exactly_one_item_active():
    from app.widgets.sidebar import Sidebar
    sidebar = Sidebar()
    sidebar.set_active("converter")
    assert sidebar._nav_buttons["converter"].property("active") == "true"
    for item_id, btn in sidebar._nav_buttons.items():
        if item_id != "converter":
            assert btn.property("active") != "true"

    sidebar.set_active("dashboard")
    assert sidebar._nav_buttons["dashboard"].property("active") == "true"
    assert sidebar._nav_buttons["converter"].property("active") != "true"
