# Data Converter - ATS Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ATS-to-Standard-Format CSV converter module to DATO Toolkit on a feature branch, ready for TRACE acceptance testing.

**Architecture:** A pure-Python `app/converters/` package handles all parsing and writing logic with no UI dependencies. A `FlagReviewWidget` and `ConverterPage` layer on top using PyQt6 patterns already established in the codebase. The branch is pushed but never merged or released.

**Tech Stack:** Python 3.x, PyQt6, openpyxl (already installed), csv (stdlib), pytest

## Global Constraints

- Branch: `feature/data-converter` — do NOT merge to main, do NOT tag a release
- All 100 existing tests must continue to pass throughout (run `python -m pytest -q` to verify)
- ATS file paths use exact filenames with spaces: `"examples/ats/7-88-0525 - 01 FLOOR.xlsx"` (no underscores)
- `app/parser.py` is read-only — do not modify it
- No new pip dependencies — openpyxl and csv are already available
- `convert_reading()` is a standalone public function in `app/converters/ats_parser.py`
- `Ctrl+T` shortcut opens the Converter page
- All openpyxl file loads use `data_only=True`
- The Standard Format CSV output must be parseable by the existing `app.parser.parse_trace_csv()`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `app/converters/__init__.py` | Empty package init |
| Create | `app/converters/ats_parser.py` | Parse ATS xlsx, `convert_reading()` helper |
| Create | `app/converters/flag_mapper.py` | Map ATS flag codes to Standard Format codes |
| Create | `app/converters/standard_format_writer.py` | Write Standard Format CSV |
| Create | `app/widgets/flag_review_widget.py` | UI for reviewing unknown flag mappings |
| Create | `app/pages/converter_page.py` | Full converter page UI |
| Create | `tests/test_ats_parser.py` | Parser tests against real files |
| Create | `tests/test_flag_mapper.py` | Flag mapping logic tests |
| Create | `tests/test_standard_format_writer.py` | Writer tests (round-trip via parse_trace_csv) |
| Create | `tests/test_flag_review_widget.py` | Widget signal tests |
| Modify | `app/window.py` | Add ConverterPage, nav button, Ctrl+T shortcut |
| Modify | `app/pages/dashboard_page.py` | Add "Convert Data Files" button |
| Modify | `app/pages/settings_page.py` | Add Ctrl+T to KEYBOARD_SHORTCUTS list |
| Modify | `app/builder.py` | Update xlsx reference in docstring comment |
| Create | `examples/ats/` (7 files moved from root) | Example ATS inspection files |
| Create | `examples/standard-format/` (2 files moved) | Example Standard Format CSVs |
| Create | `examples/templates/` (3 files moved/renamed) | Reference template and docs |
| Create | `examples/team/.gitkeep` | Stub for future TEAM converter |
| Create | `examples/tds/.gitkeep` | Stub for future TDS converter |

---

## Key constants from `app/constants.py` (read-only, do not change)

```python
METADATA_LABEL_COL = 5    # col F (0-indexed)
METADATA_VALUE_COL = 7    # col H (0-indexed)
ELEVATION_LABEL_COL = 2   # col C (0-indexed)
ROLE_COL = 4              # col E (0-indexed)
MEASUREMENT_START_COL = 5 # col F (0-indexed)
UT_TECH_NAME_MARKER = "UT Tech Name:"
LABEL_COMPANY_NAME = "Company Name:---->"
LABEL_MILL_LOCATION = "Mill Location:---->"
LABEL_BOILER_NAME = "Boiler Name:---->"
LABEL_INSPECTION_DATE = "Inspection Date:---->"
LABEL_BOILER_SECTION = "Boiler Section:---->"
LABEL_NUMBER_OF_TUBES = "Number of Tubes:---->"
LABEL_NUMBERING_DIRECTION = "Numbering Direction:---->"
LABEL_NDE_LABORATORY = "NDE Laboratory:---->"
```

---

### Task 1: Branch creation and file organization

**Files:**
- Modify: `app/builder.py` line 4 (comment only)
- Create (move): `examples/ats/` — 7 ATS xlsx files from project root
- Create (move): `examples/standard-format/` — 2 Standard Format CSV files from root
- Create (move/rename): `examples/templates/reference_template.xlsx` (from `sample_tracksheet_2026.xlsx`)
- Create (move): `examples/templates/` — 2 docx files from root
- Create: `examples/team/.gitkeep`, `examples/tds/.gitkeep`

**Interfaces:**
- Consumes: nothing
- Produces: `examples/` directory structure all later tasks reference for test file paths

- [ ] **Step 1: Create the feature branch**

```powershell
git checkout main
git pull origin main
git checkout -b feature/data-converter
```

Expected: `Switched to a new branch 'feature/data-converter'`

- [ ] **Step 2: Create example directories**

```powershell
New-Item -ItemType Directory -Force examples/ats
New-Item -ItemType Directory -Force examples/standard-format
New-Item -ItemType Directory -Force examples/templates
New-Item -ItemType Directory -Force examples/team
New-Item -ItemType Directory -Force examples/tds
```

- [ ] **Step 3: Move ATS xlsx files**

```powershell
Move-Item "7-88-0525 - 01 FLOOR.xlsx"             "examples/ats/"
Move-Item "7-88-0525 - 02 FRONT WALL W PORTS.xlsx" "examples/ats/"
Move-Item "7-88-0525 - 03 LEFT WALL W PORTS.xlsx"  "examples/ats/"
Move-Item "7-88-0525 - 04 REAR WALL W PORTS.xlsx"  "examples/ats/"
Move-Item "7-88-0525 - 05 RIGHT WALL W PORTS.xlsx" "examples/ats/"
Move-Item "7-88-0525 - 10 SOOTBLOWER PASS A1.xlsx" "examples/ats/"
Move-Item "7-88-0525 - 99 ABOVE STUD LINE.xlsx"    "examples/ats/"
```

- [ ] **Step 4: Move Standard Format CSVs**

```powershell
Move-Item "Standard-Sample_Left-to-Right.csv"  "examples/standard-format/"
Move-Item "Standard-Sample_Right-to-Left.csv"  "examples/standard-format/"
```

- [ ] **Step 5: Move and rename reference template and docs**

```powershell
Move-Item "sample_tracksheet_2026.xlsx" "examples/templates/reference_template.xlsx"
Move-Item "Sample Update Email 2026.docx" "examples/templates/"
Move-Item "Standard CSV Format.docx"               "examples/templates/"
```

- [ ] **Step 6: Create stub .gitkeep files**

```powershell
New-Item -ItemType File "examples/team/.gitkeep"
New-Item -ItemType File "examples/tds/.gitkeep"
```

- [ ] **Step 7: Update builder.py docstring comment**

Open `app/builder.py`. Line 4 of the file reads:
```
extracted by inspecting sample_tracksheet_2026.xlsx with openpyxl
```
Change it to:
```
extracted by inspecting examples/templates/reference_template.xlsx with openpyxl
```

The module docstring at the top of `app/builder.py` should now read:
```python
"""Excel tracker generation matching the reference TRACE tracker template.

Styles below (fonts, fills, borders, column widths, freeze panes) were
extracted by inspecting examples/templates/reference_template.xlsx with openpyxl
and are reproduced here so generated workbooks match it exactly.
"""
```

- [ ] **Step 8: Verify tests still pass**

