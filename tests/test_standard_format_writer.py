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
