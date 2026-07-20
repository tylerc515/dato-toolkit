"""Tests for the TDS old-format (pre-5.3) CSV parser.

Real sample files live under examples/tds/Old/ (local/untracked, gitignored,
mixed .csv/.CSV extensions, spaces in filenames). Tests must never hardcode
a client name/value: expected values are always read straight from the
sample file with an independent csv read, then compared against what the
parser returns. Where a fully deterministic check requires values that
cannot collide with real (client) data - e.g. proving a discarded column's
value truly never leaks into output - a synthetic in-memory CSV is used
instead, built from the same confirmed positional layout.
"""
from __future__ import annotations

import csv
import dataclasses
import os
import types

import pytest

from app.converters.standard_format_writer import write_standard_format
from app.converters.team_parser import convert_team_reading
from app.converters.tds_new_parser import TDSElevation, TDSParseError
from app.converters.tds_old_parser import TDSOldParseResult, parse_tds_old_file

OLD_DIR = "examples/tds/Old"

# Positional layout constants, mirrored independently here (not imported
# from the parser) so these tests are a real independent check rather than
# a tautology against the parser's own constants.
_ROW_COMPANY_NAME = 6
_ROW_MILL_LOCATION = 7
_ROW_BOILER_NAME = 8
_ROW_INSPECTION_DATE = 9
_ROW_BOILER_SECTION = 10
_METADATA_VALUE_COL = 5
_LABEL_COL = 0
_MARKER_COL = 3
_READING_COL_START = 4


def _old_samples() -> list[str]:
    return [
        os.path.join(OLD_DIR, f)
        for f in os.listdir(OLD_DIR)
        if f.lower().endswith(".csv") and not f.startswith("~$")
    ]


def _read_rows(filepath: str) -> list[list[str]]:
    with open(filepath, "r", encoding="utf-8", errors="ignore", newline="") as f:
        return list(csv.reader(f))


def _cell(row: list[str], idx: int) -> str:
    return row[idx] if idx < len(row) else ""


def _independent_direction(rows: list[list[str]]) -> str | None:
    for row in rows[:10]:
        for cell in row:
            upper = cell.upper()
            if "LEFT-TO-RIGHT" in upper:
                return "Left-to-Right"
            if "RIGHT-TO-LEFT" in upper:
                return "Right-to-Left"
    return None


def _independent_tube_row_index(rows: list[list[str]]) -> int | None:
    for i, row in enumerate(rows):
        if any("along the top" in cell for cell in row):
            return i
    return None


def _independent_tube_numbers(rows: list[list[str]]) -> list[int]:
    tube_row_idx = _independent_tube_row_index(rows)
    assert tube_row_idx is not None
    row = rows[tube_row_idx]
    numbers: list[int] = []
    idx = _READING_COL_START
    while True:
        cell = _cell(row, idx).strip()
        if not cell:
            break
        try:
            numbers.append(int(cell))
        except ValueError:
            break
        idx += 1
    return numbers


def _independent_first_block(rows: list[list[str]]) -> tuple[list[str], list[str], list[str]]:
    """Scan forward from the tube row for the first LEFT/CNTR/RGHT triple,
    returning the three raw rows. Reimplemented separately from the parser
    to keep this an independent check."""
    tube_row_idx = _independent_tube_row_index(rows)
    assert tube_row_idx is not None
    idx = tube_row_idx + 1
    while idx + 2 < len(rows):
        left_row, cntr_row, rght_row = rows[idx], rows[idx + 1], rows[idx + 2]
        if (
            _cell(left_row, _MARKER_COL).strip() == "LEFT"
            and _cell(cntr_row, _MARKER_COL).strip() == "CNTR"
            and _cell(rght_row, _MARKER_COL).strip() == "RGHT"
        ):
            return left_row, cntr_row, rght_row
        idx += 1
    raise AssertionError("no LEFT/CNTR/RGHT block found")


