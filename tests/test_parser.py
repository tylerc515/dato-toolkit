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
