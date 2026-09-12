"""Tests for the frameless AppDialog / MessageDialog chrome."""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QFrame, QPushButton

from app.design.tokens import Color
from app.styles import build_stylesheet
from app.widgets.dialogs import DIALOG_FRAME_OBJECT_NAME, AppDialog, MessageDialog

_qapp = QApplication.instance() or QApplication(sys.argv)


def _dialog_frame(dialog: AppDialog) -> QFrame:
    frames = [f for f in dialog.findChildren(QFrame) if f.objectName() == DIALOG_FRAME_OBJECT_NAME]
    assert len(frames) == 1, "every AppDialog has exactly one bordered root frame"
    return frames[0]


def test_app_dialog_is_frameless_modal_with_bordered_frame():
    dialog = AppDialog(None, "Title")
    assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert dialog.isModal()
    assert dialog.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert _dialog_frame(dialog) is dialog.frame
    assert dialog.title_label.text() == "Title"


def test_global_stylesheet_borders_the_dialog_frame_with_dialog_border_token():
    qss = build_stylesheet("dark")
    start = qss.index("QFrame#DialogFrame")
    rule = qss[start:qss.index("}", start)]
    assert f"border: 1px solid {Color.DIALOG_BORDER}" in rule


def test_popups_and_tooltips_use_dialog_border():
    qss = build_stylesheet("dark")
    for selector in ("QToolTip", "QMenu", "QComboBox QAbstractItemView"):
        start = qss.index(selector)
        rule = qss[start:qss.index("}", start)]
        assert f"border: 1px solid {Color.DIALOG_BORDER}" in rule, selector


def test_add_button_puts_primary_last_and_right_aligned():
    dialog = AppDialog(None, "Title")
    cancel = dialog.add_button("Cancel")
    ok = dialog.add_button("OK", primary=True)
    # QPushButton has a real bool `flat` property, so Qt stores True here; the
    # `[flat="true"]` selector still matches its string form.
    assert cancel.property("flat") is True
    assert ok.property("accent") == "true"
    assert ok.isDefault()
    widgets = [dialog.button_row.itemAt(i).widget() for i in range(dialog.button_row.count())]
    assert widgets[0] is None  # leading stretch keeps the buttons right-aligned
    assert widgets[1:] == [cancel, ok]


def test_close_button_rejects():
    dialog = AppDialog(None, "Title")
    dialog.close_button.click()
    assert dialog.result() == QDialog.DialogCode.Rejected


def test_message_dialog_default_is_single_ok_button():
    dialog = MessageDialog(None, "Heads up", "Something <b>happened</b>")
    buttons = dialog.findChildren(QPushButton)
    labels = [b.text() for b in buttons if b is not dialog.close_button]
    assert labels == ["OK"]
    # Message text is shown verbatim - never interpreted as HTML.
    assert dialog.message_label.textFormat() == Qt.TextFormat.PlainText
    assert dialog.message_label.text() == "Something <b>happened</b>"


def test_message_dialog_tone_colors_title():
    dialog = MessageDialog(None, "Failed", "boom", tone="danger")
    assert dialog.title_label.property("tone") == "danger"


def test_question_buttons_map_to_accept_and_reject():
    dialog = MessageDialog(None, "Overwrite?", "files", [("Cancel", False), ("Overwrite", True)])
    buttons = {b.text(): b for b in dialog.findChildren(QPushButton)}
    buttons["Overwrite"].click()
    assert dialog.result() == QDialog.DialogCode.Accepted

    dialog = MessageDialog(None, "Overwrite?", "files", [("Cancel", False), ("Overwrite", True)])
    buttons = {b.text(): b for b in dialog.findChildren(QPushButton)}
    buttons["Cancel"].click()
    assert dialog.result() == QDialog.DialogCode.Rejected


def test_question_helper_returns_bool(monkeypatch):
    monkeypatch.setattr(MessageDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    assert MessageDialog.question(None, "t", "x") is True
    monkeypatch.setattr(MessageDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    assert MessageDialog.question(None, "t", "x") is False


def test_every_app_dialog_subclass_keeps_the_bordered_frame(tmp_path):
    from app.pages.email_page import EmailPage
    from app.project import ProjectConfig
    from app.updater import UpdateCheckResult
    from app.widgets import OnboardingDialog
    from app.widgets.update_dialog import UpdateDialog

    info = UpdateCheckResult(update_available=True, latest_version="9.9.9", current_version="1.0.0")
    page = EmailPage()
    recent, _list = page._build_recent_projects_dialog([(tmp_path / "a.json", ProjectConfig(title="A"))])
    for dialog in (OnboardingDialog(), UpdateDialog(info), recent, MessageDialog(None, "t", "x")):
        assert isinstance(dialog, AppDialog)
        _dialog_frame(dialog)
