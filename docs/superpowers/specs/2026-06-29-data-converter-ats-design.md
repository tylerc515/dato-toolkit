# Data Converter - ATS Phase 1 Design Spec

**Date:** 2026-06-29
**Branch:** `feature/data-converter`
**Version target:** not released yet (branch pushed for TRACE acceptance testing)

---

## Overview

Add a Data Converter module to DATO Toolkit. Phase 1 covers ATS (Applied Technical Services) `.xlsx` inspection files only. The converter reads ATS thickness data and produces Standard Format CSV files that TRACE can import. The Standard Format CSV is the same format already parsed by `app/parser.py`.

---

## Step 1 - Branch and file organization

### Branch

```bash
git checkout main && git pull origin main && git checkout -b feature/data-converter
```

### File moves (project root → examples/)

| Source (root) | Destination |
|---|---|
| `7-88-0525 - 01 FLOOR.xlsx` (and 6 siblings) | `examples/ats/` (keep original filenames with spaces) |
| `Standard-Sample_Left-to-Right.csv` | `examples/standard-format/` |
| `Standard-Sample_Right-to-Left.csv` | `examples/standard-format/` |
| `sample_tracksheet_2026.xlsx` | `examples/templates/reference_template.xlsx` (rename on move) |
| `Sample Update Email 2026.docx` | `examples/templates/` |
| `Standard CSV Format.docx` | `examples/templates/` |

Stub directories with `.gitkeep`:
- `examples/team/.gitkeep`
- `examples/tds/.gitkeep`

Examples/ is tracked in git (not gitignored).

### Code updates

`app/builder.py` lines 1 and 4 (comments only — no code paths reference the xlsx):
- Update mention of `sample_tracksheet_2026.xlsx` to `examples/templates/reference_template.xlsx`

`build.bat` — no changes needed. The reference template is not bundled in the exe.

---

## Step 2 - ATS parser

### File: `app/converters/ats_parser.py`

Pure module, no UI dependencies.

#### ATS file structure (sheet: "Thickness")

**Row 1 (index 0):**
- Col A: year (int)
- Col C: flag legend string e.g. `"NC - NOT CLEAN; RF - REFRACTORY;"` — may be blank

**Row 2 (index 1):**
- Col C: numbering direction sentence
  - Contains "LEFT TO RIGHT" → `"Left-to-Right"`
  - Contains "RIGHT TO LEFT" → `"Right-to-Left"`

**Row 3 (index 2) — header:**
- Col A: `"ELEVATION"`
- Col C: `"LOC"`
- Cols D onward: tube numbers (integers). Count stops at `"AVG"`, `"MIN"`, or any non-integer non-blank.

**Data rows (row 4 onward) — 3 rows per elevation block:**
- Block row 1: col A = tech code, col B = label part 1, col C = `"L"`, cols D+ = LEFT readings
- Block row 2: col A = nominal wall (float) or blank, col B = label part 2 (or blank), col C = `"C"`, cols D+ = CNTR readings
- Block row 3: col A = blank, col B = label part 3 (or blank), col C = `"R"`, cols D+ = RGHT readings

Elevation label: join non-blank col B values across all 3 rows with a single space. Strip each part.

Stop when a row has col A == `"ELEVATION"` and col C == `"LOC"` (repeat footer header).

**Metadata block (bottom-right corner, ~col CN):**

Scan rows `(max_row - 40)` to `max_row`. Find the cell containing `"TUBE WALL THICKNESS SURVEY"` as the anchor.

Relative to anchor row, all in the same column:
- anchor - 2: Company Name
- anchor - 1: Mill Location
- anchor + 0: `"TUBE WALL THICKNESS SURVEY"` (discard)
- anchor + 1: Boiler Name
- anchor + 2: Section name

NDE Lab: scan same row range for a cell that is a multi-line string (contains `"\n"`). Take the first line only, title-cased.
e.g. `"APPLIED TECHNICAL SERVICES\n1049 Triad Court\n..."` → `"Applied Technical Services"`

Date: scan for a cell containing `"Date:"`. Extract with regex `r"Date:\s*(\d{1,2})/(\d{2})/(\d{4})"`. Convert to `"Month YYYY"` format. e.g. `"5/05/2025"` → `"May 2025"`.

**Flag legend:**
Split row 1 col C on `";"`. Each part: split on `" - "` → `{code: description}`. Strip whitespace. Blank col C → `{}`.

