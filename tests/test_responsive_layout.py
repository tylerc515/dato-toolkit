"""Responsive layout guards: the window never shrinks below its minimum, and
no page compresses or clips its content at that minimum.
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_window():
    from app.window import MainWindow

    with patch("app.window.QSettings") as MockSettings, \
            patch.object(MainWindow, "_maybe_show_onboarding"), \
            patch.object(MainWindow, "_run_update_check"):
        MockSettings.return_value.value.return_value = None
        window = MainWindow()
    window.resize(1200, 800)
    window.show()
    _qapp.processEvents()
    return window


def _dispose(window) -> None:
    window.close()
    window.deleteLater()
    _qapp.processEvents()


# --- Minimum size enforcement --------------------------------------------------

@pytest.mark.parametrize("direction", ["bottom-right", "top-left", "right", "bottom"])
def test_frameless_resize_drag_clamps_exactly_at_minimum_size(direction):
    """The custom edge-drag resize path must stop at minimumSize(), not near it."""
    window = _make_window()
    try:
        window._resize_direction = direction
        window._resize_start_geometry = QRect(window.geometry())
        window._resize_start_pos = QPoint(0, 0)
        # Drag far past the minimum in the shrinking direction for every edge.
        dx = 2000 if "left" in direction else -2000
        dy = 2000 if "top" in direction else -2000
        window._perform_resize(QPoint(dx, dy))
        _qapp.processEvents()
        if "left" in direction or "right" in direction:
            assert window.width() == window.minimumWidth()
        if "top" in direction or "bottom" in direction:
            assert window.height() == window.minimumHeight()
    finally:
        window._resize_direction = None
        _dispose(window)


# --- Page geometry at the minimum window size ---------------------------------

def _long_projects():
    from pathlib import Path

    from app.project import ProjectConfig

    return [
        (
            Path(f"C:/projects/p{i}.json"),
            ProjectConfig(
                title=f"EXAMPLE PAPER RB{i} - 2026 OUTAGE NDE TRACKSHEET WITH A LONG TITLE",
                customer="Example Paper", location="Anytown", equipment=f"Recovery Boiler {i}",
                date="2026-09-01", last_modified="2026-09-01T10:00:00",
            ),
        )
        for i in range(5)
    ]


def _long_history():
    from app.history import HistoryEntry

    return [
        HistoryEntry(
            title=f"EXAMPLE PAPER RB{i} - 2026 OUTAGE NDE TRACKSHEET WITH A LONG TITLE",
            customer="Example Paper", location="Anytown", equipment=f"Recovery Boiler {i}",
            date="2026-09-01", elevation_count=12, output_path=f"C:/out/tracker{i}.xlsx",
            generated_at="2026-09-01T10:00:00", entry_type="update_email" if i % 2 else "tracker",
        )
        for i in range(6)
    ]


def _has_ancestor(widget, predicate) -> bool:
    parent = widget.parentWidget()
    while parent is not None:
        if predicate(parent):
            return True
        parent = parent.parentWidget()
    return False


def _describe(widget) -> str:
    from PyQt6.QtWidgets import QAbstractButton, QLabel

    text = ""
    if isinstance(widget, (QLabel, QAbstractButton)):
        text = f" {widget.text()[:32]!r}"
    return f"{type(widget).__name__}#{widget.objectName() or '-'}{text}"


def find_layout_problems(root) -> list[str]:
    """Every visible widget under root that is squeezed below its own minimum
    or laid out beyond its parent's rect (outside of a scrolling region)."""
    from PyQt6.QtWidgets import QAbstractScrollArea, QHeaderView, QScrollArea, QWidget

    def collapsed(candidate) -> bool:
        # Help panels and update banners animate to zero width/height on purpose.
        return candidate.maximumWidth() == 0 or candidate.maximumHeight() == 0

    problems: list[str] = []
    for widget in root.findChildren(QWidget):
        if not widget.isVisible() or widget.width() == 0 and widget.height() == 0:
            continue
        # Qt's own internals (scrollbar containers, header views) size themselves.
        if widget.objectName().startswith("qt_") or isinstance(widget, QHeaderView):
            continue
        if collapsed(widget) or _has_ancestor(widget, collapsed):
            continue
        min_hint = widget.minimumSizeHint()
        layout = widget.layout()
        if layout is not None and layout.hasHeightForWidth():
            # A container's heightForWidth is its *preferred* height; the
            # layout knows the minimum it needs at this width.
            needed_height = layout.minimumHeightForWidth(widget.width())
        elif widget.hasHeightForWidth():
            # A word-wrapped label needs this much height at its current width.
            needed_height = widget.heightForWidth(widget.width())
        else:
            needed_height = min_hint.height()
        needed_height = min(needed_height, widget.maximumHeight())
        needed_width = min(min_hint.width(), widget.maximumWidth())
        if widget.width() < needed_width or widget.height() < needed_height:
            problems.append(
                f"compressed: {_describe(widget)} is {widget.width()}x{widget.height()}, "
                f"needs {needed_width}x{needed_height}"
            )
        parent = widget.parentWidget()
        inside_scroll = _has_ancestor(widget, lambda w: isinstance(w, QAbstractScrollArea))
        if parent is not None and not inside_scroll and not parent.rect().contains(widget.geometry()):
            problems.append(
                f"clipped: {_describe(widget)} at {widget.geometry().getRect()} "
                f"exceeds parent {_describe(parent)} {parent.rect().getRect()}"
            )
        if isinstance(widget, QAbstractScrollArea) and not widget.property("allowsHorizontalScroll"):
            # Sideways overflow is never acceptable: neither a horizontal
            # scrollbar nor content silently cut off past the right edge.
            # (The tracker preview opts out: it is an Excel sheet at real widths.)
            if widget.horizontalScrollBar().isVisible():
                problems.append(f"horizontal scrollbar: {_describe(widget)}")
            content = widget.widget() if isinstance(widget, QScrollArea) else None
            if content is not None and content.width() > widget.viewport().width():
                problems.append(
                    f"overflow: {_describe(widget)} content is {content.width()}px wide "
                    f"in a {widget.viewport().width()}px viewport"
                )
    return problems


