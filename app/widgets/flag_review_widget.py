"""Flag review widget for confirming ATS -> Standard Format code mappings."""
from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.converters.flag_mapper import FlagMappingResult, STANDARD_SYMBOL_DESCRIPTIONS
from app.styles import color

HEADING_TEXT = "Flag Review"
SUBTEXT_ALL_KNOWN = "All flag codes were auto-mapped. No review needed."
SUBTEXT_UNKNOWN = (
    "Some flag codes in these files are not in the auto-map list. "
    "Enter a Standard Format code for each, or check 'Leave as-is' to pass it through unchanged."
)
SUBTEXT_SUGGESTED = (
    "Some flag codes were matched by description. Review the suggested mappings below "
    "and confirm or change them before converting."
)
CONFIRM_TEXT = "Confirm Mappings"
AUTO_MAPPED_LABEL = "Auto-mapped"
NEEDS_MAPPING_LABEL = "Needs mapping"
SUGGESTED_MATCH_LABEL = "Suggested match"
SUGGESTED_MATCH_COLOR = "#4da6ff"
LEAVE_AS_IS_TEXT = "Leave as-is"
COMBO_SEPARATOR = "  -  "
COMBO_MIN_WIDTH = 220


def _symbol_from_display(text: str) -> str:
    """Extract the symbol character from a combo display string.

    Display strings look like '*  -  Scaffold was interfering'.
    If the text has no separator, return it stripped (bare character typed by user).
    """
    if COMBO_SEPARATOR in text:
        return text.split(COMBO_SEPARATOR, 1)[0].strip()
    return text.strip()


def _make_combo() -> QComboBox:
    """Build a searchable combo box populated with all standard symbols."""
    combo = QComboBox()
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.setMinimumWidth(COMBO_MIN_WIDTH)

    for symbol, description in STANDARD_SYMBOL_DESCRIPTIONS.items():
        combo.addItem(f"{symbol}{COMBO_SEPARATOR}{description}")

    completer = combo.completer()
    if completer is not None:
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    combo.setCurrentIndex(-1)
    return combo


