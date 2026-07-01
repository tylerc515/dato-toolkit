"""Tests for Standard Format CSV writer.

The round-trip test (write -> parse with parse_trace_csv) is the primary
correctness check. parse_trace_csv returns a TraceFileData dataclass -
access fields as attributes, not dict keys.
"""
from __future__ import annotations

import csv
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


def test_write_flag_mapping_translates_in_readings(tmp_path: Path):
    """Flag codes are translated in readings; fixed legend is always present."""
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<"}, out)
    content = out.read_text(encoding="utf-8")
    # The translated symbol should appear in the readings section
    assert "<" in content
    # The fixed legend is always written (contains reference symbols)
    assert "Structural interference" in content


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


# ---------------------------------------------------------------------------
# Bug 1 - tech name default
# ---------------------------------------------------------------------------

def test_tech_name_single_letter_becomes_ats(tmp_path: Path):
    """Single uppercase letter crew codes must be replaced with 'ATS'."""
    from app.converters.standard_format_writer import write_standard_format
    result = ATSParseResult(
        company_name="TEST CO",
        mill_location="Somewhere, TX",
        boiler_name="Boiler 1",
        inspection_date="January 2025",
        boiler_section="FLOOR",
        num_tubes=2,
        numbering_direction="Left-to-Right",
        nde_laboratory="ATS Lab",
        year=2025,
        ats_flags={},
        elevations=[
            ATSElevation(
                label="10 FT",
                tech_code="A",
                nominal_wall=0.220,
                left=["220", "215"],
                cntr=["218", "213"],
                rght=["222", "216"],
            ),
        ],
        tube_numbers=[1, 2],
    )
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out)
    rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
    # The CNTR row for each elevation has col-0 = tech name
    cntr_col0_values = [r[0] for r in rows if len(r) > 4 and r[4] == "CNTR"]
    assert cntr_col0_values, "No CNTR row found in output"
    assert all(v == "ATS" for v in cntr_col0_values), (
        f"Expected all CNTR col-0 values to be 'ATS', got: {cntr_col0_values}"
    )


def test_tech_name_real_name_preserved(tmp_path: Path):
    """Multi-character tech names must be written as-is."""
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()  # tech_code="JD" on both elevations
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out)
    rows = list(csv.reader(out.read_text(encoding="utf-8").splitlines()))
    cntr_col0_values = [r[0] for r in rows if len(r) > 4 and r[4] == "CNTR"]
    assert cntr_col0_values, "No CNTR row found in output"
    assert all(v == "JD" for v in cntr_col0_values), (
        f"Expected 'JD', got: {cntr_col0_values}"
    )


# ---------------------------------------------------------------------------
# Bug 2 - fixed legend (always written in full from reference file)
# ---------------------------------------------------------------------------

def _make_result_with_flags(flag_codes_in_cntr: list[str]) -> ATSParseResult:
    """Helper: build a 3-tube result where cntr readings contain the given flag codes."""
    padded = (flag_codes_in_cntr + ["", ""])[:3]
    return ATSParseResult(
        company_name="TEST CO",
        mill_location="Somewhere, TX",
        boiler_name="Boiler 1",
        inspection_date="January 2025",
        boiler_section="FLOOR",
        num_tubes=3,
        numbering_direction="Left-to-Right",
        nde_laboratory="ATS Lab",
        year=2025,
        ats_flags={"NC": "NOT CLEAN", "RF": "REFRACTORY"},
        elevations=[
            ATSElevation(
                label="10 FT",
                tech_code="AB",
                nominal_wall=0.220,
                left=["220", "215", "210"],
                cntr=padded,
                rght=["222", "216", "212"],
            ),
        ],
        tube_numbers=[1, 2, 3],
    )


def _find_legend_rows(output_path: Path) -> list[list[str]]:
    """Return all rows starting immediately after the second 'TUBE NUMBERS along the' row.

    Row 0 of the returned list is the blank separator that separates the footer
    from the symbol entries. The legend block is written as-is from
    load_standard_legend_block(), which includes that blank separator.
    """
    rows = list(csv.reader(output_path.read_text(encoding="utf-8").splitlines()))
    found = 0
    for i, row in enumerate(rows):
        if any("TUBE NUMBERS along the" in cell for cell in row):
            found += 1
            if found == 2:
                return rows[i + 1:]
    return []


