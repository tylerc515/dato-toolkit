"""TDS "new" (5.3+) format CSV parser.

TDS 5.3+ exports are CSV files structurally close to Standard Format
output: labeled metadata rows near the top, a tube-number row, and a
series of 3-row LEFT/CNTR/RGHT elevation blocks. Read with the `csv`
module (encoding="utf-8", errors="ignore"), NOT openpyxl.

`TDSElevation` and `TDSParseError` are shared with the Old-format parser
(app.converters.tds_old_parser imports them from here).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from app.converters.team_parser import convert_team_reading


class TDSParseError(Exception):
    """Raised when a TDS file cannot be parsed."""


@dataclass
class TDSElevation:
    label: str
    left: list[str]
    cntr: list[str]
    rght: list[str]
    has_data: bool   # True if any reading cell in this block is non-blank
    tech_code: str = "TDS"   # default so the writer never emits "TEAM"


@dataclass
class TDSNewParseResult:
    company_name: str
    mill_location: str
    boiler_name: str
    inspection_date: str
    boiler_section: str
    num_tubes: int
    numbering_direction: str   # "Left-to-Right" or "Right-to-Left"
    nde_laboratory: str
    tube_numbers: list[int]
    elevations: list[TDSElevation]


# Metadata field name -> label substring to search for. Trailing arrow
# characters/spacing vary between files, so we match on substring only.
_METADATA_LABELS = {
    "company_name": "Company Name:",
    "mill_location": "Mill Location:",
    "boiler_name": "Boiler Name:",
    "inspection_date": "Inspection Date:",
    "boiler_section": "Boiler Section:",
    "num_tubes": "Number of tubes:",
    "numbering_direction": "Numbering direction:",
    "nde_laboratory": "NDE Laboratory:",
}

_METADATA_SCAN_ROWS = 15
_TUBE_ROW_SIGNAL = "along the top"

_READING_COL_START = 5   # column F, 0-indexed
_LABEL_COL = 2            # column C, 0-indexed
_MARKER_COL = 4           # column E, 0-indexed
_TECH_COL = 0             # column A, 0-indexed


def _cell(row: list[str], idx: int) -> str:
    """Safe positional cell access; short/ragged CSV rows return ""."""
    return row[idx] if idx < len(row) else ""


def _normalize_direction(raw: str) -> str:
    upper = raw.upper()
    if "LEFT-TO-RIGHT" in upper or "LEFT TO RIGHT" in upper:
        return "Left-to-Right"
    if "RIGHT-TO-LEFT" in upper or "RIGHT TO LEFT" in upper:
        return "Right-to-Left"
    return raw.strip()


def _find_label_value(row: list[str], label_substr: str) -> str | None:
    """Return the next non-empty cell after the label cell on this row."""
    for i, cell in enumerate(row):
        if label_substr in cell:
            for j in range(i + 1, len(row)):
                if row[j].strip():
                    return row[j].strip()
            return None
    return None


def _extract_metadata(rows: list[list[str]]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for row in rows[:_METADATA_SCAN_ROWS]:
        for field, label in _METADATA_LABELS.items():
            if field in metadata:
                continue
            value = _find_label_value(row, label)
            if value is not None:
                metadata[field] = value
    return metadata


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


def parse_tds_new_file(filepath: str | Path) -> TDSNewParseResult:
    """Parse a TDS new-format (5.3+) CSV file into a TDSNewParseResult.

    Raises:
        TDSParseError: if the file cannot be opened, required metadata is
            missing, the tube-number row cannot be found, or no elevation
            blocks are found.
    """
    path = Path(filepath)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            rows = list(csv.reader(f))
    except OSError as exc:
        raise TDSParseError(f"Cannot open '{path.name}': {exc}") from exc

    metadata = _extract_metadata(rows)
    missing = [field for field in _METADATA_LABELS if field not in metadata]
    if missing:
        raise TDSParseError(f"'{path.name}': missing metadata fields {missing}")

    try:
        num_tubes = int(metadata["num_tubes"])
    except ValueError as exc:
        raise TDSParseError(
            f"'{path.name}': invalid Number of tubes value {metadata['num_tubes']!r}"
        ) from exc

    numbering_direction = _normalize_direction(metadata["numbering_direction"])

    tube_row_idx = _find_tube_row_index(rows)
    if tube_row_idx is None:
        raise TDSParseError(f"'{path.name}': tube number row not found")
    tube_row = rows[tube_row_idx]

    tube_numbers: list[int] = []
    for cell in tube_row[_READING_COL_START:_READING_COL_START + num_tubes]:
        stripped = cell.strip()
        if not stripped:
            break
        try:
            tube_numbers.append(int(stripped))
        except ValueError:
            break

    elevations: list[TDSElevation] = []
    idx = tube_row_idx + 1
    while idx + 2 < len(rows):
        left_row, cntr_row, rght_row = rows[idx], rows[idx + 1], rows[idx + 2]
        if not _is_elevation_block(left_row, cntr_row, rght_row):
            idx += 1
            continue

        tech_code = _cell(cntr_row, _TECH_COL).strip() or "TDS"
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
                tech_code=tech_code,
            )
        )
        idx += 3

    if not elevations:
        raise TDSParseError(f"'{path.name}': no elevation blocks found")

    return TDSNewParseResult(
        company_name=metadata["company_name"],
        mill_location=metadata["mill_location"],
        boiler_name=metadata["boiler_name"],
        inspection_date=metadata["inspection_date"],
        boiler_section=metadata["boiler_section"],
        num_tubes=num_tubes,
        numbering_direction=numbering_direction,
        nde_laboratory=metadata["nde_laboratory"],
        tube_numbers=tube_numbers,
        elevations=elevations,
    )