class FlagReviewWidget(QWidget):
    """Shows flag mappings for user review. Emits mappings_confirmed when done."""

    mappings_confirmed = pyqtSignal(dict)

    def __init__(
        self,
        mapping_result: FlagMappingResult,
        ats_flags: dict[str, str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._mapping_result = mapping_result
        self._ats_flags: dict[str, str] = ats_flags if ats_flags is not None else {}
        self._code_inputs: dict[str, QComboBox] = {}
        self._leave_checks: dict[str, QCheckBox] = {}
        self._build_ui()

        if not mapping_result.unknown and not mapping_result.suggested:
            QTimer.singleShot(0, lambda: self.mappings_confirmed.emit(dict(mapping_result.final)))

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        heading = QLabel(HEADING_TEXT)
        heading.setProperty("role", "heading")
        outer.addWidget(heading)

        if not self._mapping_result.unknown and not self._mapping_result.suggested:
            info = QLabel(SUBTEXT_ALL_KNOWN)
            info.setStyleSheet(f"color: {color('success')}; font-size: 9pt;")
            outer.addWidget(info)
            return

        subtext_str = SUBTEXT_UNKNOWN if self._mapping_result.unknown else SUBTEXT_SUGGESTED
        subtext = QLabel(subtext_str)
        subtext.setWordWrap(True)
        subtext.setProperty("role", "muted")
        outer.addWidget(subtext)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)
        outer.addWidget(scroll)

        # Column headers
        header = QHBoxLayout()
        for label, stretch in [
            ("ATS Code", 1),
            ("ATS Description", 3),
            ("Standard Symbol", 3),
            ("Status", 2),
            ("", 1),
        ]:
            lbl = QLabel(f"<b>{label}</b>")
            header.addWidget(lbl, stretch)
        scroll_layout.addLayout(header)

        # Known flags (read-only display)
        for ats_code, std_code in self._mapping_result.known.items():
            description = self._mapping_result.unknown.get(ats_code, ats_code)
            row = QHBoxLayout()
            row.addWidget(QLabel(ats_code), 1)
            row.addWidget(QLabel(description), 3)
            code_lbl = QLabel(std_code)
            code_lbl.setStyleSheet(f"color: {color('success')};")
            row.addWidget(code_lbl, 3)
            status = QLabel(AUTO_MAPPED_LABEL)
            status.setStyleSheet(f"color: {color('success')}; font-size: 9pt;")
            row.addWidget(status, 2)
            row.addWidget(QLabel(""), 1)
            scroll_layout.addLayout(row)

        # Suggested flags (editable combo, pre-filled, no Leave as-is)
        for ats_code, std_symbol in self._mapping_result.suggested.items():
            description = self._ats_flags.get(ats_code, ats_code)
            row = QHBoxLayout()
            row.addWidget(QLabel(ats_code), 1)
            row.addWidget(QLabel(description), 3)

            combo = _make_combo()
            display_text = (
                f"{std_symbol}{COMBO_SEPARATOR}"
                f"{STANDARD_SYMBOL_DESCRIPTIONS.get(std_symbol, std_symbol)}"
            )
            combo.setCurrentText(display_text)
            combo.currentTextChanged.connect(self._on_input_changed)
            self._code_inputs[ats_code] = combo
            row.addWidget(combo, 3)

            status_lbl = QLabel(SUGGESTED_MATCH_LABEL)
            status_lbl.setStyleSheet(f"color: {SUGGESTED_MATCH_COLOR}; font-size: 9pt;")
            row.addWidget(status_lbl, 2)

            row.addWidget(QLabel(""), 1)
            scroll_layout.addLayout(row)

        # Unknown flags (editable combo, no pre-fill)
        for ats_code, description in self._mapping_result.unknown.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(ats_code), 1)
            row.addWidget(QLabel(description), 3)

            combo = _make_combo()
            combo.currentTextChanged.connect(self._on_input_changed)
            self._code_inputs[ats_code] = combo
            row.addWidget(combo, 3)

            status_lbl = QLabel(NEEDS_MAPPING_LABEL)
            status_lbl.setStyleSheet(f"color: {color('warning')}; font-size: 9pt;")
            row.addWidget(status_lbl, 2)

            leave_check = QCheckBox(LEAVE_AS_IS_TEXT)
            leave_check.stateChanged.connect(
                lambda state, code=ats_code, inp=combo, lbl=status_lbl:
                    self._on_leave_toggled(code, inp, lbl, state)
            )
            self._leave_checks[ats_code] = leave_check
            row.addWidget(leave_check, 1)

            scroll_layout.addLayout(row)

        scroll_layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._confirm_btn = QPushButton(CONFIRM_TEXT)
        self._confirm_btn.setProperty("accent", "true")
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self._confirm_btn)
        outer.addLayout(btn_row)

        self._update_confirm_button()

    def _on_leave_toggled(
        self, code: str, inp: QComboBox, status_lbl: QLabel, state: int
    ) -> None:
        checked = state == Qt.CheckState.Checked.value
        inp.setEnabled(not checked)
        if checked:
            status_lbl.setText("Leave as-is")
            status_lbl.setStyleSheet(f"color: {color('muted_text')}; font-size: 9pt;")
        else:
            status_lbl.setText(NEEDS_MAPPING_LABEL)
            status_lbl.setStyleSheet(f"color: {color('warning')}; font-size: 9pt;")
        self._update_confirm_button()

    def _on_input_changed(self) -> None:
        self._update_confirm_button()

    def _update_confirm_button(self) -> None:
        all_resolved = True
        # Suggested combos must have non-empty text (pre-filled but user can clear)
        for ats_code in self._mapping_result.suggested:
            combo = self._code_inputs.get(ats_code)
            if combo and not combo.currentText().strip():
                all_resolved = False
                break
        if all_resolved:
            # Unknown combos must be filled or have Leave as-is checked
            for ats_code in self._mapping_result.unknown:
                leave = self._leave_checks.get(ats_code)
                combo = self._code_inputs.get(ats_code)
                if leave and leave.isChecked():
                    continue
                if combo and not combo.currentText().strip():
                    all_resolved = False
                    break
        self._confirm_btn.setEnabled(all_resolved)

    def _on_confirm(self) -> None:
        final = dict(self._mapping_result.known)
        # Add suggested (may be user-overridden via the pre-filled combo)
        for ats_code in self._mapping_result.suggested:
            combo = self._code_inputs.get(ats_code)
            if combo:
                text = combo.currentText().strip()
                symbol = (
                    _symbol_from_display(text) if text
                    else self._mapping_result.suggested[ats_code]
                )
                final[ats_code] = symbol
        # Add unknown (user-selected or leave as-is)
        for ats_code in self._mapping_result.unknown:
            leave = self._leave_checks.get(ats_code)
            combo = self._code_inputs.get(ats_code)
            if leave and leave.isChecked():
                final[ats_code] = ats_code
            elif combo:
                text = combo.currentText().strip()
                final[ats_code] = _symbol_from_display(text)
        self.mappings_confirmed.emit(final)
