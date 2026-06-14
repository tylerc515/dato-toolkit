"""Tests for project save/load and fuzzy project matching."""

from app.project import (
    ProjectConfig,
    find_project_for_metadata,
    find_similar_project_for_metadata,
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