def _write_synthetic_old_csv(
    path,
    num_tubes: int,
    blocks: list[tuple[str, list[str], list[str], list[str]]],
    direction: str = "Left-to-Right",
    min_allowable: str = "999",
    company: str = "SyntheticCo",
    mill: str = "SyntheticMill",
    boiler: str = "SyntheticBoiler",
    date: str = "January 2024",
    section: str = "SYNTHETIC SECTION",
) -> None:
    """blocks: list of (label_line_1, left_vals, cntr_vals, rght_vals) where
    label_line_1/left/cntr/rght vals are lists of length num_tubes of raw
    cell strings. The CNTR row's Minimum/Allowable column (col C / index 2)
    is always set to `min_allowable`, matching the confirmed real layout."""
    rows: list[list[str]] = []
    rows.append([])
    rows.append(["", "", "", "", "This file was create by the TCRI TDS."])
    rows.append(["", "", "", "", "Best viewed if..."])
    rows.append([])
    rows.append([
        "", "", "", "",
        f"The tube numbering direction for this Boiler Section was from {direction}.",
    ])
    rows.append([])
    rows.append(["", "", "", "", "", company])
    rows.append(["", "", "", "", "", mill])
    rows.append(["", "", "", "", "", boiler])
    rows.append(["", "", "", "", "", date])
    rows.append(["", "", "", "", "", section])
    rows.append([])
    tube_row = ["TUBE NUMBERS  along the top. -------->", "", "", ""] + [
        str(i + 1) for i in range(num_tubes)
    ]
    rows.append(tube_row)
    rows.append(["Elevations down the side.    "])
    rows.append([])
    rows.append(["", "", "Minimum", ""])
    rows.append(["", "", "Allowable", ""])
    for label, left_vals, cntr_vals, rght_vals in blocks:
        rows.append([label, "", "", "LEFT"] + list(left_vals))
        rows.append(["", "", min_allowable, "CNTR"] + list(cntr_vals))
        rows.append(["", "", "", "RGHT"] + list(rght_vals))
        rows.append([])

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def test_positional_metadata_correct():
    samples = _old_samples()
    assert samples, "no Old samples found under examples/tds/Old"
    for filepath in samples:
        rows = _read_rows(filepath)

        expected_company = _cell(rows[_ROW_COMPANY_NAME], _METADATA_VALUE_COL).strip()
        expected_mill = _cell(rows[_ROW_MILL_LOCATION], _METADATA_VALUE_COL).strip()
        expected_boiler = _cell(rows[_ROW_BOILER_NAME], _METADATA_VALUE_COL).strip()
        expected_date = _cell(rows[_ROW_INSPECTION_DATE], _METADATA_VALUE_COL).strip()
        expected_section = _cell(rows[_ROW_BOILER_SECTION], _METADATA_VALUE_COL).strip()
        expected_direction = _independent_direction(rows)
        assert expected_direction is not None, f"no direction sentence in {filepath}"

        result = parse_tds_old_file(filepath)

        assert result.company_name == expected_company, filepath
        assert result.mill_location == expected_mill, filepath
        assert result.boiler_name == expected_boiler, filepath
        assert result.inspection_date == expected_date, filepath
        assert result.boiler_section == expected_section, filepath
        assert result.numbering_direction == expected_direction, filepath


def test_tube_number_row_found_despite_varying_label_wording():
    samples = _old_samples()
    assert samples, "no Old samples found under examples/tds/Old"

    variants_seen: dict[str, str] = {}
    for filepath in samples:
        rows = _read_rows(filepath)
        tube_row_idx = _independent_tube_row_index(rows)
        assert tube_row_idx is not None, f"tube row not found in {filepath}"
        signal_cell = next(
            cell for cell in rows[tube_row_idx] if "along the top" in cell
        )
        if "PLATEN NUMBERS" in signal_cell:
            variants_seen.setdefault("PLATEN NUMBERS", filepath)
        elif "TUBE NUMBERS" in signal_cell:
            variants_seen.setdefault("TUBE NUMBERS", filepath)
        elif "TUBES" in signal_cell:
            variants_seen.setdefault("TUBES", filepath)

        expected_tube_numbers = _independent_tube_numbers(rows)
        result = parse_tds_old_file(filepath)
        assert result.num_tubes == len(expected_tube_numbers), filepath
        assert result.tube_numbers == expected_tube_numbers, filepath

    # All three known real-sample wording variants must be represented.
    assert "TUBE NUMBERS" in variants_seen
    assert "TUBES" in variants_seen
    assert "PLATEN NUMBERS" in variants_seen


