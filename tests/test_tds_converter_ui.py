"""Tests for the TDS sub-tab and the TDS import/detect/parse flow on the
Data Converter page.

The convert half (blank toggle, flag review, output, conversion) is Task 6
and is intentionally NOT exercised here. Real TDS samples are local and
untracked; tests that need them read expected values dynamically and skip
when the sample directories are empty. No client values are hardcoded.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QLabel

_qapp = QApplication.instance() or QApplication(sys.argv)

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "tds"
_NEW_DIR = _EXAMPLES / "New"
_OLD_DIR = _EXAMPLES / "Old"


def _make_page():
    """Create a ConverterPage with QSettings patched to avoid disk access."""
    with patch("app.pages.converter_page.QSettings") as MockSettings:
        instance = MagicMock()
        instance.value.return_value = ""
        MockSettings.return_value = instance
        from app.pages.converter_page import ConverterPage
        return ConverterPage()


def _sample(directory: Path) -> str:
    """Return the first CSV sample in a directory, or skip if none exist."""
    if not directory.is_dir():
        pytest.skip(f"TDS samples not present: {directory}")
    files = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".csv"
    )
    if not files:
        pytest.skip(f"No TDS samples in {directory}")
    return str(files[0])


def _new_sample() -> str:
    return _sample(_NEW_DIR)


def _old_sample() -> str:
    return _sample(_OLD_DIR)


# ---------------------------------------------------------------------------
# Tab enablement + switching
# ---------------------------------------------------------------------------

def test_tds_tab_enabled():
    page = _make_page()
    assert page._tds_tab_btn.isEnabled() is True


def test_tab_switch_shows_tds_view():
    page = _make_page()
    page._show_tds_tab()
    assert page._tab_stack.currentIndex() == 2
    # The other tabs still switch correctly after the TDS tab exists.
    page._show_ats_tab()
    assert page._tab_stack.currentIndex() == 0
    page._show_team_tab()
    assert page._tab_stack.currentIndex() == 1
    page._show_tds_tab()
    assert page._tab_stack.currentIndex() == 2


# ---------------------------------------------------------------------------
# Import + detect + parse
# ---------------------------------------------------------------------------

def test_import_detects_and_parses_new_and_old():
    page = _make_page()
    new_path = _new_sample()
    old_path = _old_sample()
    page._import_tds_file(new_path)
    page._import_tds_file(old_path)

    assert new_path in page._tds_imported
    assert old_path in page._tds_imported
    # Files in the New/ sample dir are the 5.3+ format; Old/ are pre-5.3.
    assert page._tds_imported[new_path][0] == "new"
    assert page._tds_imported[old_path][0] == "old"


def test_file_card_shows_format_badge():
    page = _make_page()
    new_path = _new_sample()
    old_path = _old_sample()
    page._import_tds_file(new_path)
    page._import_tds_file(old_path)

    new_badge = page._tds_cards[new_path]._badge.text()
    old_badge = page._tds_cards[old_path]._badge.text()
    assert new_badge == "New"
    assert old_badge == "Old"


def test_old_format_shows_confirmation_and_requires_nde():
    page = _make_page()
    new_path = _new_sample()
    old_path = _old_sample()
    page._import_tds_file(new_path)
    page._import_tds_file(old_path)

    new_card = page._tds_cards[new_path]
    old_card = page._tds_cards[old_path]

    # Old: needs confirmation framing; NDE empty and flagged required.
    assert old_card.needs_confirmation is True
    assert old_card.metadata()["nde_laboratory"] == ""
    assert old_card.nde_required() is True

    # New: no confirmation framing; NDE pre-filled from the file.
    assert new_card.needs_confirmation is False
    assert new_card.metadata()["nde_laboratory"] != ""
    assert new_card.nde_required() is False


def test_new_card_metadata_prefilled_from_parse():
    page = _make_page()
    from app.converters.tds_new_parser import parse_tds_new_file

    new_path = _new_sample()
    result = parse_tds_new_file(new_path)
    page._import_tds_file(new_path)
    meta = page._tds_cards[new_path].metadata()

    # Fields mirror the parsed values (read dynamically - no hardcoding).
    assert meta["company_name"] == result.company_name
    assert meta["mill_location"] == result.mill_location
    assert meta["boiler_name"] == result.boiler_name
    assert meta["inspection_date"] == result.inspection_date
    assert meta["boiler_section"] == result.boiler_section
    assert meta["nde_laboratory"] == result.nde_laboratory


def test_old_card_positional_metadata_prefilled_but_editable():
    page = _make_page()
    from app.converters.tds_old_parser import parse_tds_old_file

    old_path = _old_sample()
    result = parse_tds_old_file(old_path)
    page._import_tds_file(old_path)
    card = page._tds_cards[old_path]

    # The five positional fields are pre-filled from position.
    assert card.metadata()["company_name"] == result.company_name
    assert card.metadata()["boiler_section"] == result.boiler_section

    # Edits are reflected in the exposed metadata (Task 6 reads current values).
    card._company_edit.setText("EDITED CO")
    card._nde_edit.setText("Some Lab")
    assert card.metadata()["company_name"] == "EDITED CO"
    assert card.metadata()["nde_laboratory"] == "Some Lab"


def test_file_card_shows_measured_vs_total_elevation_count():
    page = _make_page()
    from app.converters.tds_new_parser import parse_tds_new_file

    new_path = _new_sample()
    result = parse_tds_new_file(new_path)
    page._import_tds_file(new_path)
    card = page._tds_cards[new_path]

    total = len(result.elevations)
    measured = sum(1 for e in result.elevations if e.has_data)
    combined = " ".join(w.text() for w in card.findChildren(QLabel))
    assert f"{total} elevation" in combined
    assert f"{measured} with data" in combined


def test_remove_tds_file_clears_card_and_state():
    page = _make_page()
    new_path = _new_sample()
    page._import_tds_file(new_path)
    assert new_path in page._tds_imported
    assert new_path in page._tds_cards

    page._on_remove_tds_file(new_path)
    assert new_path not in page._tds_imported
    assert new_path not in page._tds_cards


def test_import_bad_file_records_error_card(tmp_path):
    page = _make_page()
    bad = tmp_path / "not_a_tds.csv"
    bad.write_text("just,some,garbage\nno,tds,structure\n", encoding="utf-8")
    page._import_tds_file(str(bad))
    # Unparseable file goes to the error map, not the imported map.
    assert str(bad) in page._tds_errors
    assert str(bad) not in page._tds_imported


# ---------------------------------------------------------------------------
# Tab switching preserves state
# ---------------------------------------------------------------------------

def test_tab_switch_preserves_ats_state():
    page = _make_page()
    page._imported["fake/path.xlsx"] = object()
    page._show_tds_tab()
    page._show_ats_tab()
    assert "fake/path.xlsx" in page._imported


def test_tab_switch_preserves_team_state():
    page = _make_page()
    page._team_imported["fake/team.xlsx"] = object()
    page._show_tds_tab()
    page._show_team_tab()
    assert "fake/team.xlsx" in page._team_imported


def test_tab_switch_preserves_tds_state():
    page = _make_page()
    new_path = _new_sample()
    page._import_tds_file(new_path)
    page._show_ats_tab()
    page._show_team_tab()
    page._show_tds_tab()
    assert new_path in page._tds_imported


# ---------------------------------------------------------------------------
# Task 6: convert half - toggle, flag review, output, per-format conversion
# ---------------------------------------------------------------------------

def _make_tds_elevation(label, has_data, num_tubes=2, symbol=None, tech_code="TDS"):
    """Build a TDSElevation with either measured or blank reading cells.

    Passing a symbol seeds a non-numeric flag character into the first LEFT
    cell so flag-collection logic has something to find.
    """
    from app.converters.tds_new_parser import TDSElevation

    if has_data:
        left = ["220"] * num_tubes
        cntr = ["218"] * num_tubes
        rght = ["222"] * num_tubes
        if symbol is not None:
            left[0] = symbol
    else:
        left = [""] * num_tubes
        cntr = [""] * num_tubes
        rght = [""] * num_tubes
    return TDSElevation(
        label=label, left=left, cntr=cntr, rght=rght,
        has_data=has_data, tech_code=tech_code,
    )


def _make_tds_new_result(measured=1, blank=0, nde="Some Lab", symbol=None):
    """Synthetic TDSNewParseResult with a mix of measured and blank elevations."""
    from app.converters.tds_new_parser import TDSNewParseResult

    elevations = []
    for i in range(measured):
        elevations.append(
            _make_tds_elevation(f"{i} FT", True, symbol=symbol if i == 0 else None)
        )
    for i in range(blank):
        elevations.append(_make_tds_elevation(f"BLANK {i}", False))
    return TDSNewParseResult(
        company_name="TEST CO",
        mill_location="Mill, TX",
        boiler_name="Boiler 1",
        inspection_date="March 2024",
        boiler_section="FRONT WALL",
        num_tubes=2,
        numbering_direction="Left-to-Right",
        nde_laboratory=nde,
        tube_numbers=[1, 2],
        elevations=elevations,
    )


def _make_tds_old_result(measured=1, blank=0):
    """Synthetic TDSOldParseResult (no NDE field - supplied at convert time)."""
    from app.converters.tds_old_parser import TDSOldParseResult

    elevations = []
    for i in range(measured):
        elevations.append(_make_tds_elevation(f"{i} FT", True))
    for i in range(blank):
        elevations.append(_make_tds_elevation(f"BLANK {i}", False))
    return TDSOldParseResult(
        company_name="OLD CO",
        mill_location="Mill, AR",
        boiler_name="Boiler 2",
        inspection_date="April 2024",
        boiler_section="REAR WALL",
        num_tubes=2,
        numbering_direction="Right-to-Left",
        tube_numbers=[1, 2],
        elevations=elevations,
    )


def _add_tds_file(page, path, fmt, result):
    """Register a synthetic file + its card exactly like _import_tds_file does,
    without touching disk."""
    from app.pages.converter_page import _TdsFileCard

    card = _TdsFileCard(path, fmt, result, page)
    card.metadata_changed.connect(page._on_tds_metadata_changed)
    page._tds_imported[path] = (fmt, result)
    page._tds_cards[path] = card
    return card


def _read_standard_output(path):
    """Parse a written Standard Format CSV back into rows for assertions."""
    import csv

    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def _standard_metadata_value(rows, label_substr):
    """Return the metadata value (col H / index 7) for a label row."""
    for row in rows:
        if len(row) > 5 and label_substr in row[5]:
            return row[7] if len(row) > 7 else ""
    return None


def _standard_reading_cells(rows):
    """All reading cells (col index >= 5) from LEFT/CNTR/RGHT block rows."""
    cells = set()
    for row in rows:
        marker = row[4].strip() if len(row) > 4 else ""
        if marker in ("LEFT", "CNTR", "RGHT"):
            for cell in row[5:]:
                stripped = cell.strip()
                if stripped:
                    cells.add(stripped)
    return cells


# --- Blank toggle --------------------------------------------------------

def test_blank_toggle_defaults_unchecked():
    # TDS spec intentionally differs from TEAM (which defaults checked).
    page = _make_page()
    assert page._tds_include_blank.isChecked() is False


def test_blank_toggle_batch_wide_changes_tds_output_counts():
    page = _make_page()
    _add_tds_file(page, "a/New1.csv", "new", _make_tds_new_result(measured=2, blank=3))
    _add_tds_file(page, "b/New2.csv", "new", _make_tds_new_result(measured=1, blank=2))

    # One toggle governs every file in the batch.
    page._tds_include_blank.setChecked(False)
    jobs = dict(page._tds_conversion_jobs())
    assert len(jobs["a/New1.csv"].elevations) == 2
    assert len(jobs["b/New2.csv"].elevations) == 1

    page._tds_include_blank.setChecked(True)
    jobs = dict(page._tds_conversion_jobs())
    assert len(jobs["a/New1.csv"].elevations) == 5
    assert len(jobs["b/New2.csv"].elevations) == 3


def test_blank_toggle_updates_tds_elevation_stat_live():
    page = _make_page()
    _add_tds_file(page, "a/New1.csv", "new", _make_tds_new_result(measured=2, blank=3))
    page._after_tds_files_changed()

    page._tds_include_blank.setChecked(False)
    assert page._tds_stat_elevations._value_label.text() == "2"
    page._tds_include_blank.setChecked(True)
    assert page._tds_stat_elevations._value_label.text() == "5"


# --- Convert button gating ----------------------------------------------

def test_tds_convert_all_disabled_until_metadata_complete():
    page = _make_page()
    old_path = _old_sample()
    page._import_tds_file(old_path)
    # Force flags confirmed so only metadata governs the button in this test.
    page._tds_flags_confirmed = True

    # Old file arrives with an empty, required NDE -> convert stays disabled.
    page._update_tds_convert_button()
    assert page._tds_convert_btn.isEnabled() is False

    # Filling the NDE (all other fields prefilled from parse) enables it.
    page._tds_cards[old_path]._nde_edit.setText("Regression Lab")
    page._update_tds_convert_button()
    assert page._tds_convert_btn.isEnabled() is True

    # Blanking any field disables it again.
    page._tds_cards[old_path]._section_edit.setText("")
    page._update_tds_convert_button()
    assert page._tds_convert_btn.isEnabled() is False


def test_tds_convert_needs_flags_confirmed():
    page = _make_page()
    _add_tds_file(page, "a/New1.csv", "new", _make_tds_new_result(measured=1))
    page._update_tds_convert_button()
    # Metadata is complete for a New file, but flags not confirmed yet.
    assert page._tds_convert_btn.isEnabled() is False
    page._tds_flags_confirmed = True
    page._update_tds_convert_button()
    assert page._tds_convert_btn.isEnabled() is True


# --- Flag review ---------------------------------------------------------

def test_tds_flag_review_collects_symbols_from_elevations():
    page = _make_page()
    # Seed a non-numeric symbol that is NOT a known Standard Format symbol.
    _add_tds_file(page, "a/New1.csv", "new", _make_tds_new_result(measured=1, symbol="ZZ"))
    page._after_tds_files_changed()
    symbols = page._tds_collect_symbols()
    assert "ZZ" in symbols
    # An unknown symbol shows up in the flags-needing-review stat.
    assert page._tds_stat_flags._value_label.text() == "1"


# --- Conversion output ---------------------------------------------------

def test_new_and_old_convert_to_valid_output(tmp_path):
    from app.converters.standard_format_writer import write_standard_format
    import csv

    page = _make_page()
    new_path = _new_sample()
    old_path = _old_sample()
    page._import_tds_file(new_path)
    page._import_tds_file(old_path)

    unique_nde = "REGRESSION LAB 9137"
    page._tds_cards[old_path]._nde_edit.setText(unique_nde)

    jobs = dict(page._tds_conversion_jobs())

    # Collect the Old file's discarded Minimum/Allowable values from the raw
    # source so we can assert they never leak into the converted output.
    old_rows = list(csv.reader(open(old_path, encoding="utf-8", errors="ignore")))
    min_allowable = set()
    for i in range(len(old_rows) - 1):
        row = old_rows[i]
        if len(row) > 3 and row[3].strip() == "CNTR" and len(row) > 2 and row[2].strip():
            min_allowable.add(row[2].strip())
    source_readings = set()
    for row in old_rows:
        marker = row[3].strip() if len(row) > 3 else ""
        if marker in ("LEFT", "CNTR", "RGHT"):
            for cell in row[4:]:
                if cell.strip():
                    source_readings.add(cell.strip().lstrip("0") or "0")
    # Min/Allowable values that are not coincidentally a real reading value.
    distinctive = {v for v in min_allowable if v.lstrip("0") not in source_readings}

    outputs = {}
    for path, writer_input in jobs.items():
        out = tmp_path / f"{path.replace('/', '_').replace(chr(92), '_')}.csv"
        write_standard_format(writer_input, page._tds_flag_mapping, out)
        outputs[path] = _read_standard_output(out)

    # Both outputs are structurally valid Standard Format files.
    for rows in outputs.values():
        assert _standard_metadata_value(rows, "Company Name:") is not None
        assert _standard_metadata_value(rows, "NDE Laboratory:") is not None
        assert any(
            len(r) > 1 and "TUBE NUMBERS along the top" in r[1] for r in rows
        )
        assert any(
            len(r) > 1 and "TUBE NUMBERS along the bottom" in r[1] for r in rows
        )

    # Old output carries the user-supplied NDE.
    assert _standard_metadata_value(outputs[old_path], "NDE Laboratory:") == unique_nde

    # Regression: the discarded Minimum/Allowable value never leaks into output.
    if distinctive:
        out_readings = _standard_reading_cells(outputs[old_path])
        assert distinctive.isdisjoint(out_readings)


def test_edited_metadata_flows_to_output():
    from app.pages.converter_page import _output_filename

    page = _make_page()
    card = _add_tds_file(page, "a/New1.csv", "new", _make_tds_new_result(measured=1))

    # Edit the card's boiler section and company AFTER import.
    card._section_edit.setText("EDITED SECTION")
    card._company_edit.setText("EDITED CO")

    jobs = dict(page._tds_conversion_jobs())
    writer_input = jobs["a/New1.csv"]

    # The edited values (not the original parse) drive the output.
    assert writer_input.boiler_section == "EDITED SECTION"
    assert writer_input.company_name == "EDITED CO"
    assert _output_filename(writer_input) == "EDITED SECTION_Standard_Format.csv"


def test_old_conversion_input_includes_user_nde():
    page = _make_page()
    card = _add_tds_file(page, "a/Old1.csv", "old", _make_tds_old_result(measured=1))
    card._nde_edit.setText("USER NDE LAB")

    jobs = dict(page._tds_conversion_jobs())
    writer_input = jobs["a/Old1.csv"]
    assert writer_input.nde_laboratory == "USER NDE LAB"