**Reading conversion** (`convert_reading()` — standalone helper):
- `float` input: `round(value * 1000)` formatted as zero-padded 3 digits. e.g. `0.234` → `"234"`, `0.010` → `"010"`
- `None` or blank: `""`
- `str` (flag code): return as-is unchanged

Load files with `openpyxl`, `data_only=True`.

#### Dataclasses

```python
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

class ATSParseError(Exception):
    pass

def parse_ats_file(filepath: str | Path) -> ATSParseResult: ...
def convert_reading(value: object) -> str: ...
```

---

## Step 3 - Standard Format CSV writer

### File: `app/converters/standard_format_writer.py`

Writes the exact structure of `examples/standard-format/Standard-Sample_Left-to-Right.csv`. Uses `csv.writer` (not pandas).

**Column index mapping:** A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7

**Row layout:**

| Row index | Label col | Label content | Value col | Value content |
|---|---|---|---|---|
| 0 | E(4) | Excel format comment | — | — |
| 1 | E(4) | Font comment | — | — |
| 2-3 | — | blank | — | — |
| 4 | F(5) | `"Company Name:---->"` | H(7) | company_name |
| 5 | F(5) | `"Mill Location:---->"` | H(7) | mill_location |
| 6 | F(5) | `"Boiler Name:---->"` | H(7) | boiler_name |
| 7 | F(5) | `"Inspection Date:---->"` | H(7) | inspection_date |
| 8 | F(5) | `"Boiler Section:---->"` | H(7) | boiler_section |
| 9 | F(5) | `"Number of Tubes:---->"` | H(7) | num_tubes |
| 10 | F(5) | `"Numbering Direction:---->"` | H(7) | numbering_direction |
| 11 | F(5) | `"NDE Laboratory:---->"` | H(7) | nde_laboratory |
| 12-13 | — | blank | — | — |
| 14 | B(1) | `"TUBE NUMBERS along the top.---->"` | F(5)+ | tube numbers |
| 15 | — | blank | — | — |
| 16+ | — | elevation blocks (3 rows each) | — | — |
| after elevations | — | repeat tube number row | — | — |
| +1-2 | — | blank | — | — |
| +3+ | A(0) | `"FLAG - DESCRIPTION"` per flag | — | — |

**Elevation block (3 rows per elevation):**

| Sub-row | Col A | Col C | Col E | Col F+ |
|---|---|---|---|---|
| 1 | `"UT Tech Name:"` | elevation_label | `"LEFT"` | left readings |
| 2 | tech_code (or `"ATS"`) | — | `"CNTR"` | cntr readings |
| 3 | — | — | `"RGHT"` | rght readings |

Unknown flags not in `flag_mapping`: written as-is, warning logged.

```python
def write_standard_format(
    result: ATSParseResult,
    flag_mapping: dict[str, str],  # {ats_code: standard_code}
    output_path: str | Path,
) -> None: ...
```

---

## Step 4 - Flag mapping

### File: `app/converters/flag_mapper.py`

```python
DEFAULT_ATS_FLAG_MAP = {
    "RF": "(",   # Refractory
    "SI": ";",   # Signal interrupt
    "ST": "+",   # Stud
    "RT": ")",   # Recessed tube
    "NC": "<",   # Not clean
    "NS": "[",   # No scan
}

@dataclass
class FlagMappingResult:
    known: dict[str, str]    # flags auto-mapped from DEFAULT_ATS_FLAG_MAP
    unknown: dict[str, str]  # {ats_code: ats_description} not in defaults
    final: dict[str, str]    # complete mapping after user review

def build_flag_mapping(ats_flags: dict[str, str]) -> FlagMappingResult: ...
```

---

## Step 5 - Flag review widget

### File: `app/widgets/flag_review_widget.py`

`FlagReviewWidget(QWidget)` — shown on converter page when unknown flags are detected.

Layout:
- Heading: "Flag Review" (bold)
- Subtext description
- Table: ATS Code (read-only), ATS Description (read-only), Standard Format Code (editable, 3 chars max), Status badge ("Auto-mapped" green / "Needs mapping" yellow)
- Per-row checkbox: "Leave as-is" — disables the code field, passes ats_code unchanged
- "Confirm Mappings" button — disabled until all rows have a non-empty code or "Leave as-is" checked