```powershell
python -m pytest -q
```

Expected: `100 passed`

- [ ] **Step 9: Commit**

```powershell
git add examples/ app/builder.py
git commit -m "Reorganize root example files into examples/ subdirectories"
```

---

### Task 2: ATS parser

**Files:**
- Create: `app/converters/__init__.py`
- Create: `app/converters/ats_parser.py`
- Create: `tests/test_ats_parser.py`

**Interfaces:**
- Consumes: nothing from prior tasks
- Produces:
  - `ATSElevation` dataclass (used by Task 4 and Task 5)
  - `ATSParseResult` dataclass (used by Tasks 3, 4, 5, 6)
  - `ATSParseError` exception (used by Task 6)
  - `parse_ats_file(filepath: str | Path) -> ATSParseResult`
  - `convert_reading(value: object) -> str`

#### ATS file structure reference (sheet name: "Thickness")

openpyxl uses **1-based** row and column indices. The spec's "Row 1 (index 0)" means openpyxl row 1. "Col A" = openpyxl column 1.

- **openpyxl row 1**: col A = year (int), col C = flag legend string (e.g., `"NC - NOT CLEAN; RF - REFRACTORY;"`) — may be None
- **openpyxl row 2**: col C = numbering direction string (contains "LEFT TO RIGHT" or "RIGHT TO LEFT")
- **openpyxl row 3**: col A = "ELEVATION", col C = "LOC", cols D onward = tube numbers (int) — stop at "AVG", "MIN", or non-integer non-blank
- **openpyxl row 4 onward**: 3 rows per elevation block:
  - Block row 1: col A = tech code (str), col B = label part 1 (str|None), col C = "L", col D+ = LEFT readings
  - Block row 2: col A = nominal wall (float|None), col B = label part 2 (str|None), col C = "C", col D+ = CNTR readings
  - Block row 3: col A = None/blank, col B = label part 3 (str|None), col C = "R", col D+ = RGHT readings
  - Stop when col A == "ELEVATION" and col C == "LOC" (repeat footer header)
- **Elevation label**: join non-None/non-blank col B values across the 3 rows with a single space, stripped
- **Metadata** (bottom-right area, ~col CN): scan rows `(max_row - 40)` to `max_row` for anchor cell containing `"TUBE WALL THICKNESS SURVEY"`. Relative to anchor (same column): anchor-2 = Company Name, anchor-1 = Mill Location, anchor+1 = Boiler Name, anchor+2 = Section name.
- **NDE Lab**: scan same row range for first cell whose string value contains `"\n"`. Take `.split("\n")[0]`, title-cased.
- **Date**: scan same row range for cell whose string contains `"Date:"`. Apply regex `r"Date:\s*(\d{1,2})/(\d{2})/(\d{4})"`. Convert to `"Month YYYY"` (e.g., `"5/05/2025"` → `"May 2025"`).
- **Flag legend** (openpyxl row 1, col C): split on `";"`, each part split on `" - "` → `{code: description}`. Blank → `{}`.

- [ ] **Step 1: Create the converters package**

Create `app/converters/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_ats_parser.py`:

```python
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
    assert isinstance(result.ats_flags, dict)


def test_parse_floor_flags_passthrough_in_readings():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FLOOR)
    flag_codes = set(result.ats_flags.keys())
    for elev in result.elevations:
        for reading in elev.left + elev.cntr + elev.rght:
            if reading and not reading.isdigit():
                assert reading in flag_codes or reading == "", (
                    f"Non-numeric reading '{reading}' not in known flag codes {flag_codes}"
                )


def test_parse_front_wall_has_elevations():
    from app.converters.ats_parser import parse_ats_file
    result = parse_ats_file(FRONT_WALL)
    assert len(result.elevations) > 0


def test_parse_invalid_file_raises():
    from app.converters.ats_parser import ATSParseError, parse_ats_file
    with pytest.raises(ATSParseError):
        parse_ats_file("nonexistent_file_that_does_not_exist.xlsx")
```

- [ ] **Step 3: Run tests to confirm they fail**

```powershell
python -m pytest tests/test_ats_parser.py -q
```

Expected: `ImportError` or `ModuleNotFoundError` — `app/converters/ats_parser.py` does not exist yet.

- [ ] **Step 4: Implement `app/converters/ats_parser.py`**

