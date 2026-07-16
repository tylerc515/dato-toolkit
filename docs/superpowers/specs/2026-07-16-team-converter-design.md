# TEAM Data Converter - Design Spec

**Date:** 2026-07-16
**Branch:** `feature/team-converter` (from main @ post-v2.3.0)
**Status:** Confirmed - ready for implementation plan

## Overview

Add TEAM file support to the existing Data Converter, filling the
already-present (currently disabled) "TEAM" tab in
`app/pages/converter_page.py`. TEAM files are structurally similar to
ATS (3-row L/C/R elevation blocks) but differ in three ways:

1. No embedded metadata anywhere - the user supplies it manually, once
   per batch.
2. Readings are pre-converted integers (no ATS-style decimal->int
   conversion).
3. Flag characters are already Standard Format symbols directly, not
   codes needing translation.

The converter reuses existing ATS infrastructure rather than
duplicating it: `standard_format_writer.write_standard_format`,
`STANDARD_SYMBOL_DESCRIPTIONS`, and `FlagReviewWidget` are shared. The
shipped ATS flow must not regress - all TEAM work is additive.

### Structure confirmed against the real files

A scan of `examples/team/FLOOR.xlsx` and `FLOOR MLO.xlsx` confirms:
row 1 has tube numbers from column C (cols A/B blank); data is 3-row
blocks with column B = L/C/R and column A = label fragments on varying
rows; blank blocks (all reading cells empty) are placeholder templates
to skip; a block containing only flag symbols (e.g. `<,<,<`) is real
data and is kept; readings are integers; flags seen include `*` and
`<`; no metadata rows exist.

## 1. Parser - `app/converters/team_parser.py`

### File structure
- **Row 1:** tube numbers from column C onward. First tube number `1`
  => Left-to-Right; otherwise Right-to-Left. No flag-legend row and no
  numbering-direction sentence row (unlike ATS).
- **Data rows:** 3-row blocks. Column A = elevation label fragment (may
  appear on any of the 3 rows); concatenate all non-blank fragments
  across the block, stripping whitespace, using the same join rule as
  ATS. Column B = L/C/R. Columns C+ = readings.
- **No tech-code column** (nothing equivalent to ATS's column A tech
  letter / nominal wall value).
- **Skip rule:** if every reading cell in a 3-row block (columns C
  through the last tube column) is blank, skip the block - it is an
  unmeasured template placeholder. A block with any non-blank reading
  cell, including a flag symbol, is real and kept.
- **No metadata** anywhere in the file.

### Reading conversion - `convert_team_reading(value) -> str`
- Integer (already in thousandths): zero-pad to 3 digits. `58`->`"058"`,
  `214`->`"214"`.
- `None`/blank: `""`.
- Single-character string flag (`"*"`, `"<"`): return unchanged.
- Numeric string with a trailing letter suffix (regex `^\d+[A-Za-z]$`,
  e.g. `"14V"`): zero-pad the numeric part to 3 digits, preserve the
  suffix exactly -> `"014V"`. Never strip or reject a suffix. (Synthetic
  case; not present in the 7 samples but confirmed possible.)
- Out-of-range values (e.g. the `2791` anomaly in one sample): write
  through as-is, zero-padded to its own digit count. Do not reject,
  validate, or flag - a known human data-entry error class caught
  downstream, not the converter's job.

### Dataclasses / API
```python
@dataclass
class TEAMElevation:
    label: str
    left: list[str]
    cntr: list[str]
    rght: list[str]

@dataclass
class TEAMParseResult:
    tube_numbers: list[int]
    numbering_direction: str   # "Left-to-Right" | "Right-to-Left"
    num_tubes: int
    elevations: list[TEAMElevation]
    flags_found: set[str]      # every unique non-numeric symbol seen

class TEAMParseError(Exception): ...

def parse_team_file(filepath: str | Path) -> TEAMParseResult: ...
def convert_team_reading(value: object) -> str: ...
```
`TEAMParseResult` has **no** metadata fields - those are supplied at
the batch level.

## 2. Flag handling - extends `app/converters/flag_mapper.py`

