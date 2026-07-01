"""Write ATS parse results as Standard Format CSV files for TRACE import."""
from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

from app.converters.ats_parser import ATSParseResult

logger = logging.getLogger(__name__)

_FORMAT_COMMENT = (
    "This Excel file is in the 'Standard Format' for sharing the raw UT data between the labs."
)
_FONT_COMMENT = (
    "Best viewed if Excel's Default Font is set to either  ARIAL-size 10  or  CALIBRI-size 11."
)

_legend_block_cache: list[list[str]] | None = None


_RVN_SYMBOLS: frozenset[str] = frozenset({"R", "V", "N"})


def _row_has_rvn_symbol(row: list[str]) -> bool:
    """Return True if any cell in the row has a leading symbol of R, V, or N."""
    for cell in row:
        parts = cell.strip().split()
        if parts and parts[0] in _RVN_SYMBOLS:
            return True
    return False


def load_standard_legend_block() -> list[list[str]]:
    """Read the fixed, universal legend block from the bundled reference file.

    Returns a list of rows (each row a list of cell values). Row 0 is the
    blank separator that follows the tube-numbers footer. R, V, and N rows
    are excluded because they are reading-suffix codes, not flag symbols.
    Trailing all-empty rows are also removed. Cached after first read.
    """
    global _legend_block_cache
    if _legend_block_cache is not None:
        return _legend_block_cache

    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent.parent))
    path = base / "examples" / "standard-format" / "Standard-Sample_Left-to-Right.csv"

    with path.open(newline="", encoding="utf-8") as f:
        all_rows = list(csv.reader(f))

    # Find the second occurrence of a cell containing "TUBE NUMBERS along the".
    found = 0
    second_index = -1
    for i, row in enumerate(all_rows):
        if any("TUBE NUMBERS along the" in cell for cell in row):
            found += 1
            if found == 2:
                second_index = i
                break

    if second_index == -1:
        raise ValueError(
            "Could not find second 'TUBE NUMBERS along the' row in reference file"
        )

    # Include the blank separator row immediately after the footer (second_index + 1),
    # then take everything to EOF.
    block = all_rows[second_index + 1:]

    # Remove rows that carry R, V, or N reading-suffix symbols.
    # The blank separator at position 0 has no leading symbol, so it is preserved.
    block = [row for row in block if not _row_has_rvn_symbol(row)]

    # Strip trailing all-empty rows left after removing the R/V/N entries.
    while block and all(c == "" for c in block[-1]):
        block.pop()

    _legend_block_cache = block
    return _legend_block_cache


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
        flag_mapping: {ats_code: standard_format_code} - the confirmed mapping
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

    # Row 14: tube numbers - top
    tube_row: dict[int, str] = {1: "TUBE NUMBERS along the top.---->"}
    for i, n in enumerate(result.tube_numbers):
        tube_row[5 + i] = str(n)
    rows.append(_make_row(n_cols, tube_row))

    # Row 15: blank
    rows.append([""] * n_cols)

    def _translate(val: str) -> str:
        """Substitute known ATS flag codes with Standard Format equivalents."""
        if not val:
            return val
        translated = flag_mapping.get(val, val)
        if translated == val and not val.isdigit():
            logger.warning("Unrecognized flag code in reading: %r", val)
        return translated

    # Elevation blocks (3 rows each)
    for elevation in result.elevations:
        # Sub-row 1: UT Tech Name / label / LEFT / readings
        r1: dict[int, str] = {0: "UT Tech Name:", 2: elevation.label, 4: "LEFT"}
        for i, val in enumerate(elevation.left):
            r1[5 + i] = _translate(val)
        rows.append(_make_row(n_cols, r1))

        # Sub-row 2: tech code / CNTR / readings
        # Single uppercase letter is a crew/shift code - write "ATS" instead
        tech_code = elevation.tech_code
        if not tech_code or (len(tech_code) == 1 and tech_code.isupper()):
            tech_code = "ATS"
        r2: dict[int, str] = {0: tech_code, 4: "CNTR"}
        for i, val in enumerate(elevation.cntr):
            r2[5 + i] = _translate(val)
        rows.append(_make_row(n_cols, r2))

        # Sub-row 3: RGHT / readings
        r3: dict[int, str] = {4: "RGHT"}
        for i, val in enumerate(elevation.rght):
            r3[5 + i] = _translate(val)
        rows.append(_make_row(n_cols, r3))

    # Repeat tube numbers - bottom
    tube_row_bottom: dict[int, str] = {1: "TUBE NUMBERS along the bottom.---->"}
    for i, n in enumerate(result.tube_numbers):
        tube_row_bottom[5 + i] = str(n)
    rows.append(_make_row(n_cols, tube_row_bottom))

    # Fixed universal legend - always written in full, every time
    for legend_row in load_standard_legend_block():
        # Pad or trim each legend row to match n_cols
        padded = list(legend_row) + [""] * n_cols
        rows.append(padded[:n_cols])

    out = Path(output_path)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
