"""Shared component library built exclusively from app.design.tokens.

FixedGridTable is the fix for the converter-page column-alignment bug
class: one shared QGridLayout drives the header row AND every data row,
so columns are guaranteed to line up - never build a table as a stack
of independent per-row QHBoxLayouts again. Any table anywhere in the
app must use this component.
"""
from __future__ import annotations

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.design.icons import icon
from app.design.qss import apply_style
from app.design.tokens import Color, FontSize, Radius, Spacing
from app.design.tooltip import set_tooltip

ICON_BUTTON_SIZE = 32
ICON_BUTTON_SIZE_SMALL = 28

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


class IconButton(QPushButton):
    """Square, outlined button holding one glyph or icon and nothing else.

    Always carries a tooltip because there is no text label to read. The
    `iconButton` property zeroes the global button padding, which otherwise
    leaves no room for the glyph inside a 28-32px square."""

    def __init__(
        self,
        glyph: str,
        tooltip: str,
        *,
        icon_name: str | None = None,
        size: int = ICON_BUTTON_SIZE,
        parent: QWidget | None = None,
    ):
        super().__init__(glyph, parent)
        if icon_name is not None:
            self.setIcon(icon(icon_name))
        self.setProperty("flat", "true")
        self.setProperty("iconButton", "true")
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        set_tooltip(self, tooltip)


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
        tooltip: str | None = None,
    ):
        super().__init__(parent)
        if tooltip:
            set_tooltip(self, tooltip)
        self._label_label = QLabel(label)
        apply_style(self._label_label, f"color: {Color.TEXT_MUTED}; font-size: {FontSize.SMALL}px;")
        self.layout().addWidget(self._label_label)

        self._value_label = QLabel(value)
        apply_style(
            self._value_label,
            f"color: {value_color}; font-size: {FontSize.STAT_NUMBER}px; font-weight: 500;",
        )
        self.layout().addWidget(self._value_label)

    def set_value(self, value: str, color: str | None = None) -> None:
        self._value_label.setText(value)
        if color is not None:
            apply_style(
                self._value_label,
                f"color: {color}; font-size: {FontSize.STAT_NUMBER}px; font-weight: 500;",
            )


