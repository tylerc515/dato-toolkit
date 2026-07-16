"""Tests for the ATS/TEAM sub-tab switching and TEAM flow on the Data Converter page."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication, QLabel

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_page():
    """Create a ConverterPage with QSettings patched to avoid disk access."""
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = ""
        MockSettings.return_value = instance
        from app.pages.converter_page import ConverterPage
        return ConverterPage()


def _make_team_result():
    """Minimal TEAMParseResult for TEAM-flow tests."""
    from app.converters.team_parser import TEAMElevation, TEAMParseResult

    return TEAMParseResult(
        tube_numbers=[1, 2],
        numbering_direction="Left-to-Right",
        num_tubes=2,
        elevations=[
            TEAMElevation(
                label="10 FT",
                left=["220", "215"],
                cntr=["218", "213"],
                rght=["222", "216"],
                has_data=True,
            ),
        ],
        flags_found=set(),
    )


def _make_mixed_team_result(measured=2, blank=3):
    """TEAMParseResult with a mix of measured and blank elevations."""
    from app.converters.team_parser import TEAMElevation, TEAMParseResult

    elevations = []
    for i in range(measured):
        elevations.append(TEAMElevation(
            label=f"{i} FT",
            left=["220"], cntr=["218"], rght=["222"],
            has_data=True,
        ))
    for i in range(blank):
        elevations.append(TEAMElevation(
            label=f"BLANK {i}",
            left=[""], cntr=[""], rght=[""],
            has_data=False,
        ))
    return TEAMParseResult(
        tube_numbers=[1],
        numbering_direction="Left-to-Right",
        num_tubes=1,
        elevations=elevations,
        flags_found=set(),
    )


def _fill_team_metadata(page, company="TEST CO", mill="Mill, TX", boiler="Boiler 1", nde="ATS Lab"):
    page._team_company_edit.setText(company)
    page._team_mill_edit.setText(mill)
    page._team_boiler_edit.setText(boiler)
    page._team_nde_edit.setText(nde)


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


# ---------------------------------------------------------------------------
# TEAM flow
# ---------------------------------------------------------------------------

def test_convert_all_disabled_until_metadata_complete():
    page = _make_page()
    path = "C:/x/FLOOR.xlsx"
    page._team_imported[path] = _make_team_result()
    page._team_section_names[path] = "FLOOR"
    page._team_flags_confirmed = True
    page._team_flag_mapping = {}

    # Metadata blank -> convert stays disabled.
    _fill_team_metadata(page, company="", mill="", boiler="", nde="")
    page._update_team_convert_button()
    assert page._team_convert_btn.isEnabled() is False

    # All five metadata fields (+ section name) set -> convert enabled.
    _fill_team_metadata(page)
    page._update_team_convert_button()
    assert page._team_convert_btn.isEnabled() is True

    # Blanking a section name disables it again.
    page._team_section_names[path] = ""
    page._update_team_convert_button()
    assert page._team_convert_btn.isEnabled() is False


def test_section_name_defaults_from_filename():
    from app.pages.converter_page import _default_section_name

    assert _default_section_name("SOOTBLOWER_PASS_A.xlsx") == "SOOTBLOWER PASS A"
    assert _default_section_name("FLOOR MLO.xlsx") == "FLOOR MLO"
    assert _default_section_name("FLOOR.xlsx") == "FLOOR"


def test_batch_flag_mapping_applies_to_all_files(tmp_path):
    page = _make_page()
    r1, r2 = _make_team_result(), _make_team_result()
    page._team_imported = {"a/FLOOR.xlsx": r1, "b/ROOF.xlsx": r2}
    page._team_section_names = {"a/FLOOR.xlsx": "FLOOR", "b/ROOF.xlsx": "ROOF"}
    _fill_team_metadata(page, company="CO", mill="Mill", boiler="B1", nde="Lab")
    page._team_flags_confirmed = True
    page._team_flag_mapping = {"@": "@"}
    page._team_output_folder_edit.setText(str(tmp_path))

    with patch("app.pages.converter_page._ConvertWorker") as MockWorker:
        page._on_team_convert()

    args, _ = MockWorker.call_args
    jobs, mapping, output_dir = args[0], args[1], args[2]

    assert len(jobs) == 2
    # One batch-wide flag mapping for the whole worker (applies to every job).
    assert mapping == {"@": "@"}
    # Every job carries the identical batch metadata; only the section differs.
    sections = set()
    for _path, inp in jobs:
        assert inp.company_name == "CO"
        assert inp.mill_location == "Mill"
        assert inp.boiler_name == "B1"
        assert inp.nde_laboratory == "Lab"
        assert inp.inspection_date == (
            f"{page._team_month_combo.currentText()} {page._team_year_combo.currentText()}"
        )
        sections.add(inp.boiler_section)
    assert sections == {"FLOOR", "ROOF"}


# ---------------------------------------------------------------------------
# Refinement task 2: NDE default, blank-elevation toggle, card counts
# ---------------------------------------------------------------------------

def test_nde_laboratory_defaults_to_team():
    page = _make_page()
    assert page._team_nde_edit.text() == "TEAM"
    assert page._team_nde_edit.isReadOnly() is False


def test_include_blank_defaults_to_checked():
    page = _make_page()
    assert page._team_include_blank.isChecked() is True


def test_include_blank_toggle_changes_output_elevation_count():
    page = _make_page()
    path = "C:/x/FLOOR.xlsx"
    result = _make_mixed_team_result(measured=2, blank=3)
    page._team_imported[path] = result
    page._team_section_names[path] = "FLOOR"
    _fill_team_metadata(page)

    # Unchecked -> only measured elevations reach the conversion input.
    page._team_include_blank.setChecked(False)
    jobs = page._team_conversion_inputs()
    assert len(jobs) == 1
    _p, inp = jobs[0]
    assert len(inp.elevations) == 2

    # Checked -> all elevations (measured + blank) are included.
    page._team_include_blank.setChecked(True)
    jobs = page._team_conversion_inputs()
    _p, inp = jobs[0]
    assert len(inp.elevations) == 5


def test_include_blank_toggle_updates_elevation_stat_live():
    page = _make_page()
    path = "C:/x/FLOOR.xlsx"
    page._team_imported[path] = _make_mixed_team_result(measured=2, blank=3)

    page._team_include_blank.setChecked(False)
    page._update_team_file_stats()
    assert page._team_stat_elevations._value_label.text() == "2"

    # Flipping the toggle updates the stat live via its signal connection.
    page._team_include_blank.setChecked(True)
    assert page._team_stat_elevations._value_label.text() == "5"


def test_file_card_shows_measured_vs_total_elevation_count():
    from app.pages.converter_page import _TeamFileCard

    result = _make_mixed_team_result(measured=2, blank=3)  # 5 total, 2 measured
    card = _TeamFileCard("C:/x/FLOOR.xlsx", result, "FLOOR")
    combined = " ".join(w.text() for w in card.findChildren(QLabel))
    assert "5 elevations" in combined
    assert "2 with data" in combined
