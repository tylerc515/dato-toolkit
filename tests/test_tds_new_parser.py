"""Tests for the TDS new-format (5.3+) CSV parser.

Real sample files live under examples/tds/New/ (local/untracked, gitignored).
Tests must never hardcode a client name/value: expected values are always
read straight from the sample file with an independent csv read, then
compared against what the parser returns.
"""
from __future__ import annotations

import csv
import os

import pytest

from app.converters.tds_new_parser import (
    TDSElevation,
    TDSNewParseResult,
    TDSParseError,
    parse_tds_new_file,
)

NEW_DIR = "examples/tds/New"


def _new_samples() -> list[str]:
    return [
        os.path.join(NEW_DIR, f)
        for f in os.listdir(NEW_DIR)
        if f.lower().endswith(".csv") and not f.startswith("~$")
    ]


def _read_rows(filepath: str) -> list[list[str]]:
    with open(filepath, "r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.reader(f))


def _independent_label_value(rows: list[list[str]], label: str) -> str | None:
    """Re-implementation of the label/value extraction, kept separate from
    the parser so the test is an independent check, not a tautology."""
    for row in rows:
        for i, cell in enumerate(row):
            if label in cell:
                for j in range(i + 1, len(row)):
                    if row[j].strip():
                        return row[j].strip()
                return None
    return None


def _independent_direction(raw: str) -> str:
    upper = raw.upper()
    if "LEFT-TO-RIGHT" in upper or "LEFT TO RIGHT" in upper:
        return "Left-to-Right"
    if "RIGHT-TO-LEFT" in upper or "RIGHT TO LEFT" in upper:
        return "Right-to-Left"
    return raw.strip()


def _write_synthetic_csv(path, num_tubes: int, blocks: list[tuple]) -> None:
    """blocks: list of (tech, label_fragment, left_vals, cntr_vals, rght_vals)
    where *_vals are lists of length num_tubes of raw cell strings."""
    rows: list[list[str]] = []
    rows.append(["", "", "", "", "This file was created as a data sharing 'Standard'."])
    rows.append(["", "", "", "", "Best viewed if..."])
    rows.append([])
    rows.append([])
    rows.append(["", "", "", "", "", "Company Name:---->", "", "SyntheticCo"])
    rows.append(["", "", "", "", "", "Mill Location:--------->", "", "SyntheticMill"])
    rows.append(["", "", "", "", "", "Boiler Name:--------->", "", "SyntheticBoiler"])
    rows.append(["", "", "", "", "", "Inspection Date:----->", "", "January 2024"])
    rows.append(["", "", "", "", "", "Boiler Section:------->", "", "SYNTHETIC SECTION"])
    rows.append(["", "", "", "", "", "Number of tubes:---->", "", str(num_tubes)])
    rows.append(["", "", "", "", "", "Numbering direction:>", "", "LEFT-TO-RIGHT"])
    rows.append(["", "", "", "", "", "NDE Laboratory:----->", "", "Synthetic Lab"])
    rows.append([])
    rows.append([])
    tube_row = ["", "TUBE NUMBERS  along the top. -------->", "", "", ""] + [
        str(i + 1) for i in range(num_tubes)
    ]
    rows.append(tube_row)
    rows.append([])
    for tech, label, left_vals, cntr_vals, rght_vals in blocks:
        rows.append(["UT Tech Name:   ", "", label, "", "    LEFT "] + list(left_vals))
        rows.append([tech, "", "", "", "    CNTR "] + list(cntr_vals))
        rows.append(["", "", "", "", "    RGHT "] + list(rght_vals))

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def test_metadata_matches_labeled_values():
    samples = _new_samples()
    assert samples, "no New samples found under examples/tds/New"
    filepath = samples[0]
    rows = _read_rows(filepath)

    expected_company = _independent_label_value(rows, "Company Name:")
    expected_mill = _independent_label_value(rows, "Mill Location:")
    expected_boiler = _independent_label_value(rows, "Boiler Name:")
    expected_date = _independent_label_value(rows, "Inspection Date:")
    expected_section = _independent_label_value(rows, "Boiler Section:")
    expected_nde = _independent_label_value(rows, "NDE Laboratory:")
    expected_num_tubes = int(_independent_label_value(rows, "Number of tubes:"))
    expected_direction_raw = _independent_label_value(rows, "Numbering direction:")
    expected_direction = _independent_direction(expected_direction_raw)

    result = parse_tds_new_file(filepath)

    assert result.company_name == expected_company
    assert result.mill_location == expected_mill
    assert result.boiler_name == expected_boiler
    assert result.inspection_date == expected_date
    assert result.boiler_section == expected_section
    assert result.nde_laboratory == expected_nde
    assert result.num_tubes == expected_num_tubes
    assert result.numbering_direction == expected_direction


def test_reading_suffix_preserved(tmp_path):
    path = tmp_path / "suffix.CSV"
    _write_synthetic_csv(
        path,
        num_tubes=2,
        blocks=[
            ("ATS", "Test Elevation", ["14V", "100"], ["101", "102"], ["103", "104"]),
        ],
    )

    result = parse_tds_new_file(path)

    assert result.elevations[0].left[0] == "014V"
    from app.converters.team_parser import convert_team_reading

    assert convert_team_reading("14V") == "014V"


def test_has_data_flag_correctness(tmp_path):
    path = tmp_path / "has_data.CSV"
    blank = ["", "", ""]
    measured = ["250", "251", "252"]
    _write_synthetic_csv(
        path,
        num_tubes=3,
        blocks=[
            ("ATS", "Blank Block", blank, blank, blank),
            ("ATS", "Measured Block", measured, blank, blank),
        ],
    )

    result = parse_tds_new_file(path)

    assert len(result.elevations) == 2
    assert result.elevations[0].has_data is False
    assert result.elevations[1].has_data is True


def test_tech_code_read_from_file():
    samples = _new_samples()
    assert samples, "no New samples found under examples/tds/New"
    filepath = samples[0]
    rows = _read_rows(filepath)

    tube_row_idx = None
    for i, row in enumerate(rows):
        if any("along the top" in cell for cell in row):
            tube_row_idx = i
            break
    assert tube_row_idx is not None

    # Independently locate the first LEFT/CNTR/RGHT block after the tube
    # row and read the CNTR row's column-A tech value directly.
    expected_tech_code = None
    idx = tube_row_idx + 1
    while idx + 2 < len(rows):
        left_row, cntr_row, rght_row = rows[idx], rows[idx + 1], rows[idx + 2]

        def marker(row):
            return row[4].strip() if len(row) > 4 else ""

        if marker(left_row) == "LEFT" and marker(cntr_row) == "CNTR" and marker(rght_row) == "RGHT":
            expected_tech_code = cntr_row[0].strip() if cntr_row else ""
            break
        idx += 1
    assert expected_tech_code, "no elevation block with a tech code found in sample"

    result = parse_tds_new_file(filepath)
    matching = [e for e in result.elevations if e.tech_code == expected_tech_code]
    assert matching, f"no parsed elevation had tech_code {expected_tech_code!r}"


def test_all_new_samples_parse_without_error():
    samples = _new_samples()
    assert samples, "no New samples found under examples/tds/New"
    for filepath in samples:
        result = parse_tds_new_file(filepath)
        assert isinstance(result, TDSNewParseResult)
        assert len(result.elevations) >= 1
        assert result.company_name.strip() != ""
        for elevation in result.elevations:
            assert isinstance(elevation, TDSElevation)


def test_parse_invalid_file_raises():
    with pytest.raises(TDSParseError):
        parse_tds_new_file("nonexistent_tds_file_that_does_not_exist.CSV")
