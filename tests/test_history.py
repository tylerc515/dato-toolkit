from app.history import HistoryEntry, add_history_entry, load_history


def _entry(title: str, **overrides) -> HistoryEntry:
    fields = dict(
        title=title,
        customer="Acme",
        location="Plant 1",
        equipment="Boiler 2",
        date="2026-01-01",
        elevation_count=12,
        output_path="C:/out/tracker.xlsx",
        generated_at="2026-01-01T12:00:00",
    )
    fields.update(overrides)
    return HistoryEntry(**fields)


def test_load_history_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("app.history.get_app_data_dir", lambda: tmp_path)
    assert load_history() == []


def test_add_and_load_history_entry(tmp_path, monkeypatch):
    monkeypatch.setattr("app.history.get_app_data_dir", lambda: tmp_path)

    add_history_entry(_entry("Test Tracker"))

    entries = load_history()
    assert len(entries) == 1
    assert entries[0].title == "Test Tracker"
    assert entries[0].elevation_count == 12


def test_history_most_recent_first(tmp_path, monkeypatch):
    monkeypatch.setattr("app.history.get_app_data_dir", lambda: tmp_path)

    add_history_entry(_entry("First"))
    add_history_entry(_entry("Second"))

    entries = load_history()
    assert [e.title for e in entries] == ["Second", "First"]


def test_history_caps_at_max_entries(tmp_path, monkeypatch):
    monkeypatch.setattr("app.history.get_app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("app.history.MAX_HISTORY_ENTRIES", 3)

    for i in range(5):
        add_history_entry(_entry(str(i)))

    entries = load_history()
    assert len(entries) == 3
    assert [e.title for e in entries] == ["4", "3", "2"]