def test_grid_column_shift_parsed_correctly():
    samples = _old_samples()
    assert samples, "no Old samples found under examples/tds/Old"
    filepath = samples[0]
    rows = _read_rows(filepath)

    expected_tube_numbers = _independent_tube_numbers(rows)
    num_tubes = len(expected_tube_numbers)
    left_row, cntr_row, rght_row = _independent_first_block(rows)

    expected_left = [
        convert_team_reading(_cell(left_row, _READING_COL_START + k))
        for k in range(num_tubes)
    ]
    expected_cntr = [
        convert_team_reading(_cell(cntr_row, _READING_COL_START + k))
        for k in range(num_tubes)
    ]
    expected_rght = [
        convert_team_reading(_cell(rght_row, _READING_COL_START + k))
        for k in range(num_tubes)
    ]

    result = parse_tds_old_file(filepath)
    first = result.elevations[0]

    assert len(first.left) == num_tubes
    assert len(first.cntr) == num_tubes
    assert len(first.rght) == num_tubes
    assert first.left == expected_left
    assert first.cntr == expected_cntr
    assert first.rght == expected_rght


def test_minimum_allowable_discarded(tmp_path):
    # No field on the dataclass carries a Minimum/Allowable-shaped value at all.
    field_names = {f.name for f in dataclasses.fields(TDSOldParseResult)}
    assert "minimum" not in field_names
    assert "allowable" not in field_names
    assert "min_allowable" not in field_names

    # Stronger check: a synthetic file with a sentinel Minimum/Allowable
    # value that never appears among real readings must never surface it,
    # neither on the parsed result nor after round-tripping through
    # write_standard_format.
    path = tmp_path / "min_allowable.csv"
    sentinel = "999"
    _write_synthetic_old_csv(
        path,
        num_tubes=3,
        min_allowable=sentinel,
        blocks=[
            ("Elevation One", ["100", "101", "102"], ["103", "104", "105"], ["106", "107", "108"]),
        ],
    )

    result = parse_tds_old_file(path)

    for elevation in result.elevations:
        assert sentinel not in elevation.left
        assert sentinel not in elevation.cntr
        assert sentinel not in elevation.rght

    adapter = types.SimpleNamespace(
        company_name=result.company_name,
        mill_location=result.mill_location,
        boiler_name=result.boiler_name,
        inspection_date=result.inspection_date,
        boiler_section=result.boiler_section,
        num_tubes=result.num_tubes,
        numbering_direction=result.numbering_direction,
        nde_laboratory="Test Lab",
        tube_numbers=result.tube_numbers,
        elevations=result.elevations,
    )
    output_path = tmp_path / "standard_format_output.csv"
    write_standard_format(adapter, comment_code_mapping={}, output_path=output_path)

    output_text = output_path.read_text(encoding="utf-8")
    assert sentinel not in output_text


def test_direction_left_to_right():
    samples = _old_samples()
    assert samples, "no Old samples found under examples/tds/Old"
    filepath = samples[0]
    rows = _read_rows(filepath)
    expected_direction = _independent_direction(rows)
    assert expected_direction == "Left-to-Right", (
        f"expected sample {filepath} to use Left-to-Right for this test"
    )

    result = parse_tds_old_file(filepath)
    assert result.numbering_direction == "Left-to-Right"


def test_direction_right_to_left_synthetic(tmp_path):
    path = tmp_path / "right_to_left.csv"
    _write_synthetic_old_csv(
        path,
        num_tubes=2,
        direction="Right-to-Left",
        blocks=[
            ("Elevation One", ["100", "101"], ["102", "103"], ["104", "105"]),
        ],
    )

    result = parse_tds_old_file(path)

    assert result.numbering_direction == "Right-to-Left"


def test_all_old_samples_parse():
    samples = _old_samples()
    assert samples, "no Old samples found under examples/tds/Old"
    for filepath in samples:
        result = parse_tds_old_file(filepath)
        assert isinstance(result, TDSOldParseResult)
        assert len(result.elevations) >= 1, filepath
        assert result.company_name.strip() != "", filepath
        for elevation in result.elevations:
            assert isinstance(elevation, TDSElevation)
            assert elevation.tech_code == "TDS"


def test_parse_invalid_file_raises():
    with pytest.raises(TDSParseError):
        parse_tds_old_file("nonexistent_tds_old_file_that_does_not_exist.CSV")