```python
"""ATS xlsx inspection file parser."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl


class ATSParseError(Exception):
    """Raised when an ATS xlsx file cannot be parsed."""


@dataclass
class ATSElevation:
    label: str
    tech_code: str
    nominal_wall: float | None
    left: list[str]
    cntr: list[str]
    rght: list[str]


@dataclass
class ATSParseResult:
    company_name: str
    mill_location: str
    boiler_name: str
    inspection_date: str       # "Month YYYY"
    boiler_section: str
    num_tubes: int
    numbering_direction: str   # "Left-to-Right" or "Right-to-Left"
    nde_laboratory: str
    year: int
    ats_flags: dict[str, str]  # {code: description}
    elevations: list[ATSElevation]
    tube_numbers: list[int]


_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def convert_reading(value: object) -> str:
    """Convert an ATS cell value to Standard Format string.

    float/int → zero-padded 3-digit integer (0.234 → "234", 0.010 → "010")
    None or empty string → ""
    str (flag code) → unchanged
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return f"{round(value * 1000):03d}"
    stripped = str(value).strip()
    return stripped


def _parse_flag_legend(raw: object) -> dict[str, str]:
    if not isinstance(raw, str) or not raw.strip():
        return {}
    result: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if " - " in part:
            code, desc = part.split(" - ", 1)
            result[code.strip()] = desc.strip()
    return result


def _parse_direction(raw: object) -> str:
    if isinstance(raw, str):
        upper = raw.upper()
        if "LEFT TO RIGHT" in upper:
            return "Left-to-Right"
        if "RIGHT TO LEFT" in upper:
            return "Right-to-Left"
    return "Left-to-Right"


def _parse_date(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    match = re.search(r"Date:\s*(\d{1,2})/(\d{2})/(\d{4})", raw)
    if not match:
        return ""
    month_num = int(match.group(1))
    year = match.group(3)
    if 1 <= month_num <= 12:
        return f"{_MONTH_NAMES[month_num]} {year}"
    return ""


def parse_ats_file(filepath: str | Path) -> ATSParseResult:
    """Parse an ATS Thickness xlsx file into an ATSParseResult.

    Raises:
        ATSParseError: if the file cannot be opened or is missing expected data.
    """
    path = Path(filepath)
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception as exc:
        raise ATSParseError(f"Cannot open '{path.name}': {exc}") from exc

    if "Thickness" not in wb.sheetnames:
        raise ATSParseError(f"'{path.name}' has no 'Thickness' sheet")

    ws = wb["Thickness"]

    # Row 1 (openpyxl row 1): year and flag legend
    year_cell = ws.cell(row=1, column=1).value
    year = int(year_cell) if isinstance(year_cell, (int, float)) else 0
    ats_flags = _parse_flag_legend(ws.cell(row=1, column=3).value)

    # Row 2 (openpyxl row 2): numbering direction
    numbering_direction = _parse_direction(ws.cell(row=2, column=3).value)

    # Row 3 (openpyxl row 3): tube numbers starting at col D (column 4)
    tube_numbers: list[int] = []
    col = 4
    while True:
        val = ws.cell(row=3, column=col).value
        if val is None:
            break
        if isinstance(val, str) and val.upper().strip() in ("AVG", "MIN"):
            break
        if isinstance(val, (int, float)):
            tube_numbers.append(int(val))
            col += 1
        else:
            break

    num_tubes = len(tube_numbers)
    if num_tubes == 0:
        raise ATSParseError(f"'{path.name}': no tube numbers found in row 3")

    # Elevation blocks starting at openpyxl row 4
    elevations: list[ATSElevation] = []
    row_idx = 4
    while row_idx <= ws.max_row:
        col_a = ws.cell(row=row_idx, column=1).value
        col_c = ws.cell(row=row_idx, column=3).value

        # Stop at repeat footer header
        if col_a == "ELEVATION" and col_c == "LOC":
            break

        if col_c == "L":
            tech_raw = ws.cell(row=row_idx, column=1).value
            tech_code = str(tech_raw).strip() if tech_raw is not None else ""

            nominal_raw = ws.cell(row=row_idx + 1, column=1).value
            nominal_wall = (
                float(nominal_raw)
                if isinstance(nominal_raw, (int, float))
                else None
            )

            label_parts = []
            for sub_row in (row_idx, row_idx + 1, row_idx + 2):
                part = ws.cell(row=sub_row, column=2).value
                if part is not None:
                    stripped = str(part).strip()
                    if stripped:
                        label_parts.append(stripped)
            label = " ".join(label_parts)

            left = [
                convert_reading(ws.cell(row=row_idx, column=4 + i).value)
                for i in range(num_tubes)
            ]
            cntr = [
                convert_reading(ws.cell(row=row_idx + 1, column=4 + i).value)
                for i in range(num_tubes)
            ]
            rght = [
                convert_reading(ws.cell(row=row_idx + 2, column=4 + i).value)
                for i in range(num_tubes)
            ]

            elevations.append(ATSElevation(
                label=label,
                tech_code=tech_code,
                nominal_wall=nominal_wall,
                left=left,
                cntr=cntr,
                rght=rght,
            ))
            row_idx += 3
        else:
            row_idx += 1

    # Metadata from bottom-right area
    company_name = mill_location = boiler_name = boiler_section = ""
    nde_laboratory = ""
    inspection_date = ""

    scan_start = max(1, ws.max_row - 40)
    anchor_row: int | None = None
    anchor_col: int | None = None

    for ri in range(scan_start, ws.max_row + 1):
        for ci in range(1, ws.max_column + 1):
            cell_val = ws.cell(row=ri, column=ci).value
            if isinstance(cell_val, str) and "TUBE WALL THICKNESS SURVEY" in cell_val:
                anchor_row = ri
                anchor_col = ci
                break
        if anchor_row is not None:
            break

    if anchor_row is not None and anchor_col is not None:
        def _str_at(r: int) -> str:
            v = ws.cell(row=r, column=anchor_col).value
            return str(v).strip() if v is not None else ""

        company_name = _str_at(anchor_row - 2)
        mill_location = _str_at(anchor_row - 1)
        boiler_name = _str_at(anchor_row + 1)
        boiler_section = _str_at(anchor_row + 2)

    for ri in range(scan_start, ws.max_row + 1):
        for ci in range(1, ws.max_column + 1):
            cell_val = ws.cell(row=ri, column=ci).value
            if isinstance(cell_val, str) and "\n" in cell_val and not nde_laboratory:
                nde_laboratory = cell_val.split("\n")[0].strip().title()
            if isinstance(cell_val, str) and "Date:" in cell_val and not inspection_date:
                inspection_date = _parse_date(cell_val)

    if not company_name:
        raise ATSParseError(f"'{path.name}': could not locate metadata block")

    return ATSParseResult(
        company_name=company_name,
        mill_location=mill_location,
        boiler_name=boiler_name,
        inspection_date=inspection_date,
        boiler_section=boiler_section,
        num_tubes=num_tubes,
        numbering_direction=numbering_direction,
        nde_laboratory=nde_laboratory,
        year=year,
        ats_flags=ats_flags,
        elevations=elevations,
        tube_numbers=tube_numbers,
    )
```

- [ ] **Step 5: Run parser tests**

```powershell
python -m pytest tests/test_ats_parser.py -v
```

Expected: all tests pass. If any fail, read the error carefully — most likely the ATS file has a different structure than expected (wrong sheet name, different anchor text, etc.). Fix the parser, not the tests.

- [ ] **Step 6: Verify 100 existing tests still pass**

```powershell
python -m pytest -q
```

Expected: 100 passed + however many new parser tests.

- [ ] **Step 7: Commit**

```powershell
git add app/converters/ tests/test_ats_parser.py
git commit -m "Add ATS xlsx parser (ATSParseResult, convert_reading)"
```

---

### Task 3: Flag mapper

**Files:**
- Create: `app/converters/flag_mapper.py`
- Create: `tests/test_flag_mapper.py`

**Interfaces:**
- Consumes: `ATSParseResult.ats_flags: dict[str, str]` from Task 2
- Produces:
  - `DEFAULT_ATS_FLAG_MAP: dict[str, str]`
  - `FlagMappingResult` dataclass
  - `build_flag_mapping(ats_flags: dict[str, str]) -> FlagMappingResult`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_flag_mapper.py`:

```python
"""Tests for ATS flag code mapping logic."""
from __future__ import annotations


def test_default_map_has_six_entries():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert len(DEFAULT_ATS_FLAG_MAP) == 6


def test_default_map_contains_known_codes():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert DEFAULT_ATS_FLAG_MAP["NC"] == "<"
    assert DEFAULT_ATS_FLAG_MAP["RF"] == "("
    assert DEFAULT_ATS_FLAG_MAP["RT"] == ")"
    assert DEFAULT_ATS_FLAG_MAP["SI"] == ";"
    assert DEFAULT_ATS_FLAG_MAP["ST"] == "+"
    assert DEFAULT_ATS_FLAG_MAP["NS"] == "["


def test_build_mapping_all_known():
    from app.converters.flag_mapper import build_flag_mapping
    ats_flags = {"NC": "NOT CLEAN", "RF": "REFRACTORY"}
    result = build_flag_mapping(ats_flags)
    assert result.unknown == {}
    assert result.known == {"NC": "<", "RF": "("}
    assert result.final == {"NC": "<", "RF": "("}


def test_build_mapping_with_unknown():
    from app.converters.flag_mapper import build_flag_mapping
    ats_flags = {"NC": "NOT CLEAN", "XX": "SOME NEW FLAG"}
    result = build_flag_mapping(ats_flags)
    assert "XX" in result.unknown
    assert "NC" in result.known
    assert "XX" not in result.known
    assert result.final == {"NC": "<"}


def test_build_mapping_empty():
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({})
    assert result.known == {}
    assert result.unknown == {}
    assert result.final == {}


def test_build_mapping_only_unknown():
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({"ZZ": "MYSTERY"})
    assert result.known == {}
    assert "ZZ" in result.unknown
    assert result.final == {}
```

- [ ] **Step 2: Run to confirm failure**

```powershell
python -m pytest tests/test_flag_mapper.py -q
```

Expected: `ModuleNotFoundError` — file does not exist yet.

- [ ] **Step 3: Implement `app/converters/flag_mapper.py`**

```python
"""ATS flag code to Standard Format code mapping."""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_ATS_FLAG_MAP: dict[str, str] = {
    "NC": "<",   # Not clean
    "RF": "(",   # Refractory
    "RT": ")",   # Recessed tube
    "SI": ";",   # Signal interrupt
    "ST": "+",   # Stud
    "NS": "[",   # No scan
}


