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
        unknown={},
        final={"NC": "<", "RF": "("},
    )
    widget = FlagReviewWidget(result)
    with qtbot.waitSignal(widget.mappings_confirmed, timeout=1000) as blocker:
        pass
    assert blocker.args[0] == {"NC": "<", "RF": "("}