def _fixture_csvs() -> list[str]:
    from pathlib import Path

    return [str(p) for p in sorted((Path(__file__).parent / "fixtures").glob("*.csv"))[:2]]


def _show_dashboard(window):
    window._go_to_dashboard()


def _show_import(window):
    window._go_to_step(0)
    window.import_page.add_files(_fixture_csvs())


def _show_reorder(window):
    _show_import(window)
    window.import_page._emit_files_ready()


def _show_generate(window):
    _show_reorder(window)
    window._go_to_step(2)


def _show_generate_success(window):
    _show_generate(window)
    window.generate_page.success_card.setVisible(True)


def _show_email(window):
    window._go_to_email()


def _show_converter_ats(window):
    window._go_to_converter()
    window.converter_page._show_ats_tab()


def _show_converter_team(window):
    window._go_to_converter()
    window.converter_page._show_team_tab()


def _show_converter_tds(window):
    window._go_to_converter()
    window.converter_page._show_tds_tab()


def _show_history(window):
    window._go_to_history()


def _show_settings(window):
    window._go_to_settings()


def _show_batch(window):
    window._go_to_batch()


def _show_projects(window):
    window._go_to_projects()


PAGE_STATES = {
    "dashboard": _show_dashboard,
    "import": _show_import,
    "reorder": _show_reorder,
    "generate": _show_generate,
    "generate_success": _show_generate_success,
    "email": _show_email,
    "converter_ats": _show_converter_ats,
    "converter_team": _show_converter_team,
    "converter_tds": _show_converter_tds,
    "history": _show_history,
    "settings": _show_settings,
    "batch": _show_batch,
    "projects": _show_projects,
}


def settle() -> None:
    for _ in range(4):
        _qapp.processEvents()


@pytest.fixture
def window_with_data():
    from app.styles import build_stylesheet
    from app.widgets.dialogs import MessageDialog

    # Real font sizes come from the app stylesheet; without it every label
    # measures smaller than it does in the shipped app.
    previous_stylesheet = _qapp.styleSheet()
    _qapp.setStyleSheet(build_stylesheet("dark"))
    # Never block on a modal (e.g. "saved project found?" after importing files).
    with patch("app.pages.dashboard_page.list_projects", _long_projects), \
            patch("app.pages.dashboard_page.load_history", _long_history), \
            patch("app.pages.projects_page.list_projects", _long_projects), \
            patch("app.pages.history_page.load_history", _long_history), \
            patch.object(MessageDialog, "question", return_value=False), \
            patch.object(MessageDialog, "warning", return_value=None), \
            patch.object(MessageDialog, "critical", return_value=None):
        window = _make_window()
        try:
            yield window
        finally:
            _dispose(window)
            _qapp.setStyleSheet(previous_stylesheet)


@pytest.mark.parametrize("state", list(PAGE_STATES))
def test_no_page_compresses_or_clips_at_the_minimum_window_size(window_with_data, state):
    from app.window import WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH

    window = window_with_data
    PAGE_STATES[state](window)
    settle()
    window.resize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
    settle()
    assert window.size().width() == WINDOW_MIN_WIDTH and window.size().height() == WINDOW_MIN_HEIGHT
    # Whole window: the sidebar, breadcrumb, footer, and status bar must
    # survive a page's demands too, not just the page itself.
    problems = find_layout_problems(window)
    assert problems == [], "\n".join(problems)


