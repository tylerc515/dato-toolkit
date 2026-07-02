"""Tests for scripts/notify_discord_release.py's payload-building logic.

Does not test the actual HTTP POST -- only build_payload() and its
helpers, which are pure functions of release data.
"""
from __future__ import annotations

import json

from scripts.notify_discord_release import (
    build_payload,
    find_primary_asset,
    main,
    sample_release_data,
)


def test_payload_includes_role_ping_in_content():
    payload = build_payload(sample_release_data(), analyst_role_id="123")
    assert "<@&123>" in payload["content"]
    # Discord's API rejects "parse": ["roles"] combined with an explicit
    # "roles" allowlist (400: mutually exclusive) -- confirmed against the
    # real webhook. The allowlist alone is the correct, working structure.
    assert payload["allowed_mentions"] == {"roles": ["123"]}


def test_payload_omits_empty_fields():
    release = sample_release_data()
    release["body"] = "## What's New\n- Feature A\n"  # no Bug Fixes / Notes sections
    payload = build_payload(release, analyst_role_id="123")
    field_names = [f["name"] for f in payload["embeds"][0]["fields"]]
    assert "✨ What's New" in field_names
    assert "🐛 Bug Fixes" not in field_names
    assert "⚠️ Notes" not in field_names


def test_payload_includes_all_three_note_sections_when_present():
    payload = build_payload(sample_release_data(), analyst_role_id="123")
    field_names = [f["name"] for f in payload["embeds"][0]["fields"]]
    assert "✨ What's New" in field_names
    assert "🐛 Bug Fixes" in field_names
    assert "⚠️ Notes" in field_names


def test_download_field_present_when_asset_found():
    payload = build_payload(sample_release_data(), analyst_role_id="123")
    field_names = [f["name"] for f in payload["embeds"][0]["fields"]]
    assert "⬇️ Download" in field_names
    download_field = next(f for f in payload["embeds"][0]["fields"] if f["name"] == "⬇️ Download")
    assert "DATOToolkit" in download_field["value"]
    assert "MB" in download_field["value"]


def test_download_field_absent_when_no_exe_asset():
    release = sample_release_data()
    release["assets"] = [{"name": "source.zip", "browser_download_url": "https://example.com/x.zip", "size": 100}]
    payload = build_payload(release, analyst_role_id="123")
    field_names = [f["name"] for f in payload["embeds"][0]["fields"]]
    assert "⬇️ Download" not in field_names


def test_in_app_update_field_respects_config_flag():
    payload_with = build_payload(sample_release_data(), analyst_role_id="123", has_in_app_updater=True)
    field_names_with = [f["name"] for f in payload_with["embeds"][0]["fields"]]
    assert "🔄 Already installed?" in field_names_with

    payload_without = build_payload(sample_release_data(), analyst_role_id="123", has_in_app_updater=False)
    field_names_without = [f["name"] for f in payload_without["embeds"][0]["fields"]]
    assert "🔄 Already installed?" not in field_names_without


def test_full_notes_link_always_present():
    payload = build_payload(sample_release_data(), analyst_role_id="123")
    field_names = [f["name"] for f in payload["embeds"][0]["fields"]]
    assert "📄 Full Release Notes" in field_names


def test_raw_fallback_field_truncated_and_capped():
    release = sample_release_data()
    release["body"] = "x" * 2000  # unstructured, exceeds Discord's 1024 field cap
    payload = build_payload(release, analyst_role_id="123")
    fallback_field = next(f for f in payload["embeds"][0]["fields"] if f["name"] == "📋 Release Notes")
    assert len(fallback_field["value"]) <= 1024
    assert fallback_field["value"].endswith("…see full notes below")


def test_embed_title_and_url_use_release_data():
    release = sample_release_data()
    payload = build_payload(release, analyst_role_id="123")
    embed = payload["embeds"][0]
    assert release["tag_name"] in embed["title"]
    assert embed["url"] == release["html_url"]
    assert embed["timestamp"] == release["published_at"]


def test_find_primary_asset_picks_first_exe():
    assets = [
        {"name": "source.zip", "browser_download_url": "https://example.com/a.zip", "size": 10},
        {"name": "DATOToolkit_v2.3.0.exe", "browser_download_url": "https://example.com/b.exe", "size": 85_000_000},
        {"name": "another.exe", "browser_download_url": "https://example.com/c.exe", "size": 1},
    ]
    asset = find_primary_asset(assets)
    assert asset is not None
    assert asset["name"] == "DATOToolkit_v2.3.0.exe"


def test_find_primary_asset_returns_none_when_no_exe():
    assets = [{"name": "source.zip", "browser_download_url": "https://example.com/a.zip", "size": 10}]
    assert find_primary_asset(assets) is None


def test_main_falls_back_to_sample_when_event_has_no_release_key(tmp_path, monkeypatch, capsys):
    """A manual workflow_dispatch trigger has no `release` key in its event
    JSON at all -- main() must fall back to sample data instead of crashing
    with a KeyError, since Tyler's own verification plan triggers the
    workflow this way."""
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"action": "workflow_dispatch", "inputs": {"dry_run": "true"}}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("DISCORD_ANALYST_ROLE_ID", "999")

    exit_code = main(["--dry-run"])

    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "<@&999>" in payload["content"]
