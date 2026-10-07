"""Parsing logic for TRACE UT inspection export CSV files."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.constants import (
    ELEVATION_LABEL_COL,
    LABEL_BOILER_NAME,
    LABEL_BOILER_SECTION,
    LABEL_COMPANY_NAME,
    LABEL_INSPECTION_DATE,
    LABEL_MILL_LOCATION,
    LABEL_NDE_LABORATORY,
    LABEL_NUMBER_OF_TUBES,
    LABEL_NUMBERING_DIRECTION,
    MEASUREMENT_START_COL,
    METADATA_LABEL_COL,
    METADATA_VALUE_COL,
    UT_TECH_NAME_MARKER,
)

REQUIRED_METADATA_LABELS = [
    LABEL_COMPANY_NAME,
    LABEL_MILL_LOCATION,
    LABEL_BOILER_NAME,
    LABEL_INSPECTION_DATE,
    LABEL_BOILER_SECTION,
    LABEL_NUMBER_OF_TUBES,
]

ALL_METADATA_LABELS = REQUIRED_METADATA_LABELS + [
    LABEL_NUMBERING_DIRECTION,
    LABEL_NDE_LABORATORY,
]


class TraceParseError(Exception):
    """Raised when a TRACE export CSV cannot be parsed."""


@dataclass
class ElevationData:
    """A single elevation's LEFT/CNTR/RGHT tube readings."""

    label: str
    left: list[Optional[str]] = field(default_factory=list)
    cntr: list[Optional[str]] = field(default_factory=list)
    rght: list[Optional[str]] = field(default_factory=list)


@dataclass
class TraceFileData:
    """Parsed contents of a single TRACE export CSV."""

    source_path: str
    company_name: str
    mill_location: str
    boiler_name: str
    inspection_date: str
    boiler_section: str
    number_of_tubes: int
    numbering_direction: str
    nde_laboratory: Optional[str]
    elevations: list[ElevationData] = field(default_factory=list)


Rows = list[list[str]]


def read_ragged_csv(path: str | Path) -> Rows:
    """
    Read a CSV whose rows may have different field counts and return
    every row padded to the width of the widest row. TRACE exports
    that have not been round-tripped through Excel are ragged; pandas'
    C engine fails on them because it fixes the column count from the
    first line.
    """
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.reader(fh))
    width = max((len(r) for r in rows), default=0)
    return [r + [""] * (width - len(r)) for r in rows]


def _clean(value: Optional[str]) -> Optional[str]:
    """Strip whitespace from a cell value, returning None for blank cells."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _cell(rows: Rows, row_idx: int, col: int) -> Optional[str]:
    """Return the cleaned cell at (row_idx, col), or None when the column is absent."""
    row = rows[row_idx]
    if col >= len(row):
        return None
    return _clean(row[col])


def _read_metadata(rows: Rows) -> dict[str, Optional[str]]:
    """Scan every row for known metadata labels and return their values."""
    metadata: dict[str, Optional[str]] = {}
    for row_idx in range(len(rows)):
        label = _cell(rows, row_idx, METADATA_LABEL_COL)
        if label in ALL_METADATA_LABELS:
            metadata[label] = _cell(rows, row_idx, METADATA_VALUE_COL)
    return metadata


def _read_measurements(rows: Rows, row_idx: int, number_of_tubes: int) -> list[Optional[str]]:
    """Read `number_of_tubes` measurement cells starting at MEASUREMENT_START_COL."""
    end_col = MEASUREMENT_START_COL + number_of_tubes
    return [_cell(rows, row_idx, col) for col in range(MEASUREMENT_START_COL, end_col)]


def _read_elevations(rows: Rows, number_of_tubes: int, filename: str) -> list[ElevationData]:
    """Walk the CSV looking for 3-row elevation blocks (LEFT/CNTR/RGHT)."""
    elevations: list[ElevationData] = []
    row_count = len(rows)
    row_idx = 0
    while row_idx < row_count:
        if _cell(rows, row_idx, 0) == UT_TECH_NAME_MARKER:
            if row_idx + 2 >= row_count:
                raise TraceParseError(
                    f"'{filename}' has an incomplete elevation block starting at row {row_idx + 1}"
                )
            label = _cell(rows, row_idx, ELEVATION_LABEL_COL)
            if not label:
                raise TraceParseError(
                    f"'{filename}' has an elevation block with no label at row {row_idx + 1}"
                )
            elevations.append(
                ElevationData(
                    label=label,
                    left=_read_measurements(rows, row_idx, number_of_tubes),
                    cntr=_read_measurements(rows, row_idx + 1, number_of_tubes),
                    rght=_read_measurements(rows, row_idx + 2, number_of_tubes),
                )
            )
            row_idx += 3
        else:
            row_idx += 1
    return elevations


def parse_trace_csv(path: str | Path) -> TraceFileData:
    """Parse a TRACE UT inspection export CSV into a TraceFileData record.

    Raises:
        TraceParseError: if the file cannot be read or is missing expected
            metadata, elevation blocks, or measurement columns.
    """
    path = Path(path)
    try:
        rows = read_ragged_csv(path)
    except (OSError, csv.Error) as exc:
        raise TraceParseError(f"Could not read '{path.name}': {exc}") from exc

    metadata = _read_metadata(rows)

    missing = [label for label in REQUIRED_METADATA_LABELS if not metadata.get(label)]
    if missing:
        raise TraceParseError(
            f"'{path.name}' is missing required fields: {', '.join(missing)}"
        )

    raw_tube_count = metadata[LABEL_NUMBER_OF_TUBES]
    try:
        number_of_tubes = int(raw_tube_count)
    except ValueError as exc:
        raise TraceParseError(
            f"'{path.name}' has an invalid Number of Tubes value: {raw_tube_count!r}"
        ) from exc

    elevations = _read_elevations(rows, number_of_tubes, path.name)
    if not elevations:
        raise TraceParseError(f"'{path.name}' contains no elevation data blocks")

    return TraceFileData(
        source_path=str(path),
        company_name=metadata[LABEL_COMPANY_NAME],
        mill_location=metadata[LABEL_MILL_LOCATION],
        boiler_name=metadata[LABEL_BOILER_NAME],
        inspection_date=metadata[LABEL_INSPECTION_DATE],
        boiler_section=metadata[LABEL_BOILER_SECTION],
        number_of_tubes=number_of_tubes,
        numbering_direction=metadata.get(LABEL_NUMBERING_DIRECTION) or "",
        nde_laboratory=metadata.get(LABEL_NDE_LABORATORY),
        elevations=elevations,
    )