def test_legend_always_written_in_full(tmp_path: Path):
    """Fixed legend is written even when no flag symbols appear in the data."""
    from app.converters.standard_format_writer import write_standard_format
    result = ATSParseResult(
        company_name="TEST CO",
        mill_location="Somewhere, TX",
        boiler_name="Boiler 1",
        inspection_date="January 2025",
        boiler_section="FLOOR",
        num_tubes=3,
        numbering_direction="Left-to-Right",
        nde_laboratory="ATS Lab",
        year=2025,
        ats_flags={},
        elevations=[
            ATSElevation(
                label="10 FT",
                tech_code="AB",
                nominal_wall=0.220,
                left=["220", "215", "210"],
                cntr=["218", "213", "208"],
                rght=["222", "216", "212"],
            ),
        ],
        tube_numbers=[1, 2, 3],
    )
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out)
    legend_rows = _find_legend_rows(out)
    # At least 13 rows: 1 blank separator + 12 symbol rows (R/V/N excluded from output)
    assert len(legend_rows) >= 13, (
        f"Expected at least 13 legend rows, got {len(legend_rows)}"
    )


def test_legend_matches_reference_file_exactly(tmp_path: Path):
    """Legend rows in output match the reference file block row-for-row.

    Row 0 must be the blank separator that follows the tube-numbers footer.
    """
    from app.converters.standard_format_writer import (
        load_standard_legend_block,
        write_standard_format,
    )
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<", "RF": "("}, out)
    legend_rows = _find_legend_rows(out)
    reference_block = load_standard_legend_block()

    # Row 0 must be the blank separator (all empty cells)
    assert legend_rows, "Expected at least one legend row"
    assert all(c == "" for c in legend_rows[0]), (
        f"Expected blank separator at legend_rows[0], got: {legend_rows[0]}"
    )

    assert len(legend_rows) == len(reference_block), (
        f"Expected {len(reference_block)} legend rows, got {len(legend_rows)}"
    )
    n_cols = max(8, 5 + result.num_tubes)
    for i, (out_row, ref_row) in enumerate(zip(legend_rows, reference_block)):
        padded_ref = (list(ref_row) + [""] * n_cols)[:n_cols]
        assert out_row == padded_ref, (
            f"Legend row {i} mismatch:\n  output:    {out_row}\n  reference: {padded_ref}"
        )


def test_legend_identical_regardless_of_flags_used(tmp_path: Path):
    """Legend block is byte-identical whether or not flag codes appear in the data."""
    from app.converters.standard_format_writer import write_standard_format
    # File 1: NC flag used
    result_with_flag = _make_result_with_flags(["NC"])
    out1 = tmp_path / "with_flag.csv"
    write_standard_format(result_with_flag, {"NC": "<"}, out1)

    # File 2: no flags used
    result_no_flag = _make_result_with_flags([])
    out2 = tmp_path / "no_flag.csv"
    write_standard_format(result_no_flag, {}, out2)

    legend1 = _find_legend_rows(out1)
    legend2 = _find_legend_rows(out2)

    assert legend1 == legend2, (
        "Legend block differs between files with and without flags"
    )


# ---------------------------------------------------------------------------
# Bug 4 - Excel-safe output toggle
# ---------------------------------------------------------------------------

def test_excel_safe_wraps_numeric_readings(tmp_path):
    """With excel_safe=True, numeric readings are wrapped as =\"value\"."""
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<"}, out, excel_safe=True)
    content = out.read_text(encoding="utf-8")
    # "234" should appear as ="234"
    assert '="234"' in content


def test_excel_safe_does_not_wrap_flag_symbols(tmp_path):
    """With excel_safe=True, non-numeric flag symbols are NOT wrapped."""
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<"}, out, excel_safe=True)
    content = out.read_text(encoding="utf-8")
    # "<" should NOT be wrapped
    assert '="<"' not in content


def test_excel_safe_false_writes_plain_strings(tmp_path):
    """With excel_safe=False (default), readings are plain strings."""
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out, excel_safe=False)
    content = out.read_text(encoding="utf-8")
    assert "234" in content
    assert '="234"' not in content


# ---------------------------------------------------------------------------
# Fix 2 - R/V/N reading-suffix codes excluded from output legend
# ---------------------------------------------------------------------------

def test_output_legend_excludes_rvn(tmp_path: Path):
    """R, V, N are reading-suffix codes and must not appear as legend entries."""
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result()
    out = tmp_path / "output.csv"
    write_standard_format(result, {}, out)
    legend_rows = _find_legend_rows(out)
    rvn = {"R", "V", "N"}
    for row in legend_rows:
        for cell in row:
            # Exact-value check: no bare R/V/N cell (avoids false positives from
            # words that contain those letters, e.g. "REMOVAL")
            assert cell.strip() not in rvn, (
                f"Legend row contains bare R/V/N cell value: {row}"
            )
            # First-token check: no cell whose leading symbol is R, V, or N
            parts = cell.strip().split()
            assert not (parts and parts[0] in rvn), (
                f"Legend row contains R/V/N symbol entry: {row}"
            )
