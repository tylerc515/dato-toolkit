"""Tests for ConverterPage QSettings output folder persistence."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from app.converters.ats_parser import ATSElevation, ATSParseResult

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_page():
    """Create a ConverterPage with QSettings patched to return an empty saved path."""
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = ""
        MockSettings.return_value = instance
        from app.pages.converter_page import ConverterPage
        return ConverterPage()


def _make_ats_result(section: str = "01 FLOOR") -> ATSParseResult:
    """Minimal ATSParseResult for conversion-flow tests."""
    return ATSParseResult(
        company_name="TEST CO",
        mill_location="Somewhere, TX",
        boiler_name="Boiler 1",
        inspection_date="January 2025",
        boiler_section=section,
        num_tubes=2,
        numbering_direction="Left-to-Right",
        nde_laboratory="ATS Lab",
        year=2025,
        ats_flags={},
        elevations=[
            ATSElevation(
                label="10 FT",
                tech_code="AB",
                nominal_wall=0.220,
                left=["220", "215"],
                cntr=["218", "213"],
                rght=["222", "216"],
            ),
        ],
        tube_numbers=[1, 2],
    )


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


# ---------------------------------------------------------------------------
# Overwrite confirmation
# ---------------------------------------------------------------------------

def test_overwrite_confirmation_lists_all_conflicts(tmp_path: Path):
    """The confirmation dialog text names every conflicting output file."""
    page = _make_page()
    conflicts = [
        tmp_path / "01 FLOOR_Standard_Format.csv",
        tmp_path / "02 CEILING_Standard_Format.csv",
    ]
    with patch("app.pages.converter_page.QMessageBox") as MockBox:
        instance = MockBox.return_value
        overwrite_btn = MagicMock()
        cancel_btn = MagicMock()
        instance.addButton.side_effect = [overwrite_btn, cancel_btn]
        instance.clickedButton.return_value = overwrite_btn

        result = page._confirm_overwrite(conflicts)

        message = instance.setText.call_args[0][0]
        assert "01 FLOOR_Standard_Format.csv" in message
        assert "02 CEILING_Standard_Format.csv" in message
        assert result is True


def test_conversion_cancelled_on_overwrite_decline(tmp_path: Path):
    """Declining the overwrite dialog aborts conversion; no files are touched."""
    page = _make_page()
    result = _make_ats_result(section="01 FLOOR")
    out_path = tmp_path / "01 FLOOR_Standard_Format.csv"
    out_path.write_text("existing content", encoding="utf-8")

    page._imported = {"input.xlsx": result}
    page._flag_mapping = {}
    page._flags_confirmed = True
    page._output_folder_edit.setText(str(tmp_path))

    with patch.object(page, "_confirm_overwrite", return_value=False):
        page._on_convert()

    assert page._worker is None
    assert out_path.read_text(encoding="utf-8") == "existing content"


# ---------------------------------------------------------------------------
# Friendly file write errors
# ---------------------------------------------------------------------------

def test_permission_error_shows_friendly_message(tmp_path: Path):
    """A locked output file produces a plain-English message, not a raw errno string."""
    from app.pages.converter_page import _ConvertWorker

    result = _make_ats_result(section="01 FLOOR")
    worker = _ConvertWorker([("input.xlsx", result)], {}, tmp_path)
    received: list[tuple[str, bool, str]] = []
    worker.file_done.connect(lambda path, success, msg: received.append((path, success, msg)))

    with patch(
        "app.pages.converter_page.write_standard_format",
        side_effect=PermissionError(13, "Permission denied"),
    ):
        worker.run()

    assert len(received) == 1
    path, success, message = received[0]
    assert success is False
    assert "Errno" not in message
    assert "another program" in message.lower()


def test_batch_continues_after_one_file_fails(tmp_path: Path):
    """One file failing with a write error does not stop the rest of the batch."""
    from app.pages.converter_page import _ConvertWorker

    result_a = _make_ats_result(section="01 FLOOR")
    result_b = _make_ats_result(section="02 CEILING")
    worker = _ConvertWorker(
        [("a.xlsx", result_a), ("b.xlsx", result_b)], {}, tmp_path
    )
    received: list[tuple[str, bool, str]] = []
    worker.file_done.connect(lambda path, success, msg: received.append((path, success, msg)))

    def fake_write(res, mapping, out_path):
        if "01 FLOOR" in str(out_path):
            raise PermissionError(13, "Permission denied")

    with patch("app.pages.converter_page.write_standard_format", side_effect=fake_write):
        worker.run()

    assert len(received) == 2
    assert received[0] == ("a.xlsx", False, received[0][2])
    assert received[1][0] == "b.xlsx"
    assert received[1][1] is True


def test_output_filename_rejects_path_traversal_in_boiler_section(tmp_path: Path):
    """boiler_section is parsed from an untrusted ATS xlsx file. A malicious or
    corrupted value like a path-traversal payload must not let the output file
    escape the chosen output directory."""
    from app.pages.converter_page import _ConvertWorker

    malicious_result = _make_ats_result(section="../../../../Windows/System32/evil")
    worker = _ConvertWorker([("a.xlsx", malicious_result)], {}, tmp_path)
    received: list[tuple[str, bool, str]] = []
    worker.file_done.connect(lambda path, success, msg: received.append((path, success, msg)))

    written_paths: list[Path] = []

    def fake_write(res, mapping, out_path):
        written_paths.append(Path(out_path))

    with patch("app.pages.converter_page.write_standard_format", side_effect=fake_write):
        worker.run()

    assert len(written_paths) == 1
    out_path = written_paths[0].resolve()
    assert out_path.parent == tmp_path.resolve()
    assert out_path.is_relative_to(tmp_path.resolve())
    assert "/" not in out_path.name
    assert "\\" not in out_path.name
