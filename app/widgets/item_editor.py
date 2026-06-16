"""Reusable list-editor widget for auxiliary scope items and punchlist items."""

from __future__ import annotations

from uuid import uuid4

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.styles import color


class _ItemRowWidget(QWidget):
    """A single row in the item list: description label + edit/remove buttons."""

    edit_clicked = pyqtSignal()
    remove_clicked = pyqtSignal()

    def __init__(self, description: str, has_notes: bool, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        label_text = (description[:80] + "…") if len(description) > 80 else description
        label_text = label_text.replace("\n", " ")
        label = QLabel(label_text)
        label.setWordWrap(False)
        if has_notes:
            label.setToolTip("Has notes")
            label.setText(label.text() + "  \U0001f4ce")
        layout.addWidget(label, 1)

        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(28, 28)
        edit_btn.setToolTip("Edit this item")
        edit_btn.setProperty("flat", "true")
        edit_btn.clicked.connect(self.edit_clicked)
        layout.addWidget(edit_btn)

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setToolTip("Remove this item")
        remove_btn.setProperty("flat", "true")
        remove_btn.clicked.connect(self.remove_clicked)
        layout.addWidget(remove_btn)


class _EditForm(QFrame):
    """Inline add/edit form shown below the item list."""

    saved = pyqtSignal(str, str, str)  # id, description, notes
    cancelled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self._item_id = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        desc_label = QLabel("Description")
        desc_label.setProperty("role", "label")
        layout.addWidget(desc_label)

        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setPlaceholderText("Enter item description (e.g. PT OF COMPOSITE PORTS)")
        self.desc_edit.setFixedHeight(72)
        layout.addWidget(self.desc_edit)

        notes_label = QLabel("Notes (optional)")
        notes_label.setProperty("role", "label")
        layout.addWidget(notes_label)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Enter any notes or findings for this item")
        self.notes_edit.setFixedHeight(72)
        layout.addWidget(self.notes_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("flat", "true")
        cancel_btn.clicked.connect(self.cancelled)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setProperty("accent", "true")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def open_for_new(self) -> None:
        self._item_id = str(uuid4())
        self.desc_edit.setPlainText("")
        self.notes_edit.setPlainText("")
        self.desc_edit.setFocus()

    def open_for_edit(self, item_id: str, description: str, notes: str) -> None:
        self._item_id = item_id
        self.desc_edit.setPlainText(description)
        self.notes_edit.setPlainText(notes)
        self.desc_edit.setFocus()

    def _on_save(self) -> None:
        desc = self.desc_edit.toPlainText().strip()
        if not desc:
            return
        self.saved.emit(self._item_id, desc, self.notes_edit.toPlainText().strip())


class ItemEditorWidget(QWidget):
    """Reusable editor for a list of auxiliary/punchlist items with drag-to-reorder."""

    items_changed = pyqtSignal(list)  # list of dicts: {id, description, notes}

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._build_ui(title)

    def _build_ui(self, title: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        heading = QLabel(title)
        heading.setStyleSheet("font-weight: 600;")
        layout.addWidget(heading)

        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setFixedHeight(140)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self._list)

        add_btn = QPushButton("+ Add Item")
        add_btn.setProperty("accent", "true")
        add_btn.clicked.connect(self._on_add)
        layout.addWidget(add_btn)

        self._form = _EditForm()
        self._form.setVisible(False)
        self._form.saved.connect(self._on_form_saved)
        self._form.cancelled.connect(lambda: self._form.setVisible(False))
        layout.addWidget(self._form)

    # --- Public API -------------------------------------------------------

    def set_items(self, items: list[dict]) -> None:
        """Populate from a list of dicts with keys: id, description, notes."""
        self._items = [dict(i) for i in items]
        self._rebuild_list()

    def get_items(self) -> list[dict]:
        return [dict(i) for i in self._items]

    # --- Internal ---------------------------------------------------------

    def _rebuild_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for item in self._items:
            li = QListWidgetItem()
            li.setData(Qt.ItemDataRole.UserRole, item["id"])
            li.setSizeHint(QSize(0, 36))
            self._list.addItem(li)
            row_widget = _ItemRowWidget(item["description"], bool(item.get("notes")))
            row_widget.edit_clicked.connect(lambda checked=False, iid=item["id"]: self._on_edit(iid))
            row_widget.remove_clicked.connect(lambda checked=False, iid=item["id"]: self._on_remove(iid))
            self._list.setItemWidget(li, row_widget)
        self._list.blockSignals(False)

    def _sync_order_from_list(self) -> None:
        id_to_item = {i["id"]: i for i in self._items}
        new_order = []
        for row in range(self._list.count()):
            iid = self._list.item(row).data(Qt.ItemDataRole.UserRole)
            if iid in id_to_item:
                new_order.append(id_to_item[iid])
        self._items = new_order

    def _on_rows_moved(self) -> None:
        self._sync_order_from_list()
        self._rebuild_list()
        self.items_changed.emit(self.get_items())

    def _on_add(self) -> None:
        self._form.open_for_new()
        self._form.setVisible(True)

    def _on_edit(self, item_id: str) -> None:
        item = next((i for i in self._items if i["id"] == item_id), None)
        if item is None:
            return
        self._form.open_for_edit(item["id"], item["description"], item.get("notes", ""))
        self._form.setVisible(True)

    def _on_remove(self, item_id: str) -> None:
        self._items = [i for i in self._items if i["id"] != item_id]
        self._rebuild_list()
        self.items_changed.emit(self.get_items())

    def _on_form_saved(self, item_id: str, description: str, notes: str) -> None:
        existing = next((i for i in self._items if i["id"] == item_id), None)
        if existing is not None:
            existing["description"] = description
            existing["notes"] = notes
        else:
            self._items.append({"id": item_id, "description": description, "notes": notes})
        self._form.setVisible(False)
        self._rebuild_list()
        self.items_changed.emit(self.get_items())
