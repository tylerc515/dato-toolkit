"""Tests that MainWindow's sidebar navigation stays in sync with page switches."""
from __future__ import annotations

import sys
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_window():
    from app.window import MainWindow
    with patch("app.window.QSettings") as MockSettings, \
            patch.object(MainWindow, "_maybe_show_onboarding"), \
            patch.object(MainWindow, "_run_update_check"):
        instance = MockSettings.return_value
        instance.value.return_value = None
        return MainWindow()


def test_window_has_sidebar_attribute():
    win = _make_window()
    from app.widgets.sidebar import Sidebar
    assert isinstance(win.sidebar, Sidebar)


def test_go_to_converter_activates_converter_sidebar_item():
    win = _make_window()
    win._go_to_converter()
    assert win.sidebar._nav_buttons["converter"].property("active") == "true"


def test_go_to_dashboard_activates_dashboard_sidebar_item():
    win = _make_window()
    win._go_to_converter()  # move away from dashboard first
    win._go_to_dashboard()
    assert win.sidebar._nav_buttons["dashboard"].property("active") == "true"


def test_go_to_history_activates_history_sidebar_item():
    win = _make_window()
    win._go_to_history()
    assert win.sidebar._nav_buttons["history"].property("active") == "true"


def test_sidebar_nav_click_switches_stack_page():
    from app.pages.converter_page import ConverterPage
    win = _make_window()
    win.sidebar.nav_item_clicked.emit("converter")
    assert isinstance(win.stack.currentWidget(), ConverterPage)


def test_breadcrumb_updates_on_navigation():
    win = _make_window()
    win._go_to_converter()
    assert "Data converter" in win.breadcrumb_label.text()


def test_import_page_back_button_returns_to_dashboard():
    win = _make_window()
    win._go_to_step(0)  # navigate to import page (stack index 1)
    assert win.stack.currentIndex() == 1
    win.import_page.back_button.click()
    assert win.stack.currentIndex() == 0