@dataclass
class FlagMappingResult:
    known: dict[str, str]    # flags auto-mapped from DEFAULT_ATS_FLAG_MAP
    unknown: dict[str, str]  # {ats_code: ats_description} not in defaults
    final: dict[str, str]    # complete mapping after user review (known only until confirmed)


def build_flag_mapping(ats_flags: dict[str, str]) -> FlagMappingResult:
    """Split ats_flags into known (auto-mapped) and unknown (need user review).

    Args:
        ats_flags: {ats_code: description} from ATSParseResult.ats_flags

    Returns:
        FlagMappingResult where final contains only the auto-mapped codes
        until the user reviews unknowns and calls update on the result.
    """
    known: dict[str, str] = {}
    unknown: dict[str, str] = {}
    for code, description in ats_flags.items():
        if code in DEFAULT_ATS_FLAG_MAP:
            known[code] = DEFAULT_ATS_FLAG_MAP[code]
        else:
            unknown[code] = description
    return FlagMappingResult(known=known, unknown=unknown, final=dict(known))
```

- [ ] **Step 4: Run flag mapper tests**

```powershell
python -m pytest tests/test_flag_mapper.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add app/converters/flag_mapper.py tests/test_flag_mapper.py
git commit -m "Add flag mapper (DEFAULT_ATS_FLAG_MAP, build_flag_mapping)"
```

---

### Task 4: Standard Format CSV writer

**Files:**
- Create: `app/converters/standard_format_writer.py`
- Create: `tests/test_standard_format_writer.py`

**Interfaces:**
- Consumes:
  - `ATSParseResult` from Task 2
  - `FlagMappingResult.final: dict[str, str]` from Task 3
- Produces:
  - `write_standard_format(result: ATSParseResult, flag_mapping: dict[str, str], output_path: str | Path) -> None`

#### CSV structure reference

The output must be parseable by `app.parser.parse_trace_csv()`. Key column indices (0-based, matching constants.py):
- Metadata label: col 5 (F), metadata value: col 7 (H)
- Elevation marker: col 0 (A) = `"UT Tech Name:"`, elevation label: col 2 (C)
- Role: col 4 (E) = `"LEFT"`, `"CNTR"`, or `"RGHT"`
- Readings: cols 5+ (F+)
- Tube numbers row: col 1 (B) = `"TUBE NUMBERS along the top.---->"`, values at cols 5+
- Flag legend: col 1 (B) = `" {std_code}    means {description}."` (one row per flag)

Row layout (0-indexed):
- 0: col 4 = format comment
- 1: col 4 = font comment
- 2-3: blank
- 4-11: metadata rows (label at col 5, value at col 7)
- 12-13: blank
- 14: tube numbers row (top)
- 15: blank
- 16+: elevation blocks (3 rows each)
- after all elevations: tube numbers row (bottom, label = `"TUBE NUMBERS along the bottom.---->"`)
- +1: blank
- +2+: flag legend rows

- [ ] **Step 1: Write the failing tests**

Create `tests/test_standard_format_writer.py`:

```python
"""Tests for Standard Format CSV writer.

The round-trip test (write → parse with parse_trace_csv) is the primary
correctness check. parse_trace_csv returns a TraceFileData dataclass —
access fields as attributes, not dict keys.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.converters.ats_parser import ATSElevation, ATSParseResult
from app.parser import parse_trace_csv


def _make_result(num_tubes: int = 3) -> ATSParseResult:
    return ATSParseResult(
        company_name="EXAMPLE PAPER",
        mill_location="Anytown, LA",
        boiler_name="Recovery Boiler 2",
        inspection_date="May 2025",
        boiler_section="01 FLOOR",
        num_tubes=num_tubes,
        numbering_direction="Left-to-Right",
        nde_laboratory="Applied Technical Services",
        year=2025,
        ats_flags={"NC": "NOT CLEAN", "RF": "REFRACTORY"},
        elevations=[
            ATSElevation(
                label="8 FT",
                tech_code="JD",
                nominal_wall=0.234,
                left=["234", "220", ""][:num_tubes],
                cntr=["210", "NC", "230"][:num_tubes],
                rght=["215", "200", "240"][:num_tubes],
            ),
            ATSElevation(
                label="14 FT",
                tech_code="JD",
                nominal_wall=0.234,
                left=["218", "232", "244"][:num_tubes],
                cntr=["209", "215", "RF"][:num_tubes],
                rght=["222", "211", "233"][:num_tubes],
            ),
        ],
        tube_numbers=list(range(1, num_tubes + 1)),
    )


def test_write_creates_file(tmp_path: Path):
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "test.csv"
    write_standard_format(result, {"NC": "<", "RF": "("}, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_write_parseable_by_dato_parser(tmp_path: Path):
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<", "RF": "("}, out)
    parsed = parse_trace_csv(str(out))
    assert parsed.company_name == "EXAMPLE PAPER"
    assert parsed.mill_location == "Anytown, LA"
    assert parsed.boiler_name == "Recovery Boiler 2"
    assert parsed.inspection_date == "May 2025"
    assert parsed.boiler_section == "01 FLOOR"
    assert parsed.number_of_tubes == 3
    assert len(parsed.elevations) == 2


def test_write_elevation_labels_preserved(tmp_path: Path):
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out)
    parsed = parse_trace_csv(str(out))
    labels = [e.label for e in parsed.elevations]
    assert "8 FT" in labels
    assert "14 FT" in labels


def test_write_flag_mapping_in_legend(tmp_path: Path):
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<"}, out)
    content = out.read_text(encoding="utf-8")
    assert "<" in content
    assert "NOT CLEAN" in content


def test_write_tube_numbers_row(tmp_path: Path):
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result(num_tubes=5)
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out)
    content = out.read_text(encoding="utf-8")
    assert "TUBE NUMBERS along the top" in content
    assert "TUBE NUMBERS along the bottom" in content


def test_write_empty_flag_mapping_succeeds(tmp_path: Path):
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out)
    assert out.exists()
```

- [ ] **Step 2: Run to confirm failure**

```powershell
python -m pytest tests/test_standard_format_writer.py -q
```

Expected: `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement `app/converters/standard_format_writer.py`**

```python
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
```

- [ ] **Step 4: Run writer tests**

```powershell
python -m pytest tests/test_standard_format_writer.py -v
```

Expected: all tests pass. If `test_write_parseable_by_dato_parser` fails, check the column assignments against the constants in `app/constants.py` — `METADATA_LABEL_COL=5`, `METADATA_VALUE_COL=7`, `UT_TECH_NAME_MARKER="UT Tech Name:"`, `ELEVATION_LABEL_COL=2`, `ROLE_COL=4`, `MEASUREMENT_START_COL=5`.

- [ ] **Step 5: Run full suite**

```powershell
python -m pytest -q
```

Expected: 100 original + new tests, all passed.

- [ ] **Step 6: Commit**

```powershell
git add app/converters/standard_format_writer.py tests/test_standard_format_writer.py
git commit -m "Add Standard Format CSV writer (write_standard_format)"
```

---

### Task 5: Flag review widget

**Files:**
- Create: `app/widgets/flag_review_widget.py`
- Create: `tests/test_flag_review_widget.py`

**Interfaces:**
- Consumes: `FlagMappingResult` from Task 3
- Produces:
  - `FlagReviewWidget(QWidget)` class
  - Signal: `mappings_confirmed = pyqtSignal(dict)` — emits `{ats_code: std_code}` for all flags

The widget shows when `FlagMappingResult.unknown` is non-empty. If all flags are auto-mapped (`unknown == {}`), the widget emits `mappings_confirmed` immediately after construction (via `QTimer.singleShot(0, ...)`) and shows only a slim info bar.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_flag_review_widget.py`:

```python
"""Tests for FlagReviewWidget.

