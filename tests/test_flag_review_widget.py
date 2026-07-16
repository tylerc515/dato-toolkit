"""Tests for FlagReviewWidget.

Uses module-level QApplication to prevent GC crash on Windows (same pattern
as test_footer.py).
"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_widget_instantiates_with_all_known():
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={"NC": "<"},
        suggested={},
        unknown={},
        final={"NC": "<"},
    )
    widget = FlagReviewWidget(result)
    assert widget is not None


def test_widget_instantiates_with_unknowns():
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={"NC": "<"},
        suggested={},
        unknown={"XX": "MYSTERY FLAG"},
        final={"NC": "<"},
    )
    widget = FlagReviewWidget(result)
    assert widget is not None


def test_all_known_emits_confirmed_signal(qtbot):
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={"NC": "<", "RF": "("},
        suggested={},
        unknown={},
        final={"NC": "<", "RF": "("},
    )
    widget = FlagReviewWidget(result)
    with qtbot.waitSignal(widget.mappings_confirmed, timeout=1000) as blocker:
        pass
    assert blocker.args[0] == {"NC": "<", "RF": "("}


def test_suggested_flags_emit_confirmed_after_confirm_click(qtbot):
    """Suggested-match flags appear pre-filled; confirm emits them in final mapping."""
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={},
        suggested={"SI": ";"},
        unknown={},
        final={},
    )
    widget = FlagReviewWidget(result)
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.mappings_confirmed, timeout=1000) as blocker:
        widget._on_confirm()
    assert blocker.args[0]["SI"] == ";"


def test_all_known_and_no_suggested_auto_emits(qtbot):
    """When known is populated and suggested+unknown are empty, auto-emits immediately."""
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={"NC": "<"},
        suggested={},
        unknown={},
        final={"NC": "<"},
    )
    widget = FlagReviewWidget(result)
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.mappings_confirmed, timeout=1000) as blocker:
        pass
    assert blocker.args[0] == {"NC": "<"}


def test_combo_confirm_emits_symbol_not_display_string(qtbot):
    """Selecting a combo item and confirming emits just the symbol, not the full display string."""
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget, COMBO_SEPARATOR
    result = FlagMappingResult(
        known={},
        suggested={},
        unknown={"XX": "MYSTERY FLAG"},
        final={},
    )
    widget = FlagReviewWidget(result)
    qtbot.addWidget(widget)

    combo = widget._code_inputs["XX"]
    assert combo.count() > 0, "Combo box should have items from STANDARD_SYMBOL_DESCRIPTIONS"
    combo.setCurrentIndex(0)

    with qtbot.waitSignal(widget.mappings_confirmed, timeout=1000) as blocker:
        widget._on_confirm()

    emitted = blocker.args[0]["XX"]
    assert COMBO_SEPARATOR not in emitted, (
        f"Emitted value should be a symbol only, not a display string. Got: {emitted!r}"
    )


def test_suggested_preselects_correct_symbol(qtbot):
    """Suggested match pre-selects the correct item in the combo box."""
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget, COMBO_SEPARATOR, _symbol_from_display
    result = FlagMappingResult(
        known={},
        suggested={"SI": ";"},
        unknown={},
        final={},
    )
    widget = FlagReviewWidget(result)
    qtbot.addWidget(widget)

    combo = widget._code_inputs["SI"]
    current_text = combo.currentText()
    symbol = _symbol_from_display(current_text)
    assert symbol == ";", (
        f"Expected pre-selected symbol ';', got symbol {symbol!r} from text {current_text!r}"
    )


def test_combo_field_width_is_constrained(qtbot):
    """The closed combo field has a fixed max width, not unbounded stretch."""
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget, COMBO_MAX_WIDTH
    result = FlagMappingResult(
        known={},
        suggested={},
        unknown={"XX": "MYSTERY FLAG"},
        final={},
    )
    widget = FlagReviewWidget(result)
    qtbot.addWidget(widget)

    combo = widget._code_inputs["XX"]
    assert combo.maximumWidth() == COMBO_MAX_WIDTH


def test_combo_popup_stays_wide_enough_for_long_descriptions(qtbot):
    """The dropdown popup view is not constrained by the narrower closed field."""
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget, COMBO_MAX_WIDTH, COMBO_POPUP_MIN_WIDTH
    result = FlagMappingResult(
        known={},
        suggested={},
        unknown={"XX": "MYSTERY FLAG"},
        final={},
    )
    widget = FlagReviewWidget(result)
    qtbot.addWidget(widget)

    combo = widget._code_inputs["XX"]
    assert combo.view().minimumWidth() >= COMBO_POPUP_MIN_WIDTH
    assert combo.view().minimumWidth() > COMBO_MAX_WIDTH


def test_leave_as_is_disables_combo(qtbot):
    """Checking 'Leave as-is' disables the combo box; unchecking re-enables it."""
    from app.converters.flag_mapper import FlagMappingResult
    from app.widgets.flag_review_widget import FlagReviewWidget
    result = FlagMappingResult(
        known={},
        suggested={},
        unknown={"XX": "MYSTERY FLAG"},
        final={},
    )
    widget = FlagReviewWidget(result)
    qtbot.addWidget(widget)

    combo = widget._code_inputs["XX"]
    leave_check = widget._leave_checks["XX"]

    assert combo.isEnabled(), "Combo should start enabled"
    leave_check.setChecked(True)
    assert not combo.isEnabled(), "Combo should be disabled when Leave as-is is checked"
    leave_check.setChecked(False)
    assert combo.isEnabled(), "Combo should re-enable when Leave as-is is unchecked"
