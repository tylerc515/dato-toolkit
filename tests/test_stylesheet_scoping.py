"""Regression guard for the "border on every child" bug class.

A per-widget stylesheet applies to the widget and every descendant. A bare
declaration (`"border: ..."`) or a type selector (`QFrame { ... }`) on a
container therefore leaks onto children - QLabel derives from QFrame, so a
`QFrame` border rule on a card draws a border around every label in it.

These tests walk every widget the app builds (main window, every page,
every dialog, and the state-dependent cards) and fail on any stylesheet
that could cascade: bare declarations, or a selector that also matches
one of the widget's own descendants.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from app.design.qss import apply_style, build_scoped_qss, scoped_name

_qapp = QApplication.instance() or QApplication(sys.argv)

APP_DIR = Path(__file__).resolve().parent.parent / "app"
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_SIMPLE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)?(#[A-Za-z0-9_\-]+)?(.*)$")


def _rules(qss: str) -> list[tuple[str, str]]:
    return [(sel.strip(), body.strip()) for sel, body in _RULE_RE.findall(qss)]


def _leaked_text(qss: str) -> str:
    """Anything in the sheet that is not inside a `selector { ... }` rule."""
    return _RULE_RE.sub("", qss).strip()


def _offending_selectors(widget: QWidget) -> list[str]:
    """Selectors on this widget's stylesheet that also match a descendant."""
    problems: list[str] = []
    descendants = widget.findChildren(QWidget)
    for selector, _body in _rules(widget.styleSheet()):
        for part in selector.split(","):
            part = part.strip()
            if " " in part or ">" in part:
                # Descendant / child combinator: targeting children on purpose.
                continue
            match = _SIMPLE_RE.match(part)
            assert match is not None
            type_name, id_name, _rest = match.groups()
            if id_name:
                name = id_name[1:]
                if any(d.objectName() == name for d in descendants):
                    problems.append(part)
            elif type_name:
                if any(d.inherits(type_name) for d in descendants):
                    problems.append(part)
            else:
                # Pure attribute / pseudo selector such as `[card="true"]` -
                # matches any descendant with that property, so flag it.
                problems.append(part)
    return problems


def _check_widget_tree(root: QWidget) -> list[str]:
    failures: list[str] = []
    for widget in [root, *root.findChildren(QWidget)]:
        qss = widget.styleSheet()
        if not qss.strip():
            continue
        label = f"{type(widget).__name__}#{widget.objectName() or '<unnamed>'}"
        if "{" not in qss:
            failures.append(f"{label}: bare declarations with no selector: {qss!r}")
            continue
        leaked = _leaked_text(qss)
        if leaked:
            failures.append(f"{label}: text outside any rule: {leaked!r}")
        for selector in _offending_selectors(widget):
            failures.append(f"{label}: selector {selector!r} also matches a descendant")
    return failures


# --- Widget factories -------------------------------------------------------

def _main_window() -> QWidget:
    from app.window import MainWindow

    window = MainWindow()
    window.resize(1100, 720)
    return window


def _stateful_widgets(tmp_path: Path) -> list[QWidget]:
    """Widgets whose styled state only exists after data is loaded."""
    from app.pages.batch_page import _ErrorCard as BatchErrorCard
    from app.pages.converter_page import _ErrorCard as ConverterErrorCard
    from app.pages.import_page import ImportResult, _FileCard
    from app.widgets import OnboardingDialog, StepIndicator

    widgets: list[QWidget] = [
        BatchErrorCard(str(tmp_path / "bad.csv"), "could not parse"),
        ConverterErrorCard(str(tmp_path / "bad.xlsx"), "could not parse"),
        _FileCard(ImportResult(path=str(tmp_path / "bad.csv"), error="could not parse")),
        OnboardingDialog(),
    ]
    stepper = StepIndicator(["One", "Two", "Three"])
    stepper.set_current_step(1, completed={0})
    widgets.append(stepper)
    return widgets


def _dialogs() -> list[QWidget]:
    from app.updater import UpdateCheckResult
    from app.widgets.update_dialog import UpdateDialog

    info = UpdateCheckResult(
        update_available=True, latest_version="9.9.9", current_version="1.0.0",
        release_notes="- a note", download_url="https://example.invalid/x.exe",
        published_at="2026-01-01T00:00:00Z",
    )
    return [UpdateDialog(info)]


# --- Tests -------------------------------------------------------------------

def test_no_widget_stylesheet_can_cascade_to_children(tmp_path):
    roots = [_main_window(), *_stateful_widgets(tmp_path), *_dialogs()]
    failures: list[str] = []
    for root in roots:
        failures.extend(_check_widget_tree(root))
    assert failures == [], "\n".join(failures)


def test_no_direct_set_stylesheet_calls_outside_helper():
    """Every per-widget stylesheet must go through app.design.qss.apply_style."""
    offenders = []
    for py in APP_DIR.rglob("*.py"):
        if py.name == "qss.py":
            continue
        if re.search(r"\.setStyleSheet\(", py.read_text(encoding="utf-8")):
            offenders.append(str(py.relative_to(APP_DIR)))
    assert offenders == [], f"Direct setStyleSheet calls (use apply_style): {offenders}"


def test_build_scoped_qss_anchors_every_rule_to_the_id():
    qss = build_scoped_qss(
        "box", "border: 1px solid red;", {":hover": "color: blue;", " QLabel": "padding: 1px;"}
    )
    selectors = [sel for sel, _ in _rules(qss)]
    assert selectors == ["#box", "#box:hover", "#box QLabel"]


def test_apply_style_assigns_unique_object_names():
    first, second = QWidget(), QWidget()
    apply_style(first, "color: red;")
    apply_style(second, "color: red;")
    assert first.objectName() and second.objectName()
    assert first.objectName() != second.objectName()
    assert first.styleSheet().startswith(f"#{first.objectName()} ")


def test_scoped_name_keeps_an_existing_object_name():
    widget = QWidget()
    widget.setObjectName("Keep")
    assert scoped_name(widget) == "Keep"


@pytest.mark.parametrize("bad", ["border: 1px solid red;", "QFrame { border: 1px solid red; }"])
def test_checker_catches_the_original_bug_shapes(bad):
    """The checker itself must flag the two patterns that caused the bug."""
    from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout

    frame = QFrame()
    QVBoxLayout(frame).addWidget(QLabel("child"))
    frame.setStyleSheet(bad)
    assert _check_widget_tree(frame)