class StatusBadge(QLabel):
    """Small pill-shaped status label with a semantic dot + text."""

    def __init__(
        self,
        text: str,
        semantic: str,
        parent: QWidget | None = None,
        tooltip: str | None = None,
    ):
        super().__init__(text, parent)
        self._semantic = semantic
        self.set_status(text, semantic, tooltip=tooltip)

    def set_status(self, text: str, semantic: str, tooltip: str | None = None) -> None:
        if semantic not in _SEMANTIC_COLORS:
            raise ValueError(f"Unknown StatusBadge semantic: {semantic!r}")
        self._semantic = semantic
        self.setText(text)
        badge_color = _SEMANTIC_COLORS[semantic]
        apply_style(
            self,
            f"color: {badge_color}; font-size: {FontSize.SMALL}px; "
            f"border-radius: {Radius.PILL}px; padding: 2px {Spacing.SM}px;",
        )
        if tooltip is not None:
            set_tooltip(self, tooltip)


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
            apply_style(
                header_cell,
                f"background-color: {Color.TABLE_HEADER_BG}; color: {Color.TEXT_MUTED}; "
                f"font-size: {FontSize.LABEL}px; font-weight: 600; padding: {Spacing.SM}px;",
            )
            if col.get("tooltip"):
                set_tooltip(header_cell, col["tooltip"])
            self._grid.addWidget(header_cell, 0, col_idx)

        self._next_row = 1

    def add_row(self, values: list[QWidget]) -> None:
        if len(values) != len(self._columns):
            raise ValueError(
                f"add_row expected {len(self._columns)} values, got {len(values)}"
            )
        for col_idx, widget in enumerate(values):
            if type(widget) is QLabel:
                apply_style(
                    widget,
                    f"color: {Color.TEXT_SECONDARY}; font-size: {FontSize.BODY}px; "
                    f"border-top: 1px solid {Color.BORDER}; padding: {Spacing.SM}px;",
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


# --- Responsive containers -----------------------------------------------------


class PageScrollArea(QScrollArea):
    """Vertical-only scroll region for a page's content.

    When the window is shorter than the content, the page scrolls; nothing
    inside is ever squeezed. Never scrolls sideways - width is handled by
    wrapping (FlowLayout) and stacking (ResponsiveColumns), and the window's
    minimum width guarantees the narrowest usable layout still fits."""

    def __init__(self, content: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidget(content)


def keep_content_height(widget: QWidget) -> None:
    """Forbid a layout from shrinking this widget below its own content height.

    Rows and cards default to a Preferred vertical policy, which lets a starved
    layout compress them until text is cut in half and buttons paint as empty
    rectangles. Minimum keeps sizeHint as the floor while still allowing growth."""
    policy = widget.sizePolicy()
    policy.setVerticalPolicy(QSizePolicy.Policy.Minimum)
    widget.setSizePolicy(policy)


class FlowLayout(QLayout):
    """Items flow left to right and wrap to the next line when the row is full.

    Port of Qt's canonical FlowLayout example with two additions:

    - `align_right`: each line is pushed against the right edge (for a page
      header's action buttons, which sit opposite the title).
    - `equal_widths`: items are laid out as a balanced grid of equal-width
      columns instead of ragged lines - four stat cards go 4 across, then 2x2,
      then a single column as the width shrinks. Column count is chosen so
      every row is as full as possible (4 items never render as 3 + 1)."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        h_spacing: int = Spacing.SM,
        v_spacing: int = Spacing.SM,
        align_right: bool = False,
        equal_widths: bool = False,
    ):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self._align_right = align_right
        self._equal_widths = equal_widths

    # -- QLayout interface --------------------------------------------------

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    # -- Layout algorithm ---------------------------------------------------

    def _lines(self, width: int) -> list[list[tuple[QLayoutItem, int]]]:
        """Group items into lines as (item, width) pairs for the given width."""
        if self._equal_widths:
            return self._grid_lines(width)
        lines: list[list[tuple[QLayoutItem, int]]] = []
        current: list[tuple[QLayoutItem, int]] = []
        x = 0
        for item in self._items:
            item_width = item.sizeHint().width()
            if current and x + item_width > width:
                lines.append(current)
                current, x = [], 0
            current.append((item, item_width))
            x += item_width + self._h_spacing
        if current:
            lines.append(current)
        return lines

    def _grid_lines(self, width: int) -> list[list[tuple[QLayoutItem, int]]]:
        count = len(self._items)
        if count == 0:
            return []
        widest = max(item.sizeHint().width() for item in self._items)
        fit = max(1, (width + self._h_spacing) // (widest + self._h_spacing))
        rows = -(-count // fit)  # ceiling division
        columns = -(-count // rows)  # balanced: every row as full as possible
        column_width = (width - self._h_spacing * (columns - 1)) // columns
        return [
            [(item, column_width) for item in self._items[start:start + columns]]
            for start in range(0, count, columns)
        ]

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        y = area.y()
        for line in self._lines(area.width()):
            heights = [
                item.heightForWidth(item_width) if item.hasHeightForWidth() else item.sizeHint().height()
                for item, item_width in line
            ]
            line_height = max(heights)
            line_width = sum(item_width for _, item_width in line) + self._h_spacing * (len(line) - 1)
            x = area.x() + (area.width() - line_width) if self._align_right else area.x()
            for (item, item_width), item_height in zip(line, heights):
                if not test_only:
                    if self._equal_widths:
                        item.setGeometry(QRect(x, y, item_width, line_height))
                    else:
                        # Items of different heights sit centred on their line.
                        item.setGeometry(QRect(x, y + (line_height - item_height) // 2, item_width, item_height))
                x += item_width + self._h_spacing
            y += line_height + self._v_spacing
        if self._items:
            y -= self._v_spacing
        return y - area.y() + margins.top() + margins.bottom()


class ResponsiveColumns(QWidget):
    """N sections side by side that stack into one column when narrow.

    One QBoxLayout whose direction flips at `stack_below` (the container's own
    width, in logical px). Children keep their stretch factors either way."""

    def __init__(self, stack_below: int, spacing: int = Spacing.MD, parent: QWidget | None = None):
        super().__init__(parent)
        self._stack_below = stack_below
        self._box = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._box.setContentsMargins(0, 0, 0, 0)
        self._box.setSpacing(spacing)

    def add_column(self, widget: QWidget, stretch: int = 1) -> None:
        self._box.addWidget(widget, stretch)

    @property
    def stacked(self) -> bool:
        return self._box.direction() == QBoxLayout.Direction.TopToBottom

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_direction(event.size().width())

    def _apply_direction(self, width: int) -> None:
        wanted = (
            QBoxLayout.Direction.TopToBottom if width < self._stack_below else QBoxLayout.Direction.LeftToRight
        )
        if self._box.direction() != wanted:
            self._box.setDirection(wanted)
            self.updateGeometry()