Uses module-level QApplication to prevent GC crash on Windows (same pattern
as test_footer.py).
"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_widget_instantiates_with_all_known():
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={"NC": "<"},
        unknown={},
        final={"NC": "<"},
    )
    widget = FlagReviewWidget(result)
    assert widget is not None


def test_widget_instantiates_with_unknowns():
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={"NC": "<"},
        unknown={"XX": "MYSTERY FLAG"},
        final={"NC": "<"},
    )
    widget = FlagReviewWidget(result)
    assert widget is not None


def test_all_known_emits_confirmed_signal(qtbot):
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={"NC": "<", "RF": "("},
        unknown={},
        final={"NC": "<", "RF": "("},
    )
    widget = FlagReviewWidget(result)
    with qtbot.waitSignal(widget.mappings_confirmed, timeout=1000) as blocker:
        pass
    assert blocker.args[0] == {"NC": "<", "RF": "("}
```

Note: `qtbot` is provided by the `pytest-qt` plugin. Install it if not present: `pip install pytest-qt`.

- [ ] **Step 2: Check if pytest-qt is available**

```powershell
python -m pytest --co -q tests/test_flag_review_widget.py 2>&1 | Select-Object -First 10
```

If you see `ERRORS` mentioning `qtbot` fixture not found, install it:
```powershell
pip install pytest-qt
```

- [ ] **Step 3: Run to confirm failure**

```powershell
python -m pytest tests/test_flag_review_widget.py -q
```

Expected: `ModuleNotFoundError` — widget file does not exist yet.

- [ ] **Step 4: Implement `app/widgets/flag_review_widget.py`**

```python
"""Flag review widget for confirming ATS → Standard Format code mappings."""
from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.converters.flag_mapper import FlagMappingResult
from app.styles import color

HEADING_TEXT = "Flag Review"
SUBTEXT_ALL_KNOWN = "All flag codes were auto-mapped. No review needed."
SUBTEXT_UNKNOWN = (
    "Some flag codes in these files are not in the auto-map list. "
    "Enter a Standard Format code for each, or check 'Leave as-is' to pass it through unchanged."
)
CONFIRM_TEXT = "Confirm Mappings"
AUTO_MAPPED_LABEL = "Auto-mapped"
NEEDS_MAPPING_LABEL = "Needs mapping"
LEAVE_AS_IS_TEXT = "Leave as-is"


class FlagReviewWidget(QWidget):
    """Shows flag mappings for user review. Emits mappings_confirmed when done."""

    mappings_confirmed = pyqtSignal(dict)

    def __init__(self, mapping_result: FlagMappingResult, parent: QWidget | None = None):
        super().__init__(parent)
        self._mapping_result = mapping_result
        self._code_inputs: dict[str, QLineEdit] = {}
        self._leave_checks: dict[str, QCheckBox] = {}
        self._build_ui()

        if not mapping_result.unknown:
            QTimer.singleShot(0, lambda: self.mappings_confirmed.emit(dict(mapping_result.final)))

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        heading = QLabel(HEADING_TEXT)
        heading.setProperty("role", "heading")
        outer.addWidget(heading)

        if not self._mapping_result.unknown:
            info = QLabel(SUBTEXT_ALL_KNOWN)
            info.setStyleSheet(f"color: {color('success')}; font-size: 9pt;")
            outer.addWidget(info)
            return

        subtext = QLabel(SUBTEXT_UNKNOWN)
        subtext.setWordWrap(True)
        subtext.setProperty("role", "muted")
        outer.addWidget(subtext)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        outer.addWidget(scroll)

        # Column headers
        header = QHBoxLayout()
        for label, stretch in [("ATS Code", 1), ("ATS Description", 3), ("Std Code", 1), ("Status", 2), ("", 1)]:
            lbl = QLabel(f"<b>{label}</b>")
            header.addWidget(lbl, stretch)
        scroll_layout.addLayout(header)

        # Known flags (read-only display)
        for ats_code, std_code in self._mapping_result.known.items():
            description = self._mapping_result.unknown.get(ats_code, ats_code)
            row = QHBoxLayout()
            row.addWidget(QLabel(ats_code), 1)
            row.addWidget(QLabel(description), 3)
            code_lbl = QLabel(std_code)
            code_lbl.setStyleSheet(f"color: {color('success')};")
            row.addWidget(code_lbl, 1)
            status = QLabel(AUTO_MAPPED_LABEL)
            status.setStyleSheet(f"color: {color('success')}; font-size: 9pt;")
            row.addWidget(status, 2)
            row.addWidget(QLabel(""), 1)
            scroll_layout.addLayout(row)

        # Unknown flags (editable)
        for ats_code, description in self._mapping_result.unknown.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(ats_code), 1)
            row.addWidget(QLabel(description), 3)

            code_input = QLineEdit()
            code_input.setMaxLength(3)
            code_input.setPlaceholderText("e.g. ?")
            code_input.textChanged.connect(self._on_input_changed)
            self._code_inputs[ats_code] = code_input
            row.addWidget(code_input, 1)

            status_lbl = QLabel(NEEDS_MAPPING_LABEL)
            status_lbl.setStyleSheet(f"color: {color('warning')}; font-size: 9pt;")
            row.addWidget(status_lbl, 2)

            leave_check = QCheckBox(LEAVE_AS_IS_TEXT)
            leave_check.stateChanged.connect(
                lambda state, code=ats_code, inp=code_input, lbl=status_lbl:
                    self._on_leave_toggled(code, inp, lbl, state)
            )
            self._leave_checks[ats_code] = leave_check
            row.addWidget(leave_check, 1)

            scroll_layout.addLayout(row)

        scroll_layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._confirm_btn = QPushButton(CONFIRM_TEXT)
        self._confirm_btn.setProperty("accent", "true")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self._confirm_btn)
        outer.addLayout(btn_row)

    def _on_leave_toggled(
        self, code: str, inp: QLineEdit, status_lbl: QLabel, state: int
    ) -> None:
        checked = state == Qt.CheckState.Checked.value
        inp.setEnabled(not checked)
        if checked:
            status_lbl.setText("Leave as-is")
            status_lbl.setStyleSheet(f"color: {color('muted_text')}; font-size: 9pt;")
        else:
            status_lbl.setText(NEEDS_MAPPING_LABEL)
            status_lbl.setStyleSheet(f"color: {color('warning')}; font-size: 9pt;")
        self._update_confirm_button()

    def _on_input_changed(self) -> None:
        self._update_confirm_button()

    def _update_confirm_button(self) -> None:
        all_resolved = True
        for ats_code in self._mapping_result.unknown:
            leave = self._leave_checks.get(ats_code)
            inp = self._code_inputs.get(ats_code)
            if leave and leave.isChecked():
                continue
            if inp and not inp.text().strip():
                all_resolved = False
                break
        self._confirm_btn.setEnabled(all_resolved)

    def _on_confirm(self) -> None:
        final = dict(self._mapping_result.known)
        for ats_code in self._mapping_result.unknown:
            leave = self._leave_checks.get(ats_code)
            inp = self._code_inputs.get(ats_code)
            if leave and leave.isChecked():
                final[ats_code] = ats_code
            elif inp:
                final[ats_code] = inp.text().strip()
        self.mappings_confirmed.emit(final)