Signal: `mappings_confirmed = pyqtSignal(dict)` — emits `{ats_code: standard_code}` for all flags.

If no unknown flags (all auto-mapped): skip widget, emit `mappings_confirmed` immediately on init.

---

## Step 6 - Converter page

### File: `app/pages/converter_page.py`

Accessible from:
- Dashboard quick actions: "Convert Data Files" button
- Header nav: "Converter" button (alongside existing nav buttons)

Sub-navigation (tabs or segmented control):
- ATS Files (active)
- TEAM Files (disabled, "Coming soon" tooltip)
- TDS Files (disabled, "Coming soon" tooltip)

**Section 1 — Import:**
Drop zone (`.xlsx` only, multi-file). File list with filename, section name, tube count, elevation count, remove button. Inline red error cards per failed parse. "Clear All" button.

**Section 2 — Flag Review:**
Embedded `FlagReviewWidget`. If all auto-mapped: slim green info bar with "View Mappings" toggle.

**Section 3 — Output:**
Output folder picker (default: Settings default or Desktop). Filename preview per file: `{section_name}_Standard_Format.csv`. "Convert All" button (accent, full width, disabled until import complete and flags confirmed).

**Progress and results:**
Progress bar during conversion. Results card: green checkmark per success, red X per failure with error message. "Open Output Folder" and "Convert More Files" (resets page) buttons.

**Help panel** (collapsible right panel, matching existing HelpPanel widget):
```
The Data Converter transforms ATS inspection files into the Standard
Format CSV that TRACE accepts for data import.

Import one or more ATS .xlsx files. The converter reads all inspection
data, metadata, and flag codes automatically from each file.

If your files contain flag codes that aren't in the auto-mapping list,
a review screen will appear so you can confirm or adjust the mapping
before converting.

One Standard Format CSV is produced per ATS file. Output files are
saved to your chosen output folder.
```

---

## Step 7 - Wiring

1. Import `ConverterPage` and add to `QStackedWidget` in `app/window.py`.
2. Add `CONVERTER_PAGE_INDEX` constant.
3. Header nav button: `"⇄ Converter"` (alongside existing nav buttons).
4. Dashboard quick action: `"Convert Data Files"` button.
5. Keyboard shortcut: `Ctrl+T` for converter (no existing binding).
6. Update help panel shortcut references on every page that lists shortcuts to include `Ctrl+T - Open Converter`.
7. Wire `converter_page.back_requested` → `_go_to_dashboard()`.

---

## Step 8 - Tests

### `tests/test_ats_parser.py`

Test against real files in `examples/ats/`. All file paths use actual names with spaces.

Corrections from original spec:
- **`test_blank_cells_stay_blank`**: remove `assert "NC" not in all_readings` — parser returns flags as-is; verify pass-through in `test_parse_floor_flags` instead
- **`test_output_parseable_by_dato_parser`**: `parsed.company_name` and `parsed.elevations` (dataclass attributes, not dict keys)

```python
# File path constants used in all tests
FLOOR = "examples/ats/7-88-0525 - 01 FLOOR.xlsx"
FRONT_WALL = "examples/ats/7-88-0525 - 02 FRONT WALL W PORTS.xlsx"
```

### `tests/test_standard_format_writer.py`

`test_output_parseable_by_dato_parser` corrected:
```python
parsed = parse_trace_csv(str(out))       # returns TraceFileData dataclass
assert parsed.company_name == "EXAMPLE PAPER"
assert len(parsed.elevations) == len(result.elevations)
```

---

## Step 9 - Build and push

```bash
pytest -q                                           # all tests pass
cmd /c build.bat                                    # verify exe builds
git add -A
git commit -m "Add Data Converter module (Phase 1 - ATS files)"
git push origin feature/data-converter
```

**Do NOT merge to main. Do NOT tag a release.** Branch is pushed for TRACE acceptance testing.

---

## Global constraints

- `app/parser.py` unmodified — Standard Format CSV output must be parseable by it as-is
- No new pip dependencies beyond `openpyxl` (already in project) and `requests` (already in project)
- `Ctrl+T` shortcut added to converter; update shortcut reference in all help panels that list shortcuts
- ATS file paths always use the actual filenames with spaces (no underscores)
- `convert_reading()` is a standalone public helper in `ats_parser.py`
- Existing 100 tests must all continue to pass
