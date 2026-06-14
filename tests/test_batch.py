"""Tests for batch scanning and generation of trackers from a folder of CSVs."""

from pathlib import Path

from app.batch import generate_group, group_files, scan_folder
from app.history import load_history
from app.parser import ElevationData, TraceFileData, parse_trace_csv
from app.project import get_projects_dir

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _file(company: str, location: str, boiler: str, date: str, section: str, source: str) -> TraceFileData:
    return TraceFileData(
        source_path=source,
        company_name=company,
        mill_location=location,
        boiler_name=boiler,
        inspection_date=date,
        boiler_section=section,
        number_of_tubes=2,
        numbering_direction="",
        nde_laboratory=None,
        elevations=[ElevationData(label="EL 1", left=["1"], cntr=["2"], rght=["3"])],
    )


def test_group_files_groups_by_metadata_preserving_order():
    files = [
        _file("Acme", "Plant A", "Boiler 1", "2026", "FLOOR", "a.csv"),
        _file("Acme", "Plant B", "Boiler 2", "2025", "ROOF", "b.csv"),
        _file("Acme", "Plant A", "Boiler 1", "2026", "WALL", "c.csv"),
    ]

    groups = group_files(files)

    assert len(groups) == 2
    assert [f.source_path for f in groups[0].files] == ["a.csv", "c.csv"]
    assert [f.source_path for f in groups[1].files] == ["b.csv"]
    assert groups[0].customer == "Acme"
    assert groups[0].location == "Plant A"


def test_scan_folder_groups_fixture_csvs():
    result = scan_folder(FIXTURES_DIR)

    assert result.errors == []
    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.customer == "Example Paper"
    assert [Path(f.source_path).stem for f in group.files] == ["FLOOR", "FRONT_WALL_MLO", "FRONT_WALL_W_PORTS"]


def test_scan_folder_reports_unreadable_csv(tmp_path):
    (tmp_path / "bad.csv").write_text("not,a,valid,trace,export\n", encoding="utf-8")

    result = scan_folder(tmp_path)

    assert result.groups == []
    assert len(result.errors) == 1
    assert "bad.csv" in result.errors[0].path


def test_generate_group_writes_xlsx_and_records_history(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("app.history.get_app_data_dir", lambda: tmp_path)

    files = [parse_trace_csv(FIXTURES_DIR / name) for name in ("FLOOR.csv", "FRONT_WALL_MLO.csv")]
    groups = group_files(files)
    assert len(groups) == 1
    group = groups[0]

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate_group(group, output_dir, export_pdf=False)

    assert result.error is None
    assert result.xlsx_path is not None
    assert result.xlsx_path.exists()
    assert result.warnings == []

    history = load_history()
    assert len(history) == 1
    assert history[0].title == group.title
    assert history[0].output_path == str(result.xlsx_path)

    saved_projects = list(get_projects_dir().glob("*.json"))
    assert len(saved_projects) == 1
