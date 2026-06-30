"""Tests for ConverterPage QSettings output folder persistence."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_page():
    """Create a ConverterPage with QSettings patched to return an empty saved path."""
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = ""
        MockSettings.return_value = instance
        from app.pages.converter_page import ConverterPage
        return ConverterPage()


def test_load_output_folder_returns_qsettings_value():
    """_load_output_folder() returns the value stored in QSettings."""
    from app.pages.converter_page import ConverterPage

    page = _make_page()
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = "/some/saved/path"
        MockSettings.return_value = instance

        result = page._load_output_folder()

        MockSettings.assert_called_with("BSI", "DATOToolkit")
        instance.value.assert_called_with("converter/last_output_folder", "")
        assert result == "/some/saved/path"


def test_load_output_folder_returns_empty_string_when_no_saved_path():
    """_load_output_folder() returns an empty string when no path is saved."""
    from app.pages.converter_page import ConverterPage

    page = _make_page()
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = ""
        MockSettings.return_value = instance

        result = page._load_output_folder()

        assert result == ""


def test_save_output_folder_calls_qsettings_set_value():
    """_save_output_folder() writes the folder path to QSettings."""
    page = _make_page()
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        MockSettings.return_value = instance

        page._save_output_folder("/new/folder")

        MockSettings.assert_called_with("BSI", "DATOToolkit")
        instance.setValue.assert_called_with("converter/last_output_folder", "/new/folder")


def test_output_folder_edit_empty_when_no_saved_path():
    """Output folder field starts empty when QSettings has no saved path."""
    page = _make_page()
    assert page._output_folder_edit.text() == ""


def test_output_folder_edit_pre_filled_when_saved_path_exists():
    """Output folder field is pre-filled from QSettings when a saved path exists."""
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = "/previously/used/folder"
        MockSettings.return_value = instance

        from app.pages.converter_page import ConverterPage
        page = ConverterPage()

        assert page._output_folder_edit.text() == "/previously/used/folder"
