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
