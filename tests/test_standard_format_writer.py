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
    # Legend uses STANDARD_SYMBOL_DESCRIPTIONS; "<" has no confirmed description,
    # so the writer falls back to the symbol itself.
    assert "means <" in content


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
    import csv
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
    import csv
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
# Bug 2 - dynamic legend
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


def test_legend_generated_from_actual_flags(tmp_path: Path):
    """Legend lists only symbols that appear in the converted output."""
    from app.converters.standard_format_writer import write_standard_format
    # Only NC (maps to "<") appears; RF (maps to "(") does not appear
    result = _make_result_with_flags(["NC"])
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<", "RF": "("}, out)
    content = out.read_text(encoding="utf-8")
    # "<" has no confirmed description so the legend falls back to the symbol itself
    assert " <    means <." in content, "Expected '<' legend line"
    assert " (    means" not in content, "RF symbol should not appear in legend"


def test_legend_omits_unused_symbols(tmp_path: Path):
    """Flag mapping symbols not used in output do not appear in legend."""
    from app.converters.standard_format_writer import write_standard_format
    result = _make_result_with_flags(["NC"])
    out = tmp_path / "output.csv"
    write_standard_format(result, {"NC": "<", "RF": "("}, out)
    content = out.read_text(encoding="utf-8")
    legend_lines = [ln for ln in content.splitlines() if "means" in ln]
    assert len(legend_lines) == 1, (
        f"Expected exactly 1 legend line, got {len(legend_lines)}: {legend_lines}"
    )


def test_legend_omitted_when_no_flags_present(tmp_path: Path):
    """When no flag symbols appear in the data, legend block is absent."""
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
    content = out.read_text(encoding="utf-8")
    assert "means" not in content, (
        "No legend lines expected when data has no flag symbols"
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
