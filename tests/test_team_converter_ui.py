"""Tests for the ATS/TEAM sub-tab switching on the Data Converter page."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_page():
    """Create a ConverterPage with QSettings patched to avoid disk access."""
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = ""
        MockSettings.return_value = instance
        from app.pages.converter_page import ConverterPage
        return ConverterPage()


def test_team_tab_is_enabled():
    page = _make_page()
    assert page._team_tab_btn.isEnabled() is True


def test_clicking_team_tab_shows_team_view():
    page = _make_page()
    page._show_team_tab()
    assert page._tab_stack.currentIndex() == 1
    page._show_ats_tab()
    assert page._tab_stack.currentIndex() == 0


def test_tab_switch_preserves_ats_imported_state():
    page = _make_page()
    page._imported["fake/path.xlsx"] = object()  # simulate an imported ATS file
    page._show_team_tab()
    page._show_ats_tab()
    assert "fake/path.xlsx" in page._imported


def test_page_starts_on_ats_tab():
    page = _make_page()
    assert page._tab_stack.currentIndex() == 0
