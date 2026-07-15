"""Tests for _MarkdownConverter in app/widgets/update_dialog.py."""

import re
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_update_dialog_module_has_no_hardcoded_hex():
    src = Path(__file__).resolve().parent.parent / "app" / "widgets" / "update_dialog.py"
    text = src.read_text(encoding="utf-8")
    hexes = re.findall(r"#[0-9A-Fa-f]{6}\b", text)
    assert hexes == [], f"hardcoded hex literals remain in update_dialog.py: {hexes}"


def test_update_dialog_instantiates_and_uses_token_properties():
    from app.updater import UpdateCheckResult
    from app.widgets.update_dialog import UpdateDialog

    info = UpdateCheckResult(
        update_available=True,
        current_version="2.2.4",
        latest_version="2.3.0",
        release_notes="## What's New\n- **Item** one\n- item two",
        download_url="https://example.invalid/DATOToolkit_v2.3.0.exe",
        release_url="https://example.invalid/release",
        published_at="2026-07-15T00:00:00Z",
    )
    dlg = UpdateDialog(info)
    assert dlg._download_btn.property("accent") == "true"
    assert dlg._install_btn.property("variant") == "success"


def test_markdown_h2_becomes_h3():
    from app.widgets.update_dialog import _MarkdownConverter
    html = _MarkdownConverter.to_html("## What's New")
    assert "<h3" in html
    assert "What's New" in html


def test_markdown_bullet_becomes_li():
    from app.widgets.update_dialog import _MarkdownConverter
    html = _MarkdownConverter.to_html("- item one\n- item two")
    assert html.count("<li>") == 2
    assert "item one" in html


def test_markdown_bold_becomes_b():
    from app.widgets.update_dialog import _MarkdownConverter
    html = _MarkdownConverter.to_html("**bold text** here")
    assert "<b>bold text</b>" in html


def test_markdown_plain_becomes_p():
    from app.widgets.update_dialog import _MarkdownConverter
    html = _MarkdownConverter.to_html("plain text here")
    assert "<p" in html
    assert "plain text here" in html


def test_markdown_ul_closed_before_heading():
    from app.widgets.update_dialog import _MarkdownConverter
    html = _MarkdownConverter.to_html("- item\n\n## Heading")
    # The </ul> must appear before the <h3>
    assert html.index("</ul>") < html.index("<h3")


def test_markdown_empty_string():
    from app.widgets.update_dialog import _MarkdownConverter
    html = _MarkdownConverter.to_html("")
    assert isinstance(html, str)
