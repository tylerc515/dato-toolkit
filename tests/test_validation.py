"""Tests for post-generation validation of tracker output files."""

from pathlib import Path

from app.builder import TrackerData, TrackerSection, build_tracker
from app.validation import validate_tracker_output

DATA = TrackerData(
    title="Test Tracker",
    customer="Acme",
    location="Plant 1",
    equipment="Boiler 1",
    date="2026",
    sections=[
        TrackerSection(name="FLOOR", elevations=["EL 1", "EL 2"]),
        TrackerSection(name="ROOF", elevations=["EL 3"]),
    ],
)


def test_valid_output_has_no_warnings(tmp_path):
    xlsx_path = build_tracker(DATA, tmp_path / "tracker.xlsx")
    assert validate_tracker_output(DATA, xlsx_path, None) == []


def test_missing_xlsx_warns(tmp_path):
    xlsx_path = tmp_path / "missing.xlsx"
    warnings = validate_tracker_output(DATA, xlsx_path, None)
    assert len(warnings) == 1
    assert "missing.xlsx" in warnings[0]


def test_unreadable_xlsx_warns(tmp_path):
    xlsx_path = tmp_path / "corrupt.xlsx"
    xlsx_path.write_text("not a real workbook")
    warnings = validate_tracker_output(DATA, xlsx_path, None)
    assert len(warnings) == 1
    assert "corrupt.xlsx" in warnings[0]


def test_fewer_rows_than_expected_warns(tmp_path):
    xlsx_path = build_tracker(DATA, tmp_path / "tracker.xlsx")
    extra_section = TrackerData(
        title=DATA.title,
        customer=DATA.customer,
        location=DATA.location,
        equipment=DATA.equipment,
        date=DATA.date,
        sections=[*DATA.sections, TrackerSection(name="EXTRA", elevations=["EL 4"])],
    )
    warnings = validate_tracker_output(extra_section, xlsx_path, None)
    assert len(warnings) == 1
    assert "fewer rows than expected" in warnings[0]


def test_missing_pdf_warns(tmp_path):
    xlsx_path = build_tracker(DATA, tmp_path / "tracker.xlsx")
    pdf_path = tmp_path / "tracker.pdf"
    warnings = validate_tracker_output(DATA, xlsx_path, pdf_path)
    assert len(warnings) == 1
    assert "tracker.pdf" in warnings[0]
