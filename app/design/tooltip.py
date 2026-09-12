"""Tooltip helper that keeps long tooltips on screen.

Qt shows a plain-text tooltip on a single line, however long, so a
sentence-length tip runs off the edge of the window. Rich-text tooltips
wrap, but Qt ignores ``max-width`` on a paragraph and picks a narrow
heuristic width instead; a fixed-width ``<table>`` is the one rich-text
form whose width Qt honours. :func:`set_tooltip` applies that wrapper to
any tip longer than ``TOOLTIP_WRAP_THRESHOLD`` characters and leaves short
tips as plain text. Every tooltip in the app goes through it.
"""

from __future__ import annotations

import html
from typing import Protocol

from app.design.tokens import TOOLTIP_WRAP_THRESHOLD, TOOLTIP_WRAP_WIDTH


class _HasToolTip(Protocol):
    def setToolTip(self, text: str) -> None: ...


def wrap_tooltip(text: str) -> str:
    """Return ``text`` unchanged if short, else wrapped so Qt word-wraps it."""
    if len(text) <= TOOLTIP_WRAP_THRESHOLD:
        return text
    body = html.escape(text).replace("\n", "<br>")
    return f'<table width="{TOOLTIP_WRAP_WIDTH}"><tr><td>{body}</td></tr></table>'


def set_tooltip(target: _HasToolTip, text: str) -> None:
    """Set a tooltip on any widget, item, or tray icon, wrapping long text."""
    target.setToolTip(wrap_tooltip(text))
