"""Tests for the shared component library built from design tokens."""
from __future__ import annotations

import sys

import pytest
from PyQt6.QtWidgets import QApplication, QLabel

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_primary_button_uses_accent_property():
    from app.widgets.components import PrimaryButton
    btn = PrimaryButton("Convert All")
    assert btn.text() == "Convert All"
    assert btn.property("accent") == "true"


def test_secondary_button_is_flat_styled():
    from app.widgets.components import SecondaryButton
    btn = SecondaryButton("Browse...")
    assert btn.text() == "Browse..."
    # NOTE: "flat" collides with QPushButton's own native bool Q_PROPERTY
    # (inherited from QAbstractButton), so Qt's meta-object system routes
    # setProperty("flat", "true") through the real bool property setter
    # instead of creating a dynamic string property (unlike "accent" on
    # PrimaryButton, which has no such collision and stores a literal
    # string). This is the correct and required behavior: app/styles.py
    # uses the QPushButton[flat="true"] QSS selector, which is Qt's
    # documented way to match against the native boolean "flat" property
    # (Qt stringifies bools for stylesheet selector comparison at the C++
    # level). So we assert the real boolean value here, not the string.
    assert btn.property("flat") is True


def test_card_is_a_styled_frame_with_layout():
    from app.widgets.components import Card
    card = Card()
    assert card.property("card") == "true"
    assert card.layout() is not None
    label = QLabel("hello")
    card.layout().addWidget(label)
    assert card.layout().count() == 1


def test_stat_card_shows_label_and_value():
    from app.widgets.components import StatCard
    stat = StatCard("Files loaded", "3")
    assert stat._value_label.text() == "3"
    assert stat._label_label.text() == "Files loaded"


def test_stat_card_set_value_updates_display():
    from app.widgets.components import StatCard
    stat = StatCard("Files loaded", "0")
    stat.set_value("5")
    assert stat._value_label.text() == "5"


def test_stat_card_accepts_color_override():
    from app.widgets.components import StatCard
    from app.design.tokens import Color
    stat = StatCard("Flags needing review", "2", value_color=Color.WARNING)
    assert Color.WARNING in stat._value_label.styleSheet()


def test_stat_card_set_value_accepts_optional_color():
    from app.widgets.components import StatCard
    from app.design.tokens import Color
    stat = StatCard("Flags needing review", "0")
    stat.set_value("5", color=Color.WARNING)
    assert stat._value_label.text() == "5"
    assert Color.WARNING in stat._value_label.styleSheet()


def test_stat_card_set_value_without_color_preserves_prior_color():
    from app.widgets.components import StatCard
    from app.design.tokens import Color
    stat = StatCard("Flags needing review", "0")
    stat.set_value("3", color=Color.WARNING)
    stat.set_value("5")
    assert stat._value_label.text() == "5"
    assert Color.WARNING in stat._value_label.styleSheet()


def test_stat_card_tooltip_sets_card_tooltip():
    from app.widgets.components import StatCard
    stat = StatCard("Files loaded", "3", tooltip="Total files loaded this session")
    assert stat.toolTip() == "Total files loaded this session"


def test_stat_card_without_tooltip_arg_has_no_tooltip():
    from app.widgets.components import StatCard
    stat = StatCard("Files loaded", "3")
    assert stat.toolTip() == ""


def test_status_badge_accepts_known_semantics():
    from app.widgets.components import StatusBadge
    for semantic in ("success", "warning", "danger"):
        badge = StatusBadge("Auto-mapped", semantic)
        assert badge.text() == "Auto-mapped"


def test_status_badge_rejects_unknown_semantic():
    from app.widgets.components import StatusBadge
    with pytest.raises(ValueError):
        StatusBadge("Bad", "not-a-real-semantic")


def test_status_badge_set_status_updates_text():
    from app.widgets.components import StatusBadge
    badge = StatusBadge("Needs mapping", "warning")
    badge.set_status("Auto-mapped", "success")
    assert badge.text() == "Auto-mapped"


