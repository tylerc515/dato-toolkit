"""Write ATS parse results as Standard Format CSV files for TRACE import."""
from __future__ import annotations

import csv
import logging
from pathlib import Path

from app.converters.ats_parser import ATSParseResult

logger = logging.getLogger(__name__)

_FORMAT_COMMENT = (
    "This Excel file is in the 'Standard Format' for sharing the raw UT data between the labs."
)
_FONT_COMMENT = (
    "Best viewed if Excel's Default Font is set to either  ARIAL-size 10  or  CALIBRI-size 11."
)


def _make_row(n_cols: int, assignments: dict[int, str]) -> list[str]:
    row = [""] * n_cols
    for col_idx, val in assignments.items():
        if col_idx < n_cols:
            row[col_idx] = val
    return row


def write_standard_format(
    result: ATSParseResult,
    flag_mapping: dict[str, str],
    output_path: str | Path,
) -> None:
    """Write an ATSParseResult as a Standard Format CSV file.

    Args:
        result: parsed ATS data
        flag_mapping: {ats_code: standard_format_code} — the confirmed mapping
        output_path: where to write the CSV
    """
    n_cols = max(8, 5 + result.num_tubes)
    rows: list[list[str]] = []

    # Rows 0-1: format comments at col E (index 4)
    rows.append(_make_row(n_cols, {4: _FORMAT_COMMENT}))
    rows.append(_make_row(n_cols, {4: _FONT_COMMENT}))

    # Rows 2-3: blank
    rows.append([""] * n_cols)
    rows.append([""] * n_cols)

    # Rows 4-11: metadata (label at col F/5, value at col H/7)
    for label, value in [
        ("Company Name:---->",        result.company_name),
        ("Mill Location:---->",       result.mill_location),
        ("Boiler Name:---->",         result.boiler_name),
        ("Inspection Date:---->",     result.inspection_date),
        ("Boiler Section:---->",      result.boiler_section),
        ("Number of Tubes:---->",     str(result.num_tubes)),
        ("Numbering Direction:---->", result.numbering_direction),
        ("NDE Laboratory:---->",      result.nde_laboratory),
    ]:
        rows.append(_make_row(n_cols, {5: label, 7: value}))

    # Rows 12-13: blank
    rows.append([""] * n_cols)
    rows.append([""] * n_cols)

    # Row 14: tube numbers — top
    tube_row: dict[int, str] = {1: "TUBE NUMBERS along the top.---->"}
    for i, n in enumerate(result.tube_numbers):
        tube_row[5 + i] = str(n)
    rows.append(_make_row(n_cols, tube_row))

    # Row 15: blank
    rows.append([""] * n_cols)

    # Elevation blocks (3 rows each)
    for elevation in result.elevations:
        # Sub-row 1: UT Tech Name / label / LEFT / readings
        r1: dict[int, str] = {0: "UT Tech Name:", 2: elevation.label, 4: "LEFT"}
        for i, val in enumerate(elevation.left):
            r1[5 + i] = val
        rows.append(_make_row(n_cols, r1))

        # Sub-row 2: tech code / CNTR / readings
        r2: dict[int, str] = {0: elevation.tech_code or "ATS", 4: "CNTR"}
        for i, val in enumerate(elevation.cntr):
            r2[5 + i] = val
        rows.append(_make_row(n_cols, r2))

        # Sub-row 3: RGHT / readings
        r3: dict[int, str] = {4: "RGHT"}
        for i, val in enumerate(elevation.rght):
            r3[5 + i] = val
        rows.append(_make_row(n_cols, r3))

    # Repeat tube numbers — bottom
    tube_row_bottom: dict[int, str] = {1: "TUBE NUMBERS along the bottom.---->"}
    for i, n in enumerate(result.tube_numbers):
        tube_row_bottom[5 + i] = str(n)
    rows.append(_make_row(n_cols, tube_row_bottom))

    # Blank row after tube numbers
    rows.append([""] * n_cols)

    # Flag legend: one row per flag at col B (index 1)
    for ats_code, std_code in flag_mapping.items():
        description = result.ats_flags.get(ats_code, ats_code)
        r = [""] * n_cols
        r[1] = f" {std_code}    means {description}."
        rows.append(r)

    out = Path(output_path)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
