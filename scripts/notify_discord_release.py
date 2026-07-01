"""Posts a formatted Discord notification when a GitHub Release is published.

Reusable across tools -- when copying this into another repo, only the
config block below needs to change.

Usage:
    python scripts/notify_discord_release.py
        Reads the real GitHub Actions release event from $GITHUB_EVENT_PATH
        and posts to $DISCORD_WEBHOOK_URL, pinging $DISCORD_ANALYST_ROLE_ID.

    python scripts/notify_discord_release.py --dry-run
        Builds the payload from the real event but prints it instead of
        posting.

    python scripts/notify_discord_release.py --dry-run --sample
        Builds the payload from hardcoded sample data instead of reading
        a real event -- usable standalone, any time, with no GitHub
        Actions context or webhook configured.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

# Make `scripts` importable as a package whether this file is run directly
# (`python scripts/notify_discord_release.py`, as the GitHub Actions
# workflow does -- puts scripts/ itself on sys.path[0], not the repo root)
# or imported as a module (`from scripts.notify_discord_release import
# ...`, as the test suite does -- repo root is already on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.parse_release_notes import parse_release_notes

# --- Config: edit these when reusing this script in another repo ----------

TOOL_DISPLAY_NAME = "DATO Toolkit"
TOOL_BRAND_COLOR = 0x2563EB  # matches the new design system accent
TOOL_HAS_IN_APP_UPDATER = True
TOOL_ICON_URL = "https://raw.githubusercontent.com/tylerc515/dato-toolkit/main/assets/discord-icon.png"
GITHUB_REPO = "tylerc515/dato-toolkit"

# --- End config -------------------------------------------------------------

_FIELD_VALUE_MAX_LENGTH = 1024
_RAW_FALLBACK_TRUNCATE_LENGTH = 1000
_RAW_FALLBACK_SUFFIX = "…see full notes below"


def find_primary_asset(assets: list[dict]) -> dict | None:
    """Return the first release asset whose name ends in .exe, or None."""
    for asset in assets:
        if asset.get("name", "").endswith(".exe"):
            return asset
    return None


def _format_size_mb(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.1f}"


def _truncate_fallback(text: str) -> str:
    if len(text) <= _FIELD_VALUE_MAX_LENGTH:
        return text
    keep = _RAW_FALLBACK_TRUNCATE_LENGTH - len(_RAW_FALLBACK_SUFFIX)
    return text[:keep] + _RAW_FALLBACK_SUFFIX


def build_payload(
    release: dict,
    analyst_role_id: str,
    tool_display_name: str = TOOL_DISPLAY_NAME,
    tool_brand_color: int = TOOL_BRAND_COLOR,
    tool_icon_url: str = TOOL_ICON_URL,
    has_in_app_updater: bool = TOOL_HAS_IN_APP_UPDATER,
) -> dict:
    """Build the Discord webhook payload for a GitHub release event's `release` object."""
    tag_name = release.get("tag_name", "")
    html_url = release.get("html_url", "")
    published_at = release.get("published_at", "")
    body = release.get("body") or ""

    notes = parse_release_notes(body)
    asset = find_primary_asset(release.get("assets", []))

    fields: list[dict] = []

    if notes["whats_new"]:
        fields.append({
            "name": "✨ What's New",
            "value": "\n".join(f"• {line}" for line in notes["whats_new"]),
            "inline": False,
        })
    if notes["bug_fixes"]:
        fields.append({
            "name": "🐛 Bug Fixes",
            "value": "\n".join(f"• {line}" for line in notes["bug_fixes"]),
            "inline": False,
        })
    if notes["notes"]:
        fields.append({
            "name": "⚠️ Notes",
            "value": "\n".join(f"• {line}" for line in notes["notes"]),
            "inline": False,
        })
    if notes["raw_fallback"]:
        fields.append({
            "name": "📋 Release Notes",
            "value": _truncate_fallback(notes["raw_fallback"]),
            "inline": False,
        })

    if asset is not None:
        size_mb = _format_size_mb(asset.get("size", 0))
        fields.append({
            "name": "⬇️ Download",
            "value": f"[{asset['name']}]({asset['browser_download_url']})\n{size_mb} MB",
            "inline": True,
        })

    if has_in_app_updater:
        fields.append({
            "name": "🔄 Already installed?",
            "value": (
                "Open the app — it checks for updates automatically and will "
                "prompt you to install this version from the update banner."
            ),
            "inline": True,
        })

    fields.append({
        "name": "📄 Full Release Notes",
        "value": f"[View on GitHub]({html_url})",
        "inline": False,
    })

    return {
        "content": f"<@&{analyst_role_id}> **New release available — {tool_display_name}**",
        "allowed_mentions": {
            "parse": ["roles"],
            "roles": [analyst_role_id],
        },
        "embeds": [
            {
                "author": {
                    "name": tool_display_name,
                    "icon_url": tool_icon_url,
                },
                "title": f"🚀 {tag_name} is now available",
                "url": html_url,
                "color": tool_brand_color,
                "description": "A new version has been released. See what's changed below.",
                "fields": fields,
                "footer": {
                    "text": "Released by Tyler Chambers",
                    "icon_url": tool_icon_url,
                },
                "timestamp": published_at,
            }
        ],
    }


