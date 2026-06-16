"""Tests for _MarkdownConverter in app/widgets/update_dialog.py."""


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