# --- Responsive containers -----------------------------------------------------

def _buttons(n: int, width: int = 120):
    from PyQt6.QtWidgets import QPushButton

    buttons = []
    for i in range(n):
        button = QPushButton(f"Button {i}")
        button.setFixedSize(width, 30)
        buttons.append(button)
    return buttons


def test_flow_layout_keeps_one_line_when_everything_fits():
    from PyQt6.QtWidgets import QWidget

    from app.widgets.components import FlowLayout

    host = QWidget()
    flow = FlowLayout(host, h_spacing=10, v_spacing=10)
    flow.setContentsMargins(0, 0, 0, 0)
    buttons = _buttons(3)
    for button in buttons:
        flow.addWidget(button)
    host.resize(500, 100)
    host.show()
    settle()
    assert {b.y() for b in buttons} == {0}
    assert [b.x() for b in buttons] == [0, 130, 260]
    assert flow.heightForWidth(500) == 30


def test_flow_layout_wraps_items_when_the_width_is_constrained():
    from PyQt6.QtWidgets import QWidget

    from app.widgets.components import FlowLayout

    host = QWidget()
    flow = FlowLayout(host, h_spacing=10, v_spacing=10)
    flow.setContentsMargins(0, 0, 0, 0)
    buttons = _buttons(4)
    for button in buttons:
        flow.addWidget(button)
    host.resize(270, 200)  # room for two 120px buttons plus one gap
    host.show()
    settle()
    assert [(b.x(), b.y()) for b in buttons] == [(0, 0), (130, 0), (0, 40), (130, 40)]
    assert flow.heightForWidth(270) == 70
    assert flow.minimumSize().width() == 120  # never narrower than the widest item


def test_flow_layout_right_aligned_lines_end_at_the_right_edge():
    from PyQt6.QtWidgets import QWidget

    from app.widgets.components import FlowLayout

    host = QWidget()
    flow = FlowLayout(host, h_spacing=10, v_spacing=10, align_right=True)
    flow.setContentsMargins(0, 0, 0, 0)
    buttons = _buttons(3)
    for button in buttons:
        flow.addWidget(button)
    host.resize(300, 200)  # two per line
    host.show()
    settle()
    assert (buttons[1].x() + buttons[1].width()) == 300
    assert (buttons[2].x() + buttons[2].width()) == 300
    assert buttons[2].y() == 40


def test_flow_layout_equal_widths_balances_items_into_a_grid():
    """4 cards -> 4 across when they fit, 2x2 when only three fit, 1 column when one fits."""
    from PyQt6.QtWidgets import QLabel, QWidget

    from app.widgets.components import FlowLayout

    host = QWidget()
    flow = FlowLayout(host, h_spacing=10, v_spacing=10, equal_widths=True)
    flow.setContentsMargins(0, 0, 0, 0)
    cards = []
    for i in range(4):
        card = QLabel(f"C{i}")
        card.setMinimumWidth(100)
        cards.append(card)
        flow.addWidget(card)
    host.show()

    host.resize(430, 200)  # 4 x 100 + 3 x 10
    settle()
    assert {c.y() for c in cards} == {0}
    assert len({c.width() for c in cards}) == 1

    host.resize(340, 200)  # only three 100px cards fit -> balanced 2x2
    settle()
    assert [c.y() for c in cards][:2] == [0, 0] and cards[2].y() == cards[3].y() > 0
    assert cards[0].width() == cards[1].width() == 165

    host.resize(150, 400)  # one per line, full width
    settle()
    assert [c.x() for c in cards] == [0, 0, 0, 0]
    assert all(c.width() == 150 for c in cards)


def test_responsive_columns_stack_below_the_threshold():
    from PyQt6.QtWidgets import QLabel

    from app.widgets.components import ResponsiveColumns

    columns = ResponsiveColumns(stack_below=600, spacing=10)
    left, right = QLabel("left"), QLabel("right")
    columns.add_column(left)
    columns.add_column(right)
    columns.show()

    columns.resize(800, 100)
    settle()
    assert not columns.stacked
    assert left.y() == right.y() and right.x() > left.x()

    columns.resize(500, 300)
    settle()
    assert columns.stacked
    assert left.x() == right.x() and right.y() > left.y()

    columns.resize(700, 100)
    settle()
    assert not columns.stacked


def test_page_scroll_area_scrolls_vertically_only():
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QLabel

    from app.widgets.components import PageScrollArea

    content = QLabel("content")
    scroll = PageScrollArea(content)
    assert scroll.widget() is content
    assert scroll.widgetResizable()
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
