"""Tests for ATS xlsx parser. Tests run against real files in examples/ats/."""
from __future__ import annotations

import calendar
import pytest

FLOOR = "examples/ats/7-88-0525 - 01 FLOOR.xlsx"
FRONT_WALL = "examples/ats/7-88-0525 - 02 FRONT WALL W PORTS.xlsx"


def test_convert_reading_decimal():
    from app.converters.ats_parser import convert_reading
    assert convert_reading(0.234) == "234"


def test_convert_reading_small_value():
    from app.converters.ats_parser import convert_reading
    assert convert_reading(0.010) == "010"


def test_convert_reading_none_returns_blank():
    from app.converters.ats_parser import convert_reading
    assert convert_reading(None) == ""


def test_convert_reading_flag_passthrough():
    from app.converters.ats_parser import convert_reading
    assert convert_reading("NC") == "NC"


def test_convert_reading_empty_string():
    from app.converters.ats_parser import convert_reading
    assert convert_reading("") == ""


def test_parse_floor_returns_result():
    from app.converters.ats_parser import ATSParseResult, parse_ats_file
    result = parse_ats_file(FLOOR)
    assert isinstance(result, ATSParseResult)


def test_parse_floor_metadata_nonempty():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    assert result.company_name
    assert result.mill_location
    assert result.boiler_name
    assert result.boiler_section
    assert result.nde_laboratory


def test_parse_floor_inspection_date_format():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    parts = result.inspection_date.split()
    assert len(parts) == 2, f"Expected 'Month YYYY', got '{result.inspection_date}'"
    assert parts[0] in list(calendar.month_name)[1:], f"'{parts[0]}' is not a month name"
    assert parts[1].isdigit() and len(parts[1]) == 4, f"'{parts[1]}' is not a 4-digit year"


def test_parse_floor_has_elevations():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    assert len(result.elevations) > 0


def test_parse_floor_tube_count_matches_tube_numbers():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    assert result.num_tubes > 0
    assert len(result.tube_numbers) == result.num_tubes


def test_parse_floor_readings_length_matches_tube_count():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    for elev in result.elevations:
        assert len(elev.left) == result.num_tubes
        assert len(elev.cntr) == result.num_tubes
        assert len(elev.rght) == result.num_tubes


def test_parse_floor_readings_are_strings_not_none():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    for elev in result.elevations:
        for reading in elev.left + elev.cntr + elev.rght:
            assert reading is not None, "Reading should be str, not None"
            assert isinstance(reading, str)


def test_parse_floor_numbering_direction():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    assert result.numbering_direction in ("Left-to-Right", "Right-to-Left")


def test_parse_floor_flags_is_dict():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    assert isinstance(result.ats_comment_codes, dict)


def test_parse_floor_flags_passthrough_in_readings():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    comment_codes = set(result.ats_comment_codes.keys())
    for elev in result.elevations:
        for reading in elev.left + elev.cntr + elev.rght:
            if reading and not reading.isdigit():
                assert reading in comment_codes or reading == "", (
                    f"Non-numeric reading '{reading}' not in known comment codes {comment_codes}"
                )


def test_parse_front_wall_has_elevations():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FRONT_WALL)
    assert len(result.elevations) > 0


def test_parse_invalid_file_raises():
    from app.converters.ats_parser import ATSParseError, parse_ats_file
    with pytest.raises(ATSParseError):
        parse_ats_file("nonexistent_file_that_does_not_exist.xlsx")
