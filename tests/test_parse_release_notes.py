"""Tests for the shared release-notes parser (scripts/parse_release_notes.py)."""
from __future__ import annotations

from scripts.parse_release_notes import parse_release_notes


def test_parses_structured_notes():
    body = "## What's New\n- Feature A\n- Feature B\n\n## Bug Fixes\n- Fixed X\n"
    result = parse_release_notes(body)
    assert result["whats_new"] == ["Feature A", "Feature B"]
    assert result["bug_fixes"] == ["Fixed X"]
    assert result["notes"] == []
    assert result["raw_fallback"] is None


def test_falls_back_on_unstructured_notes():
    body = "Just some plain text with no headings."
    result = parse_release_notes(body)
    assert result["whats_new"] == []
    assert result["bug_fixes"] == []
    assert result["notes"] == []
    assert result["raw_fallback"] == body


def test_parses_all_three_sections():
    body = (
        "## What's New\n- Feature A\n\n"
        "## Bug Fixes\n- Fixed X\n- Fixed Y\n\n"
        "## Notes\n- Requires a restart\n"
    )
    result = parse_release_notes(body)
    assert result["whats_new"] == ["Feature A"]
    assert result["bug_fixes"] == ["Fixed X", "Fixed Y"]
    assert result["notes"] == ["Requires a restart"]
    assert result["raw_fallback"] is None


def test_missing_section_is_empty_list_not_fallback():
    """Only one heading present -- the other two are empty lists, not a raw fallback."""
    body = "## What's New\n- Only this section\n"
    result = parse_release_notes(body)
    assert result["whats_new"] == ["Only this section"]
    assert result["bug_fixes"] == []
    assert result["notes"] == []
    assert result["raw_fallback"] is None


def test_empty_body_falls_back():
    result = parse_release_notes("")
    assert result["whats_new"] == []
    assert result["bug_fixes"] == []
    assert result["notes"] == []
    assert result["raw_fallback"] == ""


def test_bullet_prefix_stripped_but_other_text_preserved():
    body = "## What's New\n- Added dark mode support\n"
    result = parse_release_notes(body)
    assert result["whats_new"] == ["Added dark mode support"]
