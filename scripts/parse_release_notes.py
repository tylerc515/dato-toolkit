"""Parses GitHub release-notes bodies structured with '## What's New' /
'## Bug Fixes' / '## Notes' headings.

Shared between the in-app updater and scripts/notify_discord_release.py
so both consume identical parsing behavior.
"""

from __future__ import annotations

_SECTION_HEADINGS = {
    "what's new": "whats_new",
    "bug fixes": "bug_fixes",
    "notes": "notes",
}


def parse_release_notes(body: str) -> dict:
    """
    Returns:
    {
        "whats_new": ["line 1", "line 2", ...],   # from ## What's New
        "bug_fixes": [...],                        # from ## Bug Fixes
        "notes": [...],                             # from ## Notes
        "raw_fallback": str | None,  # if no structured headings found,
                                       # the full body as-is
    }
    Each list contains bullet lines with the leading "- " stripped.
    If the body has no recognizable structure, whats_new/bug_fixes/notes
    are all empty lists and raw_fallback contains the original text.
    """
    result: dict = {"whats_new": [], "bug_fixes": [], "notes": [], "raw_fallback": None}

    lines = body.splitlines()
    current_key: str | None = None
    found_any_heading = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            heading_text = stripped[3:].strip().lower()
            current_key = _SECTION_HEADINGS.get(heading_text)
            if current_key is not None:
                found_any_heading = True
            continue
        if current_key is not None and stripped.startswith("- "):
            result[current_key].append(stripped[2:].strip())

    if not found_any_heading:
        result["raw_fallback"] = body

    return result
