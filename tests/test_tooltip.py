"""Tests for the tooltip wrapping helper."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QLabel, QToolTip, QWidget

from app.design.tokens import TOOLTIP_WRAP_THRESHOLD, TOOLTIP_WRAP_WIDTH
from app.design.tooltip import set_tooltip, wrap_tooltip

_qapp = QApplication.instance() or QApplication(sys.argv)

APP_DIR = Path(__file__).resolve().parent.parent / "app"
LONG_TEXT = "Drop one or more TRACE export .csv files here, or click to open a file browser."


def test_short_text_is_left_as_plain_text():
    assert wrap_tooltip("Minimize") == "Minimize"
    exactly = "x" * TOOLTIP_WRAP_THRESHOLD
    assert wrap_tooltip(exactly) == exactly


def test_long_text_is_wrapped_in_a_fixed_width_table():
    wrapped = wrap_tooltip(LONG_TEXT)
    assert wrapped.startswith(f'<table width="{TOOLTIP_WRAP_WIDTH}">')
    assert LONG_TEXT in wrapped


def test_long_text_is_html_escaped_and_newlines_become_breaks():
    wrapped = wrap_tooltip("Section <A> & B\n" + "y" * TOOLTIP_WRAP_THRESHOLD)
    assert "&lt;A&gt; &amp; B<br>" in wrapped
    assert "<A>" not in wrapped


def test_set_tooltip_applies_to_any_object_with_set_tool_tip():
    label = QLabel()
    set_tooltip(label, LONG_TEXT)
    assert label.toolTip() == wrap_tooltip(LONG_TEXT)

    class Item:
        text = ""

        def setToolTip(self, text: str) -> None:
            self.text = text

    item = Item()
    set_tooltip(item, "short")
    assert item.text == "short"


def test_long_tooltip_renders_no_wider_than_the_wrap_width():
    """The actual QToolTip window must wrap instead of running off screen."""
    anchor = QWidget()
    anchor.resize(200, 100)
    anchor.show()
    _qapp.processEvents()

    QToolTip.showText(QPoint(10, 10), wrap_tooltip(LONG_TEXT * 2), anchor)
    _qapp.processEvents()
    tips = [w for w in QApplication.topLevelWidgets() if w.isVisible() and w is not anchor]
    QToolTip.hideText()
    assert tips, "tooltip window did not appear"
    # Table width plus the tooltip's own padding and border.
    assert tips[0].width() <= TOOLTIP_WRAP_WIDTH + 40
    assert tips[0].height() > tips[0].fontMetrics().height() * 2, "expected multiple wrapped lines"


def test_every_app_tooltip_goes_through_set_tooltip():
    offenders = []
    for py in APP_DIR.rglob("*.py"):
        if py.name == "tooltip.py":
            continue
        if re.search(r"\.setToolTip\(", py.read_text(encoding="utf-8")):
            offenders.append(str(py.relative_to(APP_DIR)))
    assert offenders == [], f"Direct setToolTip calls (use set_tooltip): {offenders}"
