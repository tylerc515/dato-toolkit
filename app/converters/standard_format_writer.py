"""Write ATS parse results as Standard Format CSV files for TRACE import."""
from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

from app.converters.ats_parser import ATSParseResult
from app.converters.flag_mapper import STANDARD_SYMBOL_DESCRIPTIONS

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
    excel_safe: bool = False,
) -> None:
    """Write an ATSParseResult as a Standard Format CSV file.

    Args:
        result: parsed ATS data
        flag_mapping: {ats_code: standard_format_code} - the confirmed mapping
        output_path: where to write the CSV
        excel_safe: when True, wrap numeric readings as ="value" so Excel
            preserves leading zeros instead of converting them to numbers
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

    seen_symbols: list[str] = []
    seen_set: set[str] = set()

    def _translate(val: str) -> str:
        """Substitute known ATS flag codes with Standard Format equivalents."""
        if not val:
            return val
        translated = flag_mapping.get(val, val)
        if translated == val and not val.isdigit():
            logger.warning("Unrecognized flag code in reading: %r", val)
        if translated and not translated.isdigit() and translated not in seen_set:
            seen_symbols.append(translated)
            seen_set.add(translated)
        return translated

    def _excel_fmt(val: str) -> str:
        """Wrap all-digit readings in Excel text formula to preserve leading zeros."""
        if excel_safe and val.isdigit():
            return f'="{val}"'
        return val

    # Elevation blocks (3 rows each)
    for elevation in result.elevations:
        # Sub-row 1: UT Tech Name / label / LEFT / readings
        r1: dict[int, str] = {0: "UT Tech Name:", 2: elevation.label, 4: "LEFT"}
        for i, val in enumerate(elevation.left):
            translated = _translate(val)
            # legend scanning uses translated value (before excel formatting)
            r1[5 + i] = _excel_fmt(translated)
        rows.append(_make_row(n_cols, r1))

        # Sub-row 2: tech code / CNTR / readings
        # Single uppercase letter is a crew/shift code - write "ATS" instead
        tech_code = elevation.tech_code
        if not tech_code or (len(tech_code) == 1 and tech_code.isupper()):
            tech_code = "ATS"
        r2: dict[int, str] = {0: tech_code, 4: "CNTR"}
        for i, val in enumerate(elevation.cntr):
            translated = _translate(val)
            # legend scanning uses translated value (before excel formatting)
            r2[5 + i] = _excel_fmt(translated)
        rows.append(_make_row(n_cols, r2))

        # Sub-row 3: RGHT / readings
        r3: dict[int, str] = {4: "RGHT"}
        for i, val in enumerate(elevation.rght):
            translated = _translate(val)
            # legend scanning uses translated value (before excel formatting)
            r3[5 + i] = _excel_fmt(translated)
        rows.append(_make_row(n_cols, r3))

    # Repeat tube numbers — bottom
    tube_row_bottom: dict[int, str] = {1: "TUBE NUMBERS along the bottom.---->"}
    for i, n in enumerate(result.tube_numbers):
        tube_row_bottom[5 + i] = str(n)
    rows.append(_make_row(n_cols, tube_row_bottom))

    # Dynamic legend - only write when flag symbols actually appear in the output
    if seen_symbols:
        rows.append([""] * n_cols)  # blank separator before legend
        for symbol in seen_symbols:
            description = STANDARD_SYMBOL_DESCRIPTIONS.get(symbol)
            if description is None:
                logger.warning("No description for symbol %r in STANDARD_SYMBOL_DESCRIPTIONS", symbol)
                description = symbol
            r = [""] * n_cols
            r[1] = f" {symbol}    means {description}."
            rows.append(r)

    out = Path(output_path)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    if excel_safe:
        # csv.writer quotes ="234" as "=""234""" because the value contains double-quotes.
        # Post-process to restore the literal ="value" form so Excel recognizes the formula.
        text = out.read_text(encoding="utf-8")
        text = re.sub(r'"=""(\d+)"""', lambda m: f'="{m.group(1)}"', text)
        out.write_text(text, encoding="utf-8")
