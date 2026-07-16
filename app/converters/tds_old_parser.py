"""TDS "old" (pre-5.3) format CSV parser.

Old-format TDS exports have NO labeled metadata (unlike New/5.3+): the
company/mill/boiler/date/section values are positional, centered in a
fixed column a few rows below a "tube numbering direction" sentence. The
elevation grid itself is shifted one column left of the New format and
carries an extra "Minimum/Allowable" column that must never be treated
as reading data. Read with the `csv` module (encoding="utf-8",
errors="ignore"), NOT openpyxl.

`TDSElevation` and `TDSParseError` are shared with the New-format parser
and imported from there (app.converters.tds_new_parser) rather than
redefined here.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from app.converters.team_parser import convert_team_reading
from app.converters.tds_new_parser import TDSElevation, TDSParseError

# --- Positional metadata rows (0-indexed) -----------------------------
# Old-format files carry no field labels at all. Verified stable across
# 7 real Old-format samples spanning wall, superheater ("PLATEN"), and
# pass section types (RB 1 FRONT WALL UT, RB 1 RIGHT WALL, RB 1 SH
# LOOPS, RB 1 GEN BENDS, RB 1 PASS B LANE, RB 1 PASS B OPENINGS, RB 1
# PASS E LANE): the 5 metadata values always land on rows 6-10, in this
# order, centered in column F (0-indexed col 5, comment/prose column).
_ROW_COMPANY_NAME = 6
_ROW_MILL_LOCATION = 7
_ROW_BOILER_NAME = 8
_ROW_INSPECTION_DATE = 9
_ROW_BOILER_SECTION = 10
_METADATA_VALUE_COL = 5   # column F, 0-indexed

# The "tube numbering direction" sentence was confirmed at row 4 (0-indexed)
# across all inspected samples, but is located by content match (not a
# hardcoded index) for resilience against minor row-count drift.
_DIRECTION_SCAN_ROWS = 10
_DIRECTION_PATTERN = re.compile(r"(LEFT-TO-RIGHT|RIGHT-TO-LEFT)", re.IGNORECASE)

# Tube-number row: located by the "along the top" substring (never a fixed
# row index) because the label wording itself varies across samples:
# "TUBE NUMBERS along the top", "TUBES along the top", "PLATEN NUMBERS
# along the top" (superheater sections). Matching "along the top" (and
# not "along the bottom", which also appears later in every file) picks
# out the header instance only.
_TUBE_ROW_SIGNAL = "along the top"
_TUBE_NUMBER_COL_START = 4   # column E, 0-indexed

# --- Grid layout: one column LEFT of the New format --------------------
# New format:  label col C(2), Minimum/Allowable N/A, marker col E(4), readings F(5)+
# Old format:  label col A(0), Minimum/Allowable col C(2) [discarded],
#              marker col D(3), readings col E(4)+
_LABEL_COL = 0
_MIN_ALLOWABLE_COL = 2   # numeric threshold per block; never surfaced/parsed
_MARKER_COL = 3
_READING_COL_START = 4


@dataclass
class TDSOldParseResult:
    company_name: str
    mill_location: str
    boiler_name: str
    inspection_date: str
    boiler_section: str
    num_tubes: int
    numbering_direction: str   # "Left-to-Right" / "Right-to-Left"
    tube_numbers: list[int]
    elevations: list[TDSElevation]
    # NO nde_laboratory field - Old format never contains it; the user
    # supplies it at conversion time (later UI task).


@dataclass
class TDSOldConversionInput:
    """A TDSOldParseResult plus the user-supplied NDE Laboratory, shaped
    for write_standard_format(). Built per file at conversion time."""
    company_name: str
    mill_location: str
    boiler_name: str
    inspection_date: str
    boiler_section: str
    nde_laboratory: str        # supplied by the user (Old files lack it)
    num_tubes: int
    numbering_direction: str
    tube_numbers: list[int]
    elevations: list[TDSElevation]


def old_conversion_input(
    result: TDSOldParseResult, nde_laboratory: str
) -> TDSOldConversionInput:
    """Build a TDSOldConversionInput from a parsed TDSOldParseResult plus the
    user-supplied NDE Laboratory value (Old-format files never contain it)."""
    return TDSOldConversionInput(
        company_name=result.company_name,
        mill_location=result.mill_location,
        boiler_name=result.boiler_name,
        inspection_date=result.inspection_date,
        boiler_section=result.boiler_section,
        nde_laboratory=nde_laboratory,
        num_tubes=result.num_tubes,
        numbering_direction=result.numbering_direction,
        tube_numbers=result.tube_numbers,
        elevations=result.elevations,
    )


def _cell(row: list[str], idx: int) -> str:
    """Safe positional cell access; short/ragged CSV rows return ""."""
    return row[idx] if idx < len(row) else ""


def _normalize_direction(raw: str) -> str:
    match = _DIRECTION_PATTERN.search(raw.upper())
    if match:
        token = match.group(1)
        return "Left-to-Right" if token == "LEFT-TO-RIGHT" else "Right-to-Left"
    return raw.strip()


def _find_direction(rows: list[list[str]], filename: str) -> str:
    for row in rows[:_DIRECTION_SCAN_ROWS]:
        for cell in row:
            if _DIRECTION_PATTERN.search(cell.upper()):
                return _normalize_direction(cell)
    raise TDSParseError(f"'{filename}': tube numbering direction sentence not found")


def _find_tube_row_index(rows: list[list[str]]) -> int | None:
    for i, row in enumerate(rows):
        if any(_TUBE_ROW_SIGNAL in cell for cell in row):
            return i
    return None


def _is_elevation_block(left_row: list[str], cntr_row: list[str], rght_row: list[str]) -> bool:
    return (
        _cell(left_row, _MARKER_COL).strip() == "LEFT"
        and _cell(cntr_row, _MARKER_COL).strip() == "CNTR"
        and _cell(rght_row, _MARKER_COL).strip() == "RGHT"
    )


def _block_label(left_row: list[str], cntr_row: list[str], rght_row: list[str]) -> str:
    parts = []
    for row in (left_row, cntr_row, rght_row):
        fragment = _cell(row, _LABEL_COL).strip()
        if fragment:
            parts.append(fragment)
    return " ".join(parts)


def _block_readings(row: list[str], num_tubes: int) -> list[str]:
    return [
        convert_team_reading(_cell(row, _READING_COL_START + k))
        for k in range(num_tubes)
    ]


def parse_tds_old_file(filepath: str | Path) -> TDSOldParseResult:
    """Parse a TDS old-format (pre-5.3) CSV file into a TDSOldParseResult.

    Raises:
        TDSParseError: if the file cannot be opened, the direction sentence
            or positional metadata rows are missing, the tube-number row
            cannot be found, or no elevation blocks are found.
    """
    path = Path(filepath)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            rows = list(csv.reader(f))
    except OSError as exc:
        raise TDSParseError(f"Cannot open '{path.name}': {exc}") from exc

    numbering_direction = _find_direction(rows, path.name)

    max_meta_row = max(
        _ROW_COMPANY_NAME, _ROW_MILL_LOCATION, _ROW_BOILER_NAME,
        _ROW_INSPECTION_DATE, _ROW_BOILER_SECTION,
    )
    if len(rows) <= max_meta_row:
        raise TDSParseError(f"'{path.name}': file too short for positional metadata rows")

    company_name = _cell(rows[_ROW_COMPANY_NAME], _METADATA_VALUE_COL).strip()
    mill_location = _cell(rows[_ROW_MILL_LOCATION], _METADATA_VALUE_COL).strip()
    boiler_name = _cell(rows[_ROW_BOILER_NAME], _METADATA_VALUE_COL).strip()
    inspection_date = _cell(rows[_ROW_INSPECTION_DATE], _METADATA_VALUE_COL).strip()
    boiler_section = _cell(rows[_ROW_BOILER_SECTION], _METADATA_VALUE_COL).strip()

    missing = [
        name for name, value in [
            ("company_name", company_name),
            ("mill_location", mill_location),
            ("boiler_name", boiler_name),
            ("inspection_date", inspection_date),
            ("boiler_section", boiler_section),
        ] if not value
    ]
    if missing:
        raise TDSParseError(f"'{path.name}': missing positional metadata fields {missing}")

    tube_row_idx = _find_tube_row_index(rows)
    if tube_row_idx is None:
        raise TDSParseError(f"'{path.name}': tube number row not found")
    tube_row = rows[tube_row_idx]

    tube_numbers: list[int] = []
    idx = _TUBE_NUMBER_COL_START
    while True:
        cell = _cell(tube_row, idx).strip()
        if not cell:
            break
        try:
            tube_numbers.append(int(cell))
        except ValueError:
            break
        idx += 1

    num_tubes = len(tube_numbers)
    if num_tubes == 0:
        raise TDSParseError(f"'{path.name}': no tube numbers found in tube-number row")

    elevations: list[TDSElevation] = []
    idx = tube_row_idx + 1
    while idx + 2 < len(rows):
        left_row, cntr_row, rght_row = rows[idx], rows[idx + 1], rows[idx + 2]
        if not _is_elevation_block(left_row, cntr_row, rght_row):
            idx += 1
            continue

        # Minimum/Allowable numeric threshold lives at _MIN_ALLOWABLE_COL on
        # the CNTR row. It is intentionally never read into any field -
        # readings only ever come from _READING_COL_START onward.
        label = _block_label(left_row, cntr_row, rght_row)

        left = _block_readings(left_row, num_tubes)
        cntr = _block_readings(cntr_row, num_tubes)
        rght = _block_readings(rght_row, num_tubes)
        has_data = any(left) or any(cntr) or any(rght)

        elevations.append(
            TDSElevation(
                label=label,
                left=left,
                cntr=cntr,
                rght=rght,
                has_data=has_data,
            )
        )
        idx += 3

    if not elevations:
        raise TDSParseError(f"'{path.name}': no elevation blocks found")

    return TDSOldParseResult(
        company_name=company_name,
        mill_location=mill_location,
        boiler_name=boiler_name,
        inspection_date=inspection_date,
        boiler_section=boiler_section,
        num_tubes=num_tubes,
        numbering_direction=numbering_direction,
        tube_numbers=tube_numbers,
        elevations=elevations,
    )
