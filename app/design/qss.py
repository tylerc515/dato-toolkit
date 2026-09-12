"""Scoped per-widget stylesheet helpers.

Qt applies a widget's stylesheet to the widget AND every descendant. A
bare declaration string (``"border: 1px solid red;"``) or a type
selector (``"QFrame { border: ... }"``) therefore leaks onto children:
QLabel derives from QFrame, so a ``QFrame`` rule on a card draws a
border around every label inside it. That single mistake produced the
"border on every child" bugs across the drop zones, success cards, link
bar, banners, and the update dialog.

Every per-widget stylesheet in the app goes through :func:`apply_style`,
which scopes each rule to the widget's own objectName (``#name``). An
id selector matches exactly one widget, so nothing cascades. A
regression test (tests/test_stylesheet_scoping.py) walks every widget in
the app and fails on any stylesheet that is not scoped this way.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping

from PyQt6.QtWidgets import QWidget

_auto_names = itertools.count(1)

# Dynamic-property values accepted by :func:`set_tone`. Each has a matching
# ``QLabel[tone="..."]`` rule in app.styles.
TONES = ("success", "warning", "danger")


def scoped_name(widget: QWidget) -> str:
    """Return the widget's objectName, assigning a unique one if it is empty."""
    name = widget.objectName()
    if not name:
        name = f"{type(widget).__name__.lstrip('_')}_{next(_auto_names)}"
        widget.setObjectName(name)
    return name


def build_scoped_qss(name: str, declarations: str, states: Mapping[str, str] | None = None) -> str:
    """Build QSS where every rule is anchored to ``#name``.

    ``states`` maps a selector suffix to its own declarations, for example
    ``{":hover": "...", '[active="true"]': "...", " QHeaderView::section": "..."}``.
    A suffix that starts with a space is a descendant selector and targets
    children on purpose; everything else stays on the named widget.
    """
    rules = [f"#{name} {{ {declarations.strip()} }}"]
    for suffix, extra in (states or {}).items():
        rules.append(f"#{name}{suffix} {{ {extra.strip()} }}")
    return "\n".join(rules)


def apply_style(widget: QWidget, declarations: str, states: Mapping[str, str] | None = None) -> None:
    """Set a stylesheet on ``widget`` that applies to that widget only."""
    widget.setStyleSheet(build_scoped_qss(scoped_name(widget), declarations, states))


def make_transparent(widget: QWidget) -> None:
    """Stop a plain container widget painting the page background.

    The global `QWidget { background }` rule paints every container, which
    shows as a dark band when the container sits on a lighter surface such
    as a card or a dialog frame.
    """
    apply_style(widget, "background-color: transparent;")


def clear_style(widget: QWidget) -> None:
    """Remove any per-widget stylesheet, returning it to the global theme."""
    widget.setStyleSheet("")


def repolish(widget: QWidget) -> None:
    """Re-evaluate stylesheet rules after a dynamic property changed."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def set_tone(widget: QWidget, tone: str | None) -> None:
    """Set (or clear, with ``None``) the semantic ``tone`` property.

    Backed by the ``QLabel[tone="..."]`` rules in app.styles so status
    text changes color without any per-widget stylesheet.
    """
    if tone is not None and tone not in TONES:
        raise ValueError(f"Unknown tone: {tone!r}")
    widget.setProperty("tone", tone)
    repolish(widget)
