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


def test_asme_calculator_link_present_with_tooltip():
    from app.widgets.sidebar import Sidebar
    sidebar = Sidebar()
    assert sidebar._asme_button.text().strip() == "ASME Calculator"
    assert sidebar._asme_button.toolTip() == "Opens in your browser"
    # It is not a registered nav target.
    assert "asme_calculator" not in sidebar._nav_buttons


def test_asme_calculator_opens_browser_without_navigating(qtbot, monkeypatch):
    from app.widgets.sidebar import Sidebar, ASME_CALCULATOR_URL
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    sidebar.set_active("history")  # some page is active before the click

    opened = []
    monkeypatch.setattr("app.widgets.sidebar.webbrowser.open", lambda url: opened.append(url))
    nav_emissions = []
    sidebar.nav_item_clicked.connect(nav_emissions.append)

    sidebar._asme_button.click()

    # Opens the exact URL in the browser.
    assert opened == [ASME_CALCULATOR_URL]
    # Does not navigate (no nav signal) and does not change the active nav item.
    assert nav_emissions == []
    assert sidebar._nav_buttons["history"].property("active") == "true"
    assert all(
        btn.property("active") == ("true" if item_id == "history" else "false")
        for item_id, btn in sidebar._nav_buttons.items()
    )