```

- [ ] **Step 5: Run flag review widget tests**

```powershell
python -m pytest tests/test_flag_review_widget.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Run full suite**

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add app/widgets/flag_review_widget.py tests/test_flag_review_widget.py
git commit -m "Add FlagReviewWidget for reviewing ATS flag code mappings"
```

---

### Task 6: Converter page and full wiring

**Files:**
- Create: `app/pages/converter_page.py`
- Modify: `app/window.py`
- Modify: `app/pages/dashboard_page.py`
- Modify: `app/pages/settings_page.py`

**Interfaces:**
- Consumes: `ATSParseResult`, `FlagMappingResult`, `FlagReviewWidget`, `write_standard_format` from Tasks 2-5
- Produces:
  - `ConverterPage(QWidget)` with `back_requested = pyqtSignal()`
  - `STATUS_HINT` string constant (used by window.py)
  - `CONVERTER_PAGE_INDEX = 9` constant in window.py

The converter page index is 9. The existing pages occupy indices 0-8:
- 0 = Dashboard, 1 = Import, 2 = Reorder, 3 = Generate, 4 = History, 5 = Settings, 6 = Batch, 7 = Projects, 8 = Email

- [ ] **Step 1: Create `app/pages/converter_page.py`**

This is a large file. Create it in full:

```python
"""ATS Data Converter page: import ATS xlsx files and export Standard Format CSVs."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.converters.ats_parser import ATSParseError, ATSParseResult, parse_ats_file
from app.converters.flag_mapper import FlagMappingResult, build_flag_mapping
from app.converters.standard_format_writer import write_standard_format
from app.styles import apply_card_shadow, color
from app.widgets import HelpPanel
from app.widgets.flag_review_widget import FlagReviewWidget

logger = logging.getLogger(__name__)

TITLE_TEXT = "Data Converter"
BACK_TEXT = "← Back"
STATUS_HINT = "Tip: Import ATS inspection files to convert them to Standard Format CSV for TRACE."
HELP_TITLE = "Data Converter"
HELP_BODY = """
<p>The Data Converter transforms ATS inspection files into the Standard
Format CSV that TRACE accepts for data import.</p>
<p>Import one or more ATS <b>.xlsx</b> files. The converter reads all
inspection data, metadata, and flag codes automatically from each file.</p>
<p>If your files contain flag codes that are not in the auto-mapping list,
a review screen will appear so you can confirm or adjust the mapping
before converting.</p>
<p>One Standard Format CSV is produced per ATS file. Output files are
saved to your chosen output folder.</p>
<p><b>Keyboard shortcut:</b> Ctrl+T opens this page.</p>
"""

DROP_ZONE_TEXT = "Drop ATS .xlsx files here, or click to browse"
CLEAR_ALL_TEXT = "Clear All"
OUTPUT_FOLDER_LABEL = "Output Folder"
BROWSE_TEXT = "Browse..."
CONVERT_ALL_TEXT = "Convert All"
OPEN_FOLDER_TEXT = "Open Output Folder"
CONVERT_MORE_TEXT = "Convert More Files"
NO_FILES_TEXT = "No files imported yet."
CONVERTING_TEXT = "Converting..."

ATS_TAB_TEXT = "ATS Files"
TEAM_TAB_TEXT = "TEAM Files"
TDS_TAB_TEXT = "TDS Files"
COMING_SOON_TOOLTIP = "Coming soon"


class _ConvertWorker(QThread):
    """Runs conversions on a background thread."""

    file_done = pyqtSignal(str, bool, str)  # path, success, error_message
    all_done = pyqtSignal()

    def __init__(
        self,
        jobs: list[tuple[str, ATSParseResult]],
        flag_mapping: dict[str, str],
        output_dir: Path,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._jobs = jobs
        self._flag_mapping = flag_mapping
        self._output_dir = output_dir

    def run(self) -> None:
        for source_path, result in self._jobs:
            section = result.boiler_section.replace("/", "-").replace("\\", "-")
            out_name = f"{section}_Standard_Format.csv"
            out_path = self._output_dir / out_name
            try:
                write_standard_format(result, self._flag_mapping, out_path)
                self.file_done.emit(source_path, True, "")
            except Exception as exc:
                self.file_done.emit(source_path, False, str(exc))
        self.all_done.emit()


class _FileCard(QFrame):
    """One imported file shown in the file list."""

    remove_requested = pyqtSignal(str)  # path

    def __init__(self, path: str, result: ATSParseResult, parent: QWidget | None = None):
        super().__init__(parent)
        self._path = path
        self.setProperty("card", "true")
        apply_card_shadow(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        info = QVBoxLayout()
        name_lbl = QLabel(f"<b>{Path(path).name}</b>")
        info.addWidget(name_lbl)
        detail = QLabel(
            f"{result.boiler_section} — "
            f"{result.num_tubes} tubes, "
            f"{len(result.elevations)} elevation{'s' if len(result.elevations) != 1 else ''}"
        )
        detail.setProperty("role", "muted")
        info.addWidget(detail)
        layout.addLayout(info, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setProperty("flat", "true")
        remove_btn.setToolTip("Remove this file")
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._path))
        layout.addWidget(remove_btn)


class _ErrorCard(QFrame):
    """An import error shown inline in the file list."""

    def __init__(self, path: str, error: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background-color: #2a1a1a; border: 1px solid {color('error')}; "
            f"border-radius: 6px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(f"<b>{Path(path).name}</b>: {error}")
        lbl.setStyleSheet(f"color: {color('error')};")
        lbl.setWordWrap(True)
        layout.addWidget(lbl, 1)


class ConverterPage(QWidget):
    """ATS Data Converter page."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._imported: dict[str, ATSParseResult] = {}  # path → result
        self._errors: dict[str, str] = {}               # path → error message
        self._flag_mapping: dict[str, str] = {}
        self._flags_confirmed = False
        self._worker: Optional[_ConvertWorker] = None
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(main, 1)

        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

        # Header
        header_row = QHBoxLayout()
        back_btn = QPushButton(BACK_TEXT)
        back_btn.setProperty("flat", "true")
        back_btn.clicked.connect(self.back_requested.emit)
        header_row.addWidget(back_btn)
        header_row.addSpacing(12)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        help_btn = QPushButton("?")
        help_btn.setFixedSize(28, 28)
        help_btn.setToolTip("Toggle help (F1)")
        help_btn.clicked.connect(self.help_panel.toggle)
        header_row.addWidget(help_btn)
        main_layout.addLayout(header_row)

        # Sub-navigation tabs
        tab_row = QHBoxLayout()
        ats_tab = QPushButton(ATS_TAB_TEXT)
        ats_tab.setStyleSheet(
            f"QPushButton {{ background-color: {color('highlight')}; color: {color('text')}; "
            f"font-weight: 600; border-radius: 6px; padding: 4px 12px; }}"
        )
        tab_row.addWidget(ats_tab)
        for tab_text in (TEAM_TAB_TEXT, TDS_TAB_TEXT):
            btn = QPushButton(tab_text)
            btn.setEnabled(False)
            btn.setToolTip(COMING_SOON_TOOLTIP)
            btn.setProperty("flat", "true")
            tab_row.addWidget(btn)
        tab_row.addStretch(1)
        main_layout.addLayout(tab_row)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(12)
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        # Section 1: Import
        import_card = QFrame()
        import_card.setProperty("card", "true")
        apply_card_shadow(import_card)
        import_layout = QVBoxLayout(import_card)

        import_header = QHBoxLayout()
        import_header.addWidget(QLabel("<b>Import ATS Files</b>"))
        import_header.addStretch(1)
        self._clear_all_btn = QPushButton(CLEAR_ALL_TEXT)
        self._clear_all_btn.setProperty("flat", "true")
        self._clear_all_btn.setEnabled(False)
        self._clear_all_btn.clicked.connect(self._on_clear_all)
        import_header.addWidget(self._clear_all_btn)
        import_layout.addLayout(import_header)

        self._drop_zone = QPushButton(DROP_ZONE_TEXT)
        self._drop_zone.setMinimumHeight(80)
        self._drop_zone.setStyleSheet(
            f"QPushButton {{ border: 2px dashed {color('border')}; border-radius: 8px; "
            f"color: {color('muted_text')}; background: transparent; }}"
            f"QPushButton:hover {{ border-color: {color('highlight')}; color: {color('text')}; }}"
        )
        self._drop_zone.clicked.connect(self._on_browse_files)
        import_layout.addWidget(self._drop_zone)

        self._file_list_layout = QVBoxLayout()
        self._file_list_layout.setSpacing(6)
        import_layout.addLayout(self._file_list_layout)

        self._content_layout.addWidget(import_card)

        # Section 2: Flag Review
        self._flag_widget_container = QWidget()
        self._flag_widget_layout = QVBoxLayout(self._flag_widget_container)
        self._flag_widget_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.addWidget(self._flag_widget_container)

        # Section 3: Output
        output_card = QFrame()
        output_card.setProperty("card", "true")
        apply_card_shadow(output_card)
        output_layout = QVBoxLayout(output_card)
        output_layout.addWidget(QLabel("<b>Output</b>"))

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel(OUTPUT_FOLDER_LABEL))
        self._output_folder_edit = QLineEdit()
        self._output_folder_edit.setPlaceholderText("Choose output folder...")
        self._output_folder_edit.setReadOnly(True)
        self._output_folder_edit.setText(str(Path.home() / "Desktop"))
        folder_row.addWidget(self._output_folder_edit, 1)
        browse_btn = QPushButton(BROWSE_TEXT)
        browse_btn.setProperty("flat", "true")
        browse_btn.clicked.connect(self._on_browse_output)
        folder_row.addWidget(browse_btn)
        output_layout.addLayout(folder_row)

        self._convert_btn = QPushButton(CONVERT_ALL_TEXT)
        self._convert_btn.setProperty("accent", "true")
        self._convert_btn.setEnabled(False)
        self._convert_btn.clicked.connect(self._on_convert)
        output_layout.addWidget(self._convert_btn)

        self._content_layout.addWidget(output_card)

        # Progress
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._content_layout.addWidget(self._progress_bar)

        # Results area
        self._results_layout = QVBoxLayout()
        self._content_layout.addLayout(self._results_layout)

        # Post-convert action buttons
        self._post_btn_row = QHBoxLayout()
        self._open_folder_btn = QPushButton(OPEN_FOLDER_TEXT)
        self._open_folder_btn.setProperty("flat", "true")
        self._open_folder_btn.setVisible(False)
        self._open_folder_btn.clicked.connect(self._on_open_output_folder)
        self._post_btn_row.addWidget(self._open_folder_btn)
        self._convert_more_btn = QPushButton(CONVERT_MORE_TEXT)
        self._convert_more_btn.setProperty("flat", "true")
        self._convert_more_btn.setVisible(False)
        self._convert_more_btn.clicked.connect(self._reset)
        self._post_btn_row.addWidget(self._convert_more_btn)
        self._post_btn_row.addStretch(1)
        self._content_layout.addLayout(self._post_btn_row)

        self._content_layout.addStretch(1)

    # --- Import ---

    def _on_browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import ATS Files", "", "ATS Inspection Files (*.xlsx)"
        )
        for path in paths:
            self._import_file(path)

    def _import_file(self, path: str) -> None:
        if path in self._imported or path in self._errors:
            return
        try:
            result = parse_ats_file(path)
            self._imported[path] = result
            card = _FileCard(path, result, self)
            card.remove_requested.connect(self._on_remove_file)
            self._file_list_layout.addWidget(card)
        except ATSParseError as exc:
            self._errors[path] = str(exc)
            self._file_list_layout.addWidget(_ErrorCard(path, str(exc), self))
        self._clear_all_btn.setEnabled(bool(self._imported) or bool(self._errors))
        self._refresh_flag_widget()
        self._update_convert_button()

    def _on_remove_file(self, path: str) -> None:
        self._imported.pop(path, None)
        self._errors.pop(path, None)
        # Rebuild file list widgets
        while self._file_list_layout.count():
            item = self._file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for p, r in self._imported.items():
            card = _FileCard(p, r, self)
            card.remove_requested.connect(self._on_remove_file)
            self._file_list_layout.addWidget(card)
        for p, e in self._errors.items():
            self._file_list_layout.addWidget(_ErrorCard(p, e, self))
        self._clear_all_btn.setEnabled(bool(self._imported) or bool(self._errors))
        self._refresh_flag_widget()
        self._update_convert_button()

    def _on_clear_all(self) -> None:
        self._imported.clear()
        self._errors.clear()
        while self._file_list_layout.count():
            item = self._file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._clear_all_btn.setEnabled(False)
        self._flags_confirmed = False
        self._flag_mapping = {}
        self._refresh_flag_widget()
        self._update_convert_button()

    # --- Flag review ---

    def _refresh_flag_widget(self) -> None:
        while self._flag_widget_layout.count():
            item = self._flag_widget_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._imported:
            self._flags_confirmed = False
            self._flag_mapping = {}
            return

        all_flags: dict[str, str] = {}
        for result in self._imported.values():
            all_flags.update(result.ats_flags)

        mapping_result = build_flag_mapping(all_flags)
        flag_widget = FlagReviewWidget(mapping_result, self)
        flag_widget.mappings_confirmed.connect(self._on_flags_confirmed)
        self._flag_widget_layout.addWidget(flag_widget)

    def _on_flags_confirmed(self, mapping: dict[str, str]) -> None:
        self._flag_mapping = mapping
        self._flags_confirmed = True
        self._update_convert_button()

    # --- Output ---

    def _on_browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self._output_folder_edit.text()
        )
        if folder:
            self._output_folder_edit.setText(folder)

    def _update_convert_button(self) -> None:
        self._convert_btn.setEnabled(bool(self._imported) and self._flags_confirmed)

    # --- Conversion ---

    def _on_convert(self) -> None:
        output_dir = Path(self._output_folder_edit.text())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create output folder: %s", exc)
            return

        jobs = list(self._imported.items())
        self._progress_bar.setMaximum(len(jobs))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._convert_btn.setEnabled(False)

        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._worker = _ConvertWorker(jobs, self._flag_mapping, output_dir, self)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_file_done(self, path: str, success: bool, error: str) -> None:
        self._progress_bar.setValue(self._progress_bar.value() + 1)
        icon = "✓" if success else "✗"
        style_color = color("success") if success else color("error")
        text = f"{icon} {Path(path).name}" + (f": {error}" if error else "")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {style_color};")
        self._results_layout.addWidget(lbl)

    def _on_all_done(self) -> None:
        self._progress_bar.setVisible(False)
        self._open_folder_btn.setVisible(True)
        self._convert_more_btn.setVisible(True)

    def _on_open_output_folder(self) -> None:
        folder = self._output_folder_edit.text()
        if folder:
            os.startfile(folder)  # Windows only

    def _reset(self) -> None:
        self._on_clear_all()
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._open_folder_btn.setVisible(False)
        self._convert_more_btn.setVisible(False)
