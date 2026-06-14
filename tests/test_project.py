"""Tests for project save/load and fuzzy project matching."""

from app.project import (
    ProjectConfig,
    find_project_for_metadata,
    find_similar_project_for_metadata,
    list_projects,
)


def _config(**overrides) -> ProjectConfig:
    fields = dict(
        title="EP Anytown RB2",
        customer="Example Paper",
        location="Anytown",
        equipment="Recovery Boiler #2",
        date="June 2026",
    )
    fields.update(overrides)
    return ProjectConfig(**fields)


def test_find_project_for_metadata_exact_match(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    config = _config()
    path = config.save()

    found = find_project_for_metadata("Example Paper", "Anytown", "Recovery Boiler #2", "June 2026")
    assert found == path


def test_find_project_for_metadata_no_match(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    _config().save()

    assert find_project_for_metadata("Other Co", "Other Plant", "Other Boiler", "2025") is None


def test_find_similar_project_for_metadata_close_match(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    path = _config().save()

    # Slightly different date formatting should still match closely.
    found = find_similar_project_for_metadata("Example Paper", "Anytown", "Recovery Boiler #2", "June, 2026")
    assert found == path


def test_find_similar_project_for_metadata_excludes_exact_match(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    _config().save()

    # An exact match is handled by find_project_for_metadata, not the fuzzy lookup.
    found = find_similar_project_for_metadata("Example Paper", "Anytown", "Recovery Boiler #2", "June 2026")
    assert found is None


def test_find_similar_project_for_metadata_unrelated_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    _config().save()

    found = find_similar_project_for_metadata("Acme Corp", "Plant Nine", "Unit 7", "2030")
    assert found is None


def test_list_projects_sorted_most_recent_first(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True)

    older = _config(title="Older Project", last_modified="2026-01-01T00:00:00")
    newer = _config(title="Newer Project", last_modified="2026-06-01T00:00:00")
    (projects_dir / "older.json").write_text(json.dumps(older.to_dict()), encoding="utf-8")
    (projects_dir / "newer.json").write_text(json.dumps(newer.to_dict()), encoding="utf-8")

    results = list_projects()

    assert [config.title for _, config in results] == ["Newer Project", "Older Project"]