Add `check_team_flags(flags_found: set[str]) -> FlagMappingResult`
(does not replace ATS's `build_flag_mapping`):
- Symbol present in `STANDARD_SYMBOL_DESCRIPTIONS` => known, auto-mapped
  to itself (symbol -> symbol), no review.
- Symbol absent => unknown, needs manual review via `FlagReviewWidget`.
- **No Tier-2 smart-match** (TEAM files carry no per-flag description
  text to fuzzy-match). An unknown TEAM flag goes straight to manual
  picker selection with no pre-filled suggestion.

`FlagReviewWidget` is reused as-is. For a known TEAM symbol needing
display, the Description column shows the Standard Format's own
description from `STANDARD_SYMBOL_DESCRIPTIONS`; genuinely unknown
symbols show blank/"Unknown". Common case (all 5 real flags `* < ; [ &`
are known): zero flags need review, skip straight to metadata entry.

## 3. UI - TEAM tab in `converter_page.py`

The page already renders disabled "TEAM"/"TDS" pill tabs
(`TEAM_TAB_TEXT`, `TDS_TAB_TEXT`) beside the active "ATS" tab. This work
makes the tab system functional and adds the TEAM flow behind the TEAM
tab, additively, leaving the ATS flow intact.

### TEAM flow
1. **Tab switch:** clicking TEAM shows the TEAM view; ATS view is
   preserved. (TDS stays disabled/coming-soon.)
2. **Import:** drop zone - "Drop TEAM .xlsx files here, or click to
   browse. One batch = one inspection on one piece of equipment -
   company, mill, boiler, and date apply to every file in this batch."
3. Files parse on import; each file's card shows tube count, direction,
   elevation count, flags found (same card pattern as ATS).
4. **Metadata form** (appears once >=1 file imported, above flag
   review/output):
   - Company Name (text), Mill Location (text), Boiler Name (text),
     Inspection Date (**Month dropdown + Year dropdown/spinbox** ->
     `"Month YYYY"`), NDE Laboratory (text).
   - All five required. Convert All disabled until all are non-empty.
5. **Per-file section name:** shown in each file card, auto-suggested
   from the filename (strip extension, replace underscores with spaces:
   `SOOTBLOWER_PASS_A.xlsx` -> `SOOTBLOWER PASS A`), editable inline,
   required (cannot be blank).
6. **Flag review:** only if `check_team_flags()` finds an unknown symbol
   across the batch. Same widget as ATS.
7. **Output:** folder picker with persistence, overwrite confirmation
   listing conflicts, friendly permission-error messages, Convert All.
   This output machinery is currently wired to ATS types in
   `converter_page`; generalize the shared parts additively so both
   flows use them (do not fork/duplicate).

### Shared vs per-file in a batch
| Field | Scope | Source |
|---|---|---|
| Company, Mill, Boiler, Date, NDE Lab | Once per batch | Manual entry |
| Section name | Per file | Filename default, editable |
| Tube count, Direction | Per file | Auto-derived |
| Flag mappings | Once per batch | Applies to all files |

## 4. Writer - reuse `standard_format_writer.py` unchanged

`write_standard_format(result, flag_mapping, out_path)` is duck-typed:
it reads `result.company_name`, `.mill_location`, `.boiler_name`,
`.inspection_date`, `.boiler_section`, `.num_tubes`,
`.numbering_direction`, `.nde_laboratory`, `.tube_numbers`,
`.elevations`. `TEAMElevation` matches `ATSElevation`'s shape.

Therefore **no writer change**. Add a `TEAMConversionInput` dataclass
carrying all eight metadata fields plus `tube_numbers`, `num_tubes`,
`numbering_direction`, and `elevations`, built from a `TEAMParseResult`
+ the batch metadata form + the per-file section name (mapped to
`boiler_section`). Pass it straight to the unchanged writer. This is the
"shared implicit interface" option (option 1), realized with zero
changes to the shipped ATS path.

Legend-writing (fixed universal block from the reference file) is
already file-type-agnostic - no change.

## 5. Output filename

`{section}_Standard_Format.csv`, matching ATS's `_output_filename`
(with `/` and `\` stripped from the section). The section is the
per-file editable section name.

## 6. Tests

Real files live in `examples/team/` and are **local/untracked**
(gitignored `*.xlsx`); tests parse them in place, same pattern as
`test_ats_parser` and the reference tracksheet fixtures. Tests are not
reproducible on a fresh clone without the files present - an accepted
tradeoff (the real client readings stay out of the public repo).

`tests/test_team_parser.py`:
- Metadata-free parsing (assert the result has no metadata fields).
- Direction detection (all 7 samples are Left-to-Right; add a synthetic
  Right-to-Left case).
- Blank template-row skipping (`FLOOR MLO` has many placeholder blocks;
  only the populated ones appear).
- Reading conversion: integer zero-padding, the suffix-letter case
  (synthetic), the `2791` anomaly passing through unmodified.
- Flag detection: the real flags are collected in `flags_found`.

`tests/test_flag_mapper.py` additions:
- `check_team_flags()` all-known set -> no unknowns, no review.
- `check_team_flags()` with an unknown symbol -> flagged for review,
  no smart-match suggestion attached.

`tests/test_converter_page.py` additions (or new
`tests/test_team_converter_ui.py`):
- Metadata form validation (Convert All disabled until all 5 filled).
- Per-file section name defaults from filename.
- Batch-wide flag mapping applies to all files.
- Tab switching shows the TEAM view without breaking the ATS view.

`pytest -q` - all existing tests must still pass; report the final count.

## Global constraints

- No hex/pixel/font-size literal outside `app/design/tokens.py`; use the
  token/property styling system for any new UI.
- Do not regress the shipped ATS converter flow - TEAM is additive.
- No em dashes or en dashes in code/comments/copy.
- Commit email `4742780+tylerc515@users.noreply.github.com`.
- Run tests with `QT_QPA_PLATFORM=offscreen`.
- The `~$FLOOR.xlsx` Excel lock file in `examples/team/` must not be
  committed (already covered by gitignore).

## Files touched (anticipated)

- Create: `app/converters/team_parser.py`, `tests/test_team_parser.py`
  (and possibly `tests/test_team_converter_ui.py`).
- Modify: `app/converters/flag_mapper.py` (`check_team_flags`),
  `app/pages/converter_page.py` (functional tabs + TEAM flow + metadata
  form + generalized output wiring), `tests/test_flag_mapper.py`,
  `tests/test_converter_page.py`.
- Reused unchanged: `standard_format_writer.py`, `flag_review_widget.py`,
  `STANDARD_SYMBOL_DESCRIPTIONS`.

## Decisions locked
- Writer: `TEAMConversionInput` + unchanged duck-typed writer (option 1).
- Date input: Month + Year dropdowns -> `"Month YYYY"`.
- Filename: `{section}_Standard_Format.csv`.
- Samples: local/untracked.
- UI: functional TEAM tab in the existing converter page, additive to ATS.