```

- [ ] **Step 2: Wire ConverterPage into `app/window.py`**

Make these 7 edits to `app/window.py`:

**2a. Add import** — after the existing `from app.pages.email_page import EmailPage` line (line ~41), add:

```python
from app.pages.converter_page import ConverterPage
from app.pages.converter_page import STATUS_HINT as CONVERTER_STATUS_HINT
```

**2b. Add constant** — after `EMAIL_PAGE_INDEX = 8` (line ~98), add:

```python
CONVERTER_PAGE_INDEX = 9
CONVERTER_BUTTON_TEXT = "⇄ Converter"
```

**2c. Extend STATUS_HINTS** — the list currently has 9 entries (indices 0-8). Add a 10th:

```python
STATUS_HINTS = [
    DASHBOARD_STATUS_HINT,
    IMPORT_STATUS_HINT,
    REORDER_STATUS_HINT,
    GENERATE_STATUS_HINT,
    HISTORY_STATUS_HINT,
    SETTINGS_STATUS_HINT,
    BATCH_STATUS_HINT,
    PROJECTS_STATUS_HINT,
    EMAIL_STATUS_HINT,
    CONVERTER_STATUS_HINT,   # <-- add this
]
```

**2d. Add ConverterPage to stack** — in `_build_ui()`, after `self.email_page = EmailPage()` and its `self.stack.addWidget(self.email_page)` line, add:

```python
self.converter_page = ConverterPage()
self.stack.addWidget(self.converter_page)
```

**2e. Wire signals** — after `self.email_page.back_requested.connect(self._go_to_dashboard)`, add:

```python
self.converter_page.back_requested.connect(self._go_to_dashboard)
```

**2f. Add nav button** — in `_build_header()`, after the block that adds `self.email_nav_button`, add:

```python
self.converter_nav_button = QPushButton(CONVERTER_BUTTON_TEXT)
self.converter_nav_button.setProperty("flat", "true")
self.converter_nav_button.setToolTip("Open Data Converter (Ctrl+T)")
self.converter_nav_button.clicked.connect(self._go_to_converter)
layout.addWidget(self.converter_nav_button)
```

**2g. Add shortcut and navigation method** — in `_setup_shortcuts()`, add:

```python
self._add_shortcut("Ctrl+T", self._go_to_converter)
```

Add the method alongside the other `_go_to_*` methods:

```python
def _go_to_converter(self) -> None:
    self.stack.setCurrentIndex(CONVERTER_PAGE_INDEX)