def test_status_badge_tooltip_sets_label_tooltip():
    from app.widgets.components import StatusBadge
    badge = StatusBadge("Auto-mapped", "success", tooltip="Automatically mapped from source")
    assert badge.toolTip() == "Automatically mapped from source"


def test_status_badge_without_tooltip_arg_has_no_tooltip():
    from app.widgets.components import StatusBadge
    badge = StatusBadge("Auto-mapped", "success")
    assert badge.toolTip() == ""


def test_status_badge_set_status_updates_tooltip():
    from app.widgets.components import StatusBadge
    badge = StatusBadge("Needs mapping", "warning")
    badge.set_status("Auto-mapped", "success", tooltip="Now mapped")
    assert badge.toolTip() == "Now mapped"


def test_fixed_grid_table_requires_exactly_one_stretch_column():
    from app.widgets.components import FixedGridTable
    with pytest.raises(ValueError):
        FixedGridTable([{"label": "A", "width": 90}, {"label": "B", "width": 90}])
    with pytest.raises(ValueError):
        FixedGridTable([{"label": "A", "stretch": True}, {"label": "B", "stretch": True}])


def test_fixed_grid_table_header_and_row_share_column_count():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([
        {"label": "Code", "width": 90},
        {"label": "Description", "stretch": True},
        {"label": "Status", "width": 130},
    ])
    table.add_row([QLabel("NC"), QLabel("Not Clean"), QLabel("Auto-mapped")])
    table.add_row([QLabel("RF"), QLabel("Refractory"), QLabel("Auto-mapped")])
    # 1 header row + 2 data rows, 3 columns each = 9 grid items
    assert table._grid.count() == 9


def test_fixed_grid_table_fixed_columns_have_zero_stretch():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([
        {"label": "Code", "width": 90},
        {"label": "Description", "stretch": True},
    ])
    assert table._grid.columnStretch(0) == 0
    assert table._grid.columnStretch(1) == 1
    assert table._grid.columnMinimumWidth(0) == 90


def test_fixed_grid_table_clear_rows_keeps_header():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([{"label": "A", "width": 90}, {"label": "B", "stretch": True}])
    table.add_row([QLabel("1"), QLabel("2")])
    table.add_row([QLabel("3"), QLabel("4")])
    table.clear_rows()
    # Header row only = 2 columns
    assert table._grid.count() == 2


def test_fixed_grid_table_header_cell_sets_tooltip_when_provided():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([
        {"label": "Code", "width": 90, "tooltip": "The ATS flag code"},
        {"label": "Description", "stretch": True},
    ])
    header_item = table._grid.itemAtPosition(0, 0)
    assert header_item.widget().toolTip() == "The ATS flag code"


def test_fixed_grid_table_header_cell_has_no_tooltip_when_absent():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([
        {"label": "Code", "width": 90},
        {"label": "Description", "stretch": True},
    ])
    header_item = table._grid.itemAtPosition(0, 0)
    assert header_item.widget().toolTip() == ""


def test_fixed_grid_table_add_row_preserves_qlabel_subclass_styling():
    # Regression test: add_row() must not clobber a QLabel *subclass's*
    # own semantic styling (e.g. StatusBadge's color/pill CSS) - only
    # plain QLabel instances should receive the generic data-cell style.
    from app.widgets.components import FixedGridTable, StatusBadge

    table = FixedGridTable([
        {"label": "Code", "width": 90},
        {"label": "Status", "stretch": True},
    ])
    badge = StatusBadge("Auto-mapped", "success")
    badge_style_before = badge.styleSheet()
    plain_label = QLabel("NC")

    table.add_row([plain_label, badge])

    # StatusBadge's own styling must survive untouched.
    assert badge.styleSheet() == badge_style_before
    assert "border-radius" in badge.styleSheet()
    assert "border-top" not in badge.styleSheet()

    # Plain QLabel must still get the generic data-cell styling applied.
    assert "border-top" in plain_label.styleSheet()
    assert "padding" in plain_label.styleSheet()
