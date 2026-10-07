"""Unit tests for app.parser against sample TRACE export CSVs."""

from pathlib import Path

import pytest

from app.parser import TraceParseError, parse_trace_csv

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_floor_csv():
    data = parse_trace_csv(FIXTURES / "FLOOR.csv")

    assert data.company_name == "Example Paper"
    assert data.mill_location == "Anytown"
    assert data.boiler_name == "Recovery Boiler #2"
    assert data.inspection_date.strip() == "June 2026"
    assert data.boiler_section == "FLOOR"
    assert data.number_of_tubes == 97
    assert data.numbering_direction == "Left-to-Right"

    labels = [e.label for e in data.elevations]
    assert labels == [
        "-1'' FROM WELD",
        "+0' 0''",
        "+6'",
        "+12'",
        "+18'",
        "+24'",
        "+26'",
        "3X3 AREA AT SMELT SPOUTS 3'",
        "3X3 AREA AT SMELT SPOUTS 2'",
        "3X3 AREA AT SMELT SPOUTS 1'",
    ]

    for elevation in data.elevations:
        assert len(elevation.left) == 97
        assert len(elevation.cntr) == 97
        assert len(elevation.rght) == 97


def test_parse_front_wall_w_ports_csv():
    data = parse_trace_csv(FIXTURES / "FRONT_WALL_W_PORTS.csv")

    assert data.boiler_section == "FRONT WALL W/PORTS"
    labels = [e.label for e in data.elevations]
    assert labels == [
        "+37'6''",
        "+36' 0''",
        "+34' 6''",
        "+33' 0''",
        "+31'6''",
        "+30' 0''",
        "+28'6'' = 1'' ABOVE WELD LINE",
    ]


def test_parse_front_wall_mlo_csv():
    data = parse_trace_csv(FIXTURES / "FRONT_WALL_MLO.csv")

    assert data.boiler_section == "FRONT WALL MLO"
    labels = [e.label for e in data.elevations]
    assert "POSITION 'A' OF THE TERTIARY PORTS" in labels
    assert len(labels) == 12


def test_parse_missing_file_raises():
    with pytest.raises(TraceParseError):
        parse_trace_csv(FIXTURES / "does_not_exist.csv")


def test_parse_non_csv_raises(tmp_path):
    bad_file = tmp_path / "bad.csv"
    bad_file.write_text("not,a,trace,export\n1,2,3,4\n")
    with pytest.raises(TraceParseError):
        parse_trace_csv(bad_file)


# --- Ragged TRACE exports (not round-tripped through Excel) -------------------
#
# Every fixture before trace_ragged_2tube.csv was saved from Excel, which pads
# every row to the same width. Files straight out of TRACE are ragged: the
# banner line is 7 fields, the metadata lines are 8, and the data rows are 7.
# pandas' C engine fixes the column count from line 1 and raised on line 5.

RAGGED = FIXTURES / "trace_ragged_2tube.csv"

# Parsed metadata of FLOOR.csv captured on main before the ragged-CSV fix.
FLOOR_METADATA_BEFORE_FIX = {
    "company_name": "Example Paper",
    "mill_location": "Anytown",
    "boiler_name": "Recovery Boiler #2",
    "inspection_date": "June 2026",
    "boiler_section": "FLOOR",
    "number_of_tubes": 97,
    "numbering_direction": "Left-to-Right",
    "nde_laboratory": None,
}


def test_ragged_fixture_is_actually_ragged():
    """Guard against someone re-saving the fixture from Excel and padding it."""
    import csv

    with open(RAGGED, encoding="utf-8-sig", newline="") as fh:
        widths = [len(row) for row in csv.reader(fh)]
    assert widths[0] == 7
    assert widths[4] == 8
    assert widths[-1] == 7
    assert len(set(widths)) > 1


def test_ragged_csv_parses():
    data = parse_trace_csv(RAGGED)

    assert data.company_name == "Example Paper"
    assert data.mill_location == "Anytown"
    assert data.boiler_name == "RB1"
    assert data.boiler_section == "SOOTBLOWER PASS 'A'"
    assert data.number_of_tubes == 2
    assert [e.label for e in data.elevations] == ["+10' 0''", "+20' 0''", "+30' 0''"]
    assert data.elevations[0].left == ["0.185", "0.190"]
    assert data.elevations[2].rght == ["0.165", "0.169"]


def test_ragged_width_padding():
    from app.parser import read_ragged_csv

    rows = read_ragged_csv(RAGGED)
    widths = {len(row) for row in rows}
    assert widths == {8}
    assert rows[4][7] == "Example Paper"
    assert rows[0][7] == ""


def test_ragged_width_padding_empty_file(tmp_path):
    from app.parser import read_ragged_csv

    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert read_ragged_csv(empty) == []


def test_leading_space_date_stripped():
    data = parse_trace_csv(RAGGED)
    assert data.inspection_date == "October 2026"


def test_empty_nde_lab_tolerated():
    data = parse_trace_csv(RAGGED)
    assert not data.nde_laboratory
    assert data.nde_laboratory not in ("nan", "None", "NaN")


def test_padded_fixture_parses_identically_after_fix():
    data = parse_trace_csv(FIXTURES / "FLOOR.csv")
    actual = {key: getattr(data, key) for key in FLOOR_METADATA_BEFORE_FIX}
    assert actual == FLOOR_METADATA_BEFORE_FIX
    assert len(data.elevations) == 10
    assert all(len(e.left) == len(e.cntr) == len(e.rght) == 97 for e in data.elevations)
    # Every cell in FLOOR.csv is blank; blank cells must still read as None, not "".
    assert all(v is None for e in data.elevations for v in e.left + e.cntr + e.rght)