```

Also update `_toggle_current_help()` — the current dict maps page indices to pages with help panels. Add the converter page:

```python
def _toggle_current_help(self) -> None:
    page = {
        1: self.import_page,
        2: self.reorder_page,
        3: self.generate_page,
        BATCH_PAGE_INDEX: self.batch_page,
        CONVERTER_PAGE_INDEX: self.converter_page,   # <-- add this
    }.get(self.stack.currentIndex())
    if page is not None:
        page.help_panel.toggle()
```

Also update `_activate_back_action()` — add CONVERTER_PAGE_INDEX to the pages that go to dashboard:

```python
elif index in (HISTORY_PAGE_INDEX, SETTINGS_PAGE_INDEX, BATCH_PAGE_INDEX, PROJECTS_PAGE_INDEX, CONVERTER_PAGE_INDEX):
    self._go_to_dashboard()
```

- [ ] **Step 3: Wire dashboard quick action in `app/pages/dashboard_page.py`**

**3a. Add signal** — after `email_requested = pyqtSignal()` in the class body, add:

```python
converter_requested = pyqtSignal()
```

**3b. Add constant** — at the top of the module with other text constants:

```python
CONVERT_DATA_TEXT = "Convert Data Files"
```

**3c. Add button** — in `_build_ui()`, after the `self.email_button` block (which adds the email button to `header_row`), add:

```python
self.converter_button = QPushButton(CONVERT_DATA_TEXT)
self.converter_button.setProperty("flat", "true")
self.converter_button.setToolTip("Convert ATS inspection files to Standard Format CSV")
self.converter_button.clicked.connect(self.converter_requested.emit)
header_row.addWidget(self.converter_button)
```

**3d. Wire in `app/window.py`** — after `self.dashboard_page.email_requested.connect(self._go_to_email)`, add:

```python
self.dashboard_page.converter_requested.connect(self._go_to_converter)
```

- [ ] **Step 4: Add Ctrl+T to keyboard shortcuts in `app/pages/settings_page.py`**

In `settings_page.py`, find the `KEYBOARD_SHORTCUTS` list (currently 7 entries at lines ~39-46). Add one more entry:

```python
KEYBOARD_SHORTCUTS = [
    ("Ctrl+N", "Start a new tracker"),
    ("Ctrl+D", "Go to the dashboard"),
    ("Ctrl+H", "View export history"),
    ("Ctrl+B", "Open batch generation"),
    ("Ctrl+,", "Open settings"),
    ("Ctrl+T", "Open Data Converter"),        # <-- add this
    ("Ctrl+→ / Ctrl+Enter", "Continue to the next step / Generate"),
    ("Ctrl+←", "Go back a step"),
]
```

- [ ] **Step 5: Run all tests**

```powershell
python -m pytest -q
```

Expected: 100+ tests, all pass. The page wiring is not unit-tested but the existing window tests exercise imports and instantiation.

- [ ] **Step 6: Verify the exe still builds**

```powershell
cmd /c build.bat
```

Expected: Build completes, exe appears in the temp output directory (or `dist/`). If it fails with a WinError about Dropbox locking `dist/`, re-run — intermittent.

- [ ] **Step 7: Commit**

```powershell
git add app/pages/converter_page.py app/window.py app/pages/dashboard_page.py app/pages/settings_page.py
git commit -m "Add Data Converter page and wire into main window (ATS Phase 1)"
```

---

### Task 7: Final push

**Files:** none new

- [ ] **Step 1: Run full test suite one final time**

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Push the branch**

```powershell
git push origin feature/data-converter
```

**Do NOT open a PR. Do NOT merge to main. Do NOT tag a release.** The branch is pushed for TRACE acceptance testing only.

- [ ] **Step 3: Confirm push**

```powershell
git log --oneline origin/feature/data-converter
```

Expected: your commits appear.
