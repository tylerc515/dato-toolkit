"""Tests for project save/load and fuzzy project matching."""

from app.project import (
    AuxItem,
    ProjectConfig,
    find_project_for_metadata,
    find_similar_project_for_metadata,
    list_projects,
    load_project,
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


def test_aux_items_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    items = [
        AuxItem(id="a1", description="PT OF COMPOSITE PORTS", notes=""),
        AuxItem(id="a2", description="RT OF ECONOMIZER", notes="Complete"),
    ]
    config = _config(auxiliary_items=items)
    path = config.save()
    loaded = load_project(path)
    assert len(loaded.auxiliary_items) == 2
    assert loaded.auxiliary_items[0].description == "PT OF COMPOSITE PORTS"
    assert loaded.auxiliary_items[1].notes == "Complete"


def test_punchlist_items_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    items = [AuxItem(id="p1", description="ITEM 37\nUT spout 2 tube 38", notes='Reading: .286"')]
    config = _config(punchlist_items=items)
    path = config.save()
    loaded = load_project(path)
    assert loaded.punchlist_items[0].notes == 'Reading: .286"'


def test_project_without_aux_fields_loads_fine(tmp_path, monkeypatch):
    """Existing project JSON without auxiliary_items/punchlist_items loads as empty lists."""
    import json
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True)
    old_data = _config().to_dict()
    old_data.pop("auxiliary_items", None)
    old_data.pop("punchlist_items", None)
    path = projects_dir / "old.json"
    path.write_text(json.dumps(old_data), encoding="utf-8")
    loaded = load_project(path)
    assert loaded.auxiliary_items == []
    assert loaded.punchlist_items == []
