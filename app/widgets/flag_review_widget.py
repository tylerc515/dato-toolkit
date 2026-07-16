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
from app.design.tokens import Color, FontSize
from app.widgets.components import FixedGridTable, StatusBadge

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
LEAVE_AS_IS_TEXT = "Leave as-is"
COMBO_SEPARATOR = "  -  "
COMBO_MIN_WIDTH = 220
COMBO_MAX_WIDTH = 230
# Widened from 400 to 440: at the larger FontSize.BODY (15px) the longest
# symbol description renders ~401px wide, which the old 400px popup would
# clip once the vertical scrollbar and item padding are accounted for.
COMBO_POPUP_MIN_WIDTH = 440

# StatusBadge only supports "success" / "warning" / "danger" semantics
# (see app/widgets/components.py::_SEMANTIC_COLORS). Map every status this
# widget can show onto one of those three:
#   - Auto-mapped   -> success  (fully resolved, no action needed)
#   - Suggested     -> warning  (needs user confirmation before it's final;
#                                 there is no "info"/blue semantic available,
#                                 so this is the closest of the three)
#   - Needs mapping -> warning  (action required)
#   - Leave as-is   -> success  (once checked, the row is settled/resolved,
#                                 same as auto-mapped - just resolved by the
#                                 user instead of the auto-mapper)
_STATUS_SEMANTIC_AUTO_MAPPED = "success"
_STATUS_SEMANTIC_SUGGESTED = "warning"
_STATUS_SEMANTIC_NEEDS_MAPPING = "warning"
_STATUS_SEMANTIC_LEAVE_AS_IS = "success"

_COLUMNS = [
    {"label": "ATS Code", "width": 90},
    {"label": "ATS Description", "stretch": True},
    {"label": "Standard Symbol", "width": 260},
    {"label": "Status", "width": 130},
    {"label": "Leave as-is", "width": 90},
]


def _cell(widget: QWidget, alignment: Qt.AlignmentFlag) -> QWidget:
    """Wrap widget in a plain QWidget so FixedGridTable.add_row's automatic
    QLabel restyling (which would clobber StatusBadge's semantic color, since
    StatusBadge is a QLabel subclass) never touches it, and so it can be
    given an explicit alignment inside its fixed-width grid cell instead of
    stretching to fill the whole column."""
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    layout.setAlignment(widget, alignment)
    return wrapper


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
    combo.setMaximumWidth(COMBO_MAX_WIDTH)
    combo.setMaxVisibleItems(7)
    combo.setToolTip(
        "Type to search, or pick the Standard Format code this ATS flag "
        "should be converted to."
    )

    for symbol, description in STANDARD_SYMBOL_DESCRIPTIONS.items():
        combo.addItem(f"{symbol}{COMBO_SEPARATOR}{description}")

    # The popup list must stay wide enough for long descriptions even though
    # the closed field itself is capped at COMBO_MAX_WIDTH.
    combo.view().setMinimumWidth(COMBO_POPUP_MIN_WIDTH)

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
            info.setStyleSheet(f"color: {Color.SUCCESS}; font-size: {FontSize.SMALL}px;")
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

        self._table = FixedGridTable(_COLUMNS)
        scroll_layout.addWidget(self._table)

        # Known flags (read-only display) - now goes through the same
        # table.add_row() path as suggested/unknown flags, eliminating the
        # pre-redesign special case where known rows used a different
        # construction than the other two categories.
        for ats_code, std_code in self._mapping_result.known.items():
            description = self._mapping_result.unknown.get(ats_code, ats_code)
            status_badge = StatusBadge(
                AUTO_MAPPED_LABEL, _STATUS_SEMANTIC_AUTO_MAPPED,
                tooltip="This flag code was automatically matched with high confidence. No action needed.",
            )
            self._table.add_row([
                QLabel(ats_code),
                QLabel(description),
                QLabel(std_code),
                _cell(status_badge, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                QLabel(""),
            ])

        # Suggested flags (editable combo, pre-filled, no Leave as-is)
        for ats_code, std_symbol in self._mapping_result.suggested.items():
            description = self._ats_flags.get(ats_code, ats_code)

            combo = _make_combo()
            display_text = (
                f"{std_symbol}{COMBO_SEPARATOR}"
                f"{STANDARD_SYMBOL_DESCRIPTIONS.get(std_symbol, std_symbol)}"
            )
            combo.setCurrentText(display_text)
            combo.currentTextChanged.connect(self._on_input_changed)
            self._code_inputs[ats_code] = combo

            status_badge = StatusBadge(
                SUGGESTED_MATCH_LABEL, _STATUS_SEMANTIC_SUGGESTED,
                tooltip="Matched by description similarity, not an exact code match. Please confirm or change it.",
            )

            self._table.add_row([
                QLabel(ats_code),
                QLabel(description),
                _cell(combo, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                _cell(status_badge, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                QLabel(""),
            ])

        # Unknown flags (editable combo, no pre-fill)
        for ats_code, description in self._mapping_result.unknown.items():
            combo = _make_combo()
            combo.currentTextChanged.connect(self._on_input_changed)
            self._code_inputs[ats_code] = combo

            status_badge = StatusBadge(
                NEEDS_MAPPING_LABEL, _STATUS_SEMANTIC_NEEDS_MAPPING,
                tooltip="No automatic match was found. Choose a Standard Format code, or check 'Leave as-is'.",
            )

            leave_check = QCheckBox(LEAVE_AS_IS_TEXT)
            leave_check.setToolTip(
                "Pass this ATS code through to the output unchanged, instead of "
                "mapping it to a Standard Format code."
            )
            leave_check.stateChanged.connect(
                lambda state, code=ats_code, inp=combo, badge=status_badge:
                    self._on_leave_toggled(code, inp, badge, state)
            )
            self._leave_checks[ats_code] = leave_check

            self._table.add_row([
                QLabel(ats_code),
                QLabel(description),
                _cell(combo, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                _cell(status_badge, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                _cell(leave_check, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            ])

        scroll_layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._confirm_btn = QPushButton(CONFIRM_TEXT)
        self._confirm_btn.setProperty("accent", "true")
        self._confirm_btn.setToolTip(
            "Lock in these mappings so you can convert. If you change a "
            "mapping afterward, click this again to apply the update."
        )
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self._confirm_btn)
        outer.addLayout(btn_row)

        self._update_confirm_button()

    def _on_leave_toggled(
        self, code: str, inp: QComboBox, status_badge: StatusBadge, state: int
    ) -> None:
        checked = state == Qt.CheckState.Checked.value
        inp.setEnabled(not checked)
        if checked:
            status_badge.set_status(
                LEAVE_AS_IS_TEXT, _STATUS_SEMANTIC_LEAVE_AS_IS,
                tooltip="This code will be passed through unchanged in the output.",
            )
        else:
            status_badge.set_status(
                NEEDS_MAPPING_LABEL, _STATUS_SEMANTIC_NEEDS_MAPPING,
                tooltip="No automatic match was found. Choose a Standard Format code, or check 'Leave as-is'.",
            )
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