def sample_release_data() -> dict:
    """Hardcoded example release data for --sample mode and tests."""
    return {
        "tag_name": "v2.3.0",
        "html_url": f"https://github.com/{GITHUB_REPO}/releases/tag/v2.3.0",
        "published_at": "2026-07-01T18:00:00Z",
        "body": (
            "## What's New\n"
            "- New sidebar navigation and TRACE-inspired dark theme\n"
            "- Tooltips and help panels across every page\n\n"
            "## Bug Fixes\n"
            "- Fixed duplicate plus icon on the New Tracker button\n\n"
            "## Notes\n"
            "- Light theme is coming in a future update\n"
        ),
        "assets": [
            {
                "name": "DATOToolkit_v2.3.0.exe",
                "browser_download_url": f"https://github.com/{GITHUB_REPO}/releases/download/v2.3.0/DATOToolkit_v2.3.0.exe",
                "size": 87_115_397,
            }
        ],
    }


def _load_release_from_event(event_path: str) -> dict | None:
    """Return the `release` object from the GitHub Actions event JSON, or
    None if this event has no release data (e.g. a manual workflow_dispatch
    trigger, which has no `release` key at all)."""
    with open(event_path, encoding="utf-8") as f:
        event = json.load(f)
    return event.get("release")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print the payload instead of posting to Discord")
    parser.add_argument("--sample", action="store_true", help="Use hardcoded sample release data instead of a real event")
    args = parser.parse_args(argv)

    if args.sample:
        release = sample_release_data()
    else:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        release = _load_release_from_event(event_path) if event_path else None
        if release is None:
            # No real release data available (e.g. a manual workflow_dispatch
            # trigger, which has no `release` event context) -- fall back to
            # sample data so a manual/dry-run trigger never crashes.
            print("No release event data found; using sample data instead.", file=sys.stderr)
            release = sample_release_data()

    analyst_role_id = os.environ.get("DISCORD_ANALYST_ROLE_ID", "0")
    payload = build_payload(release, analyst_role_id)

    if args.dry_run:
        # Reconfigure stdout to UTF-8 so the emoji field names print as
        # actual characters rather than \uXXXX escapes -- ensure_ascii=False
        # alone would crash on Windows consoles whose default codepage
        # (e.g. cp1252) can't encode them.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL is not set.", file=sys.stderr)
        return 1

    response = requests.post(webhook_url, json=payload, timeout=10)
    if response.status_code not in (200, 204):
        print(f"Discord webhook post failed ({response.status_code}): {response.text}", file=sys.stderr)
        return 1

    print("Discord notification posted successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
