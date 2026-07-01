"""Shared component library built exclusively from app.design.tokens.

FixedGridTable is the fix for the converter-page column-alignment bug
class: one shared QGridLayout drives the header row AND every data row,
so columns are guaranteed to line up - never build a table as a stack
of independent per-row QHBoxLayouts again. Any table anywhere in the
app must use this component.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.design.tokens import Color, FontSize, Radius, Spacing

_SEMANTIC_COLORS = {
    "success": Color.SUCCESS,
    "warning": Color.WARNING,
    "danger": Color.DANGER,
}


class PrimaryButton(QPushButton):
    """Solid accent-colored call-to-action button. Styling comes from the
    QPushButton[accent="true"] QSS rule in app.styles."""

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setProperty("accent", "true")


class SecondaryButton(QPushButton):
    """Outlined, transparent-background button. Styling comes from the
    QPushButton[flat="true"] QSS rule in app.styles."""

    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setProperty("flat", "true")


class Card(QFrame):
    """Standard card surface: token background, border, radius, padding."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)


class StatCard(Card):
    """A Card showing a muted label above a large value number."""

    def __init__(
        self,
        label: str,
        value: str,
        value_color: str = Color.TEXT_PRIMARY,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._label_label = QLabel(label)
        self._label_label.setStyleSheet(f"color: {Color.TEXT_MUTED}; font-size: {FontSize.SMALL}px;")
        self.layout().addWidget(self._label_label)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {value_color}; font-size: {FontSize.STAT_NUMBER}px; font-weight: 500;"
        )
        self.layout().addWidget(self._value_label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)


class StatusBadge(QLabel):
    """Small pill-shaped status label with a semantic dot + text."""

    def __init__(self, text: str, semantic: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self._semantic = semantic
        self.set_status(text, semantic)

    def set_status(self, text: str, semantic: str) -> None:
        if semantic not in _SEMANTIC_COLORS:
            raise ValueError(f"Unknown StatusBadge semantic: {semantic!r}")
        self._semantic = semantic
        self.setText(text)
        badge_color = _SEMANTIC_COLORS[semantic]
        self.setStyleSheet(
            f"color: {badge_color}; font-size: {FontSize.SMALL}px; "
            f"border-radius: {Radius.PILL}px; padding: 2px 8px;"
        )


class FixedGridTable(QWidget):
    """A table built from ONE shared QGridLayout for the header row and
    every data row - guarantees column alignment. See module docstring.

    columns: list of {"label": str, "width": int} for fixed columns, or
    {"label": str, "stretch": True} for the ONE column allowed to grow.
    """

    def __init__(self, columns: list[dict], parent: QWidget | None = None):
        super().__init__(parent)
        stretch_cols = [c for c in columns if c.get("stretch")]
        if len(stretch_cols) != 1:
            raise ValueError(
                f"FixedGridTable requires exactly one stretch column, got {len(stretch_cols)}"
            )
        self._columns = columns
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(Spacing.MD)
        self._grid.setVerticalSpacing(0)
        self._next_row = 0

        for col_idx, col in enumerate(columns):
            if col.get("stretch"):
                self._grid.setColumnStretch(col_idx, 1)
            else:
                self._grid.setColumnMinimumWidth(col_idx, col["width"])
                self._grid.setColumnStretch(col_idx, 0)

            header_cell = QLabel(col["label"].upper())
            header_cell.setStyleSheet(
                f"background-color: {Color.TABLE_HEADER_BG}; color: {Color.TEXT_MUTED}; "
                f"font-size: {FontSize.LABEL}px; font-weight: 600; padding: {Spacing.SM}px;"
            )
            self._grid.addWidget(header_cell, 0, col_idx)

        self._next_row = 1

    def add_row(self, values: list[QWidget]) -> None:
        if len(values) != len(self._columns):
            raise ValueError(
                f"add_row expected {len(self._columns)} values, got {len(values)}"
            )
        for col_idx, widget in enumerate(values):
            if type(widget) is QLabel:
                widget.setStyleSheet(
                    f"color: {Color.TEXT_SECONDARY}; font-size: {FontSize.BODY}px; "
                    f"border-top: 1px solid {Color.BORDER}; padding: {Spacing.SM}px;"
                )
            self._grid.addWidget(widget, self._next_row, col_idx)
        self._next_row += 1

    def clear_rows(self) -> None:
        """Remove every data row, keeping the header row intact."""
        for row in range(self._next_row - 1, 0, -1):
            for col in range(len(self._columns)):
                item = self._grid.itemAtPosition(row, col)
                if item is not None and item.widget() is not None:
                    widget = item.widget()
                    self._grid.removeWidget(widget)
                    widget.deleteLater()
        self._next_row = 1
