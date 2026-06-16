# Phase 2 — Auxiliary Scope Items & Punchlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional "AUXILIARY SCOPE ITEMS" and "PUNCHLIST" sections to the bottom of generated Excel trackers, manageable from a new collapsible panel on the Arrange Sections page.

**Architecture:** `AuxItem` dataclass added to `project.py`; `ProjectConfig` gains `auxiliary_items`/`punchlist_items` fields with backward-compatible `from_dict`. `TrackerData` in `builder.py` gains parallel fields and a new `_write_extra_sections()` function. A new `ItemEditorWidget` in `app/widgets/item_editor.py` provides the reusable list-editor UI; `ReorderPage` gains a collapsible panel that hosts two of them.

**Tech Stack:** Python 3.11, PyQt6, openpyxl 3.1+

---

## Reference styling (from sample_tracksheet_2026.xlsx)

- Section header rows: Calibri 16pt bold, `SECTION_FILL` (solid, theme=0, tint=-0.249977111117893), merged A:J, height 21.0
- Item rows: Calibri 11pt not bold (= `ELEVATION_FONT`), no fill, thin borders all sides, col A left-aligned + wrap_text, col J left-aligned + wrap_text, row height 30 (openpyxl can't auto-fit)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `app/project.py` | Modify | Add `AuxItem` dataclass; extend `ProjectConfig` |
| `app/builder.py` | Modify | Add `TrackerItem`; extend `TrackerData`; `_write_extra_sections()` |
| `app/pages/generate_page.py` | Modify | Pass aux/punchlist items to `TrackerData` |
| `app/widgets/item_editor.py` | Create | `ItemEditorWidget` — reusable list editor |
| `app/pages/reorder_page.py` | Modify | Collapsible "Additional Sections" panel |
| `tests/test_project.py` | Modify | Round-trip tests for new fields |
| `tests/test_builder.py` | Modify | Builder output tests for aux/punchlist |

---

## Task 1 — Write failing tests for ProjectConfig aux/punchlist fields

**Files:**
- Test: `tests/test_project.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_project.py`:

```python
from app.project import AuxItem


def test_aux_items_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    items = [
        AuxItem(id="a1", description="PT OF COMPOSITE PORTS", notes=""),
        AuxItem(id="a2", description="RT OF ECONOMIZER", notes="Complete"),
    ]
    config = _config(auxiliary_items=items)
    path = config.save()
    loaded = load_project(path)
    assert len(loaded.auxiliary_items) == 2
    assert loaded.auxiliary_items[0].description == "PT OF COMPOSITE PORTS"
    assert loaded.auxiliary_items[1].notes == "Complete"


def test_punchlist_items_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    items = [AuxItem(id="p1", description="ITEM 37\nUT spout 2 tube 38", notes="Reading: .286\"")]
    config = _config(punchlist_items=items)
    path = config.save()
    loaded = load_project(path)
    assert loaded.punchlist_items[0].notes == 'Reading: .286"'


def test_project_without_aux_fields_loads_fine(tmp_path, monkeypatch):
    """Existing project JSON without auxiliary_items/punchlist_items loads as empty lists."""
    import json
    monkeypatch.setattr("app.project.get_app_data_dir", lambda: tmp_path)
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True)
    old_data = _config().to_dict()
    old_data.pop("auxiliary_items", None)
    old_data.pop("punchlist_items", None)
    path = projects_dir / "old.json"
    path.write_text(json.dumps(old_data), encoding="utf-8")
    loaded = load_project(path)
    assert loaded.auxiliary_items == []
    assert loaded.punchlist_items == []
```

Also add `load_project` to the import at the top of the test file:
```python
from app.project import (
    AuxItem,
    ProjectConfig,
    find_project_for_metadata,
    find_similar_project_for_metadata,
    list_projects,
    load_project,
)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_project.py::test_aux_items_round_trip tests/test_project.py::test_punchlist_items_round_trip tests/test_project.py::test_project_without_aux_fields_loads_fine -v
```

Expected: `ImportError: cannot import name 'AuxItem'` or `AttributeError`

---

## Task 2 — Implement AuxItem and ProjectConfig changes

**Files:**
- Modify: `app/project.py`

- [ ] **Step 1: Add `AuxItem` dataclass and update `ProjectConfig`**

At the top of `app/project.py`, add `uuid` to imports:
```python
from uuid import uuid4
```

After the `FUZZY_MATCH_THRESHOLD` constant, add:
```python
@dataclass
class AuxItem:
    """A single auxiliary scope or punchlist item."""
    id: str
    description: str
    notes: str = ""
```

In `ProjectConfig`, add two new fields after `export_pdf`:
```python
    auxiliary_items: list[AuxItem] = field(default_factory=list)
    punchlist_items: list[AuxItem] = field(default_factory=list)
```

- [ ] **Step 2: Update `ProjectConfig.from_dict` to handle the new fields**

In `from_dict`, after the `sections` block and before the `return cls(...)`, add:
```python
        auxiliary_items = [
            AuxItem(
                id=i.get("id", str(uuid4())),
                description=i.get("description", ""),
                notes=i.get("notes", ""),
            )
            for i in data.get("auxiliary_items", [])
        ]
        punchlist_items = [
            AuxItem(
                id=i.get("id", str(uuid4())),
                description=i.get("description", ""),
                notes=i.get("notes", ""),
            )
            for i in data.get("punchlist_items", [])
        ]
```

Then add them to the `return cls(...)` call:
```python
            auxiliary_items=auxiliary_items,
            punchlist_items=punchlist_items,
```

- [ ] **Step 3: Run the new tests — expect PASS**

```
python -m pytest tests/test_project.py -v
```

Expected: all project tests pass.

- [ ] **Step 4: Commit**

```bash
git add app/project.py tests/test_project.py
git commit -m "Add AuxItem dataclass and aux/punchlist fields to ProjectConfig"
```

---

## Task 3 — Write failing builder tests

**Files:**
- Test: `tests/test_builder.py`

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_builder.py`:

```python
from app.builder import TrackerItem


def _minimal_data(**overrides):
    base = dict(
        title="Test Tracker",
        customer="Test Co",
        location="Plant A",
        equipment="Boiler 1",
        date="June 2026",
        sections=[TrackerSection(name="FLOOR", elevations=["EL 1", "EL 2"])],
    )
    base.update(overrides)
    return TrackerData(**base)


def test_builder_omits_aux_section_when_empty(tmp_path):
    data = _minimal_data()
    out = build_tracker(data, tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(out)
    ws = wb["Tracker"]
    values = [ws.cell(row=r, column=1).value for r in range(9, ws.max_row + 1)]
    assert "AUXILIARY SCOPE ITEMS" not in values
    assert "PUNCHLIST" not in values


def test_builder_writes_aux_section_header(tmp_path):
    data = _minimal_data(
        auxiliary_items=[TrackerItem(description="PT OF COMPOSITE PORTS", notes="")]
    )
    out = build_tracker(data, tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(out)
    ws = wb["Tracker"]
    values = [ws.cell(row=r, column=1).value for r in range(9, ws.max_row + 1)]
    assert "AUXILIARY SCOPE ITEMS" in values


def test_builder_writes_punchlist_section_header(tmp_path):
    data = _minimal_data(
        punchlist_items=[TrackerItem(description="ITEM 37\nUT spout", notes="Reading: .286\"")]
    )
    out = build_tracker(data, tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(out)
    ws = wb["Tracker"]
    values = [ws.cell(row=r, column=1).value for r in range(9, ws.max_row + 1)]
    assert "PUNCHLIST" in values


def test_builder_aux_item_description_and_notes(tmp_path):
    data = _minimal_data(
        auxiliary_items=[TrackerItem(description="RT OF ECONOMIZER", notes="Complete")]
    )
    out = build_tracker(data, tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(out)
    ws = wb["Tracker"]
    # Find the AUXILIARY SCOPE ITEMS header row
    aux_row = next(
        r for r in range(9, ws.max_row + 1)
        if ws.cell(row=r, column=1).value == "AUXILIARY SCOPE ITEMS"
    )
    item_row = aux_row + 1
    assert ws.cell(row=item_row, column=1).value == "RT OF ECONOMIZER"
    assert ws.cell(row=item_row, column=10).value == "Complete"


def test_builder_closing_border_after_aux_and_punchlist(tmp_path):
    data = _minimal_data(
        auxiliary_items=[TrackerItem(description="AUX ITEM", notes="")],
        punchlist_items=[TrackerItem(description="PUNCH ITEM", notes="")],
    )
    out = build_tracker(data, tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(out)
    ws = wb["Tracker"]
    last_row = ws.max_row
    for col in range(1, 11):
        assert ws.cell(row=last_row, column=col).border.bottom.style == "medium"


def test_builder_aux_before_punchlist(tmp_path):
    data = _minimal_data(
        auxiliary_items=[TrackerItem(description="AUX ITEM", notes="")],
        punchlist_items=[TrackerItem(description="PUNCH ITEM", notes="")],
    )
    out = build_tracker(data, tmp_path / "t.xlsx")
    wb = openpyxl.load_workbook(out)
    ws = wb["Tracker"]
    aux_row = next(r for r in range(9, ws.max_row + 1) if ws.cell(row=r, column=1).value == "AUXILIARY SCOPE ITEMS")
    punch_row = next(r for r in range(9, ws.max_row + 1) if ws.cell(row=r, column=1).value == "PUNCHLIST")
    assert aux_row < punch_row
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_builder.py::test_builder_omits_aux_section_when_empty tests/test_builder.py::test_builder_writes_aux_section_header -v
```

Expected: `ImportError: cannot import name 'TrackerItem'`

---

## Task 4 — Implement builder changes

**Files:**
- Modify: `app/builder.py`

- [ ] **Step 1: Add `TrackerItem` dataclass to `builder.py`**

After the `TrackerSection` dataclass, add:

```python
@dataclass
class TrackerItem:
    """A single auxiliary scope or punchlist entry."""
    description: str
    notes: str = ""
```

- [ ] **Step 2: Extend `TrackerData` with aux/punchlist fields**

In the `TrackerData` dataclass, add after `sections`:
```python
    auxiliary_items: list[TrackerItem] = field(default_factory=list)
    punchlist_items: list[TrackerItem] = field(default_factory=list)
```

- [ ] **Step 3: Add `_write_extra_sections()` function**

Add this function after `_write_sections()`:

```python
def _write_extra_sections(ws: Worksheet, label: str, items: list[TrackerItem], start_row: int) -> int:
    """Write an auxiliary or punchlist section block. Returns the last row written."""
    row = start_row

    # Section header — merged A:J, same style as boiler section headers
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=TRACKER_COLUMN_COUNT)
    for col in range(1, TRACKER_COLUMN_COUNT + 1):
        cell = ws.cell(row=row, column=col)
        if col == 1:
            cell.value = label
        cell.font = SECTION_FONT
        cell.fill = SECTION_FILL
        left = "medium" if col == 1 else "thin"
        right = "medium" if col == TRACKER_COLUMN_COUNT else "thin"
        cell.border = _border(left=left, right=right, top="medium", bottom="medium")
    ws.row_dimensions[row].height = SECTION_ROW_HEIGHT
    row += 1

    # Item rows
    for item in items:
        for col in range(1, TRACKER_COLUMN_COUNT + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = ELEVATION_FONT
            left = "medium" if col == 1 else "thin"
            right = "medium" if col == TRACKER_COLUMN_COUNT else "thin"
            cell.border = _border(left=left, right=right, top="thin", bottom="thin")
            if col == 1:
                cell.value = item.description
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            elif col == TRACKER_COLUMN_COUNT:
                cell.value = item.notes if item.notes else None
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws.row_dimensions[row].height = 30
        row += 1

    return row - 1
```

- [ ] **Step 4: Update `build_tracker()` to call `_write_extra_sections`**

Replace the closing-border block in `build_tracker()`:

```python
    _write_header_block(ws, data)
    _add_bsi_logo(ws)
    last_row = _write_sections(ws, data.sections)

    if data.auxiliary_items:
        last_row = _write_extra_sections(ws, "AUXILIARY SCOPE ITEMS", data.auxiliary_items, last_row + 1)
    if data.punchlist_items:
        last_row = _write_extra_sections(ws, "PUNCHLIST", data.punchlist_items, last_row + 1)

    # Close the table with a medium bottom border on the final row.
    if last_row >= 9:
        for col in range(1, TRACKER_COLUMN_COUNT + 1):
            cell = ws.cell(row=last_row, column=col)
            cell.border = _with_bottom(cell.border, "medium")
```

- [ ] **Step 5: Run all builder tests**

```
python -m pytest tests/test_builder.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/builder.py tests/test_builder.py
git commit -m "Add TrackerItem and auxiliary/punchlist section generation to builder"
```

---

## Task 5 — Wire generate_page.py to pass aux/punchlist to TrackerData

**Files:**
- Modify: `app/pages/generate_page.py`

- [ ] **Step 1: Update the import in generate_page.py**

Change:
```python
from app.builder import TrackerData, TrackerSection, build_tracker
```
to:
```python
from app.builder import TrackerData, TrackerItem, TrackerSection, build_tracker
```

- [ ] **Step 2: Pass aux/punchlist when building TrackerData**

Find the `data = TrackerData(...)` block (around line 304) and add the two new fields:

```python
        data = TrackerData(
            title=self._config.title,
            customer=self._config.customer,
            location=self._config.location,
            equipment=self._config.equipment,
            date=self._config.date,
            sections=[
                TrackerSection(name=section.display_name, elevations=list(section.elevations))
                for section in self._config.sections
            ],
            auxiliary_items=[
                TrackerItem(description=i.description, notes=i.notes)
                for i in self._config.auxiliary_items
            ],
            punchlist_items=[
                TrackerItem(description=i.description, notes=i.notes)
                for i in self._config.punchlist_items
            ],
        )
```

- [ ] **Step 3: Run all tests**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add app/pages/generate_page.py
git commit -m "Pass auxiliary and punchlist items from ProjectConfig to TrackerData in generate_page"
```

---

## Task 6 — Create ItemEditorWidget

**Files:**
- Create: `app/widgets/item_editor.py`

- [ ] **Step 1: Create the file**

```python
"""Reusable list-editor widget for auxiliary scope items and punchlist items."""

from __future__ import annotations

from uuid import uuid4

from PyQt6.QtCore import Qt, pyqtSignal
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

        label_text = description[:80] + "…" if len(description) > 80 else description
        label = QLabel(label_text)
        label.setWordWrap(False)
        if has_notes:
            label.setToolTip("Has notes")
            label.setText(label.text() + "  📎")
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
    """Inline add/edit form shown below the list."""

    saved = pyqtSignal(str, str, str)   # id, description, notes
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
        self._items: list[dict] = []  # [{id, description, notes}]
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
            li.setSizeHint(__import__("PyQt6.QtCore", fromlist=["QSize"]).QSize(0, 36))
            self._list.addItem(li)
            row_widget = _ItemRowWidget(item["description"], bool(item.get("notes")))
            row_widget.edit_clicked.connect(lambda checked=False, iid=item["id"]: self._on_edit(iid))
            row_widget.remove_clicked.connect(lambda checked=False, iid=item["id"]: self._on_remove(iid))
            self._list.setItemWidget(li, row_widget)
        self._list.blockSignals(False)

    def _sync_order_from_list(self) -> None:
        """After a drag-reorder, sync self._items to match the list widget order."""
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
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

```
python -m pytest --tb=short -q
```

Expected: all pass (ItemEditorWidget has no tests yet — UI widgets are verified manually).

- [ ] **Step 3: Commit**

```bash
git add app/widgets/item_editor.py
git commit -m "Add ItemEditorWidget for editing auxiliary scope and punchlist items"
```

---

## Task 7 — Update ReorderPage with collapsible Additional Sections panel

**Files:**
- Modify: `app/pages/reorder_page.py`

- [ ] **Step 1: Add imports at the top of reorder_page.py**

Add to the existing imports:
```python
from app.project import AuxItem
from app.widgets.item_editor import ItemEditorWidget
```

- [ ] **Step 2: Add new UI-text constants**

After the existing constants block, add:
```python
ADDITIONAL_SECTIONS_LABEL = "Additional Sections"
AUX_EDITOR_TITLE = "Auxiliary Scope Items"
PUNCH_EDITOR_TITLE = "Punchlist Items"
```

- [ ] **Step 3: Add storage fields to `__init__`**

In `ReorderPage.__init__`, after `self._export_pdf = False`, add:
```python
        self._auxiliary_items: list[dict] = []
        self._punchlist_items: list[dict] = []
```

- [ ] **Step 4: Add `_build_additional_panel()` method**

Add this method to `ReorderPage`:

```python
    def _build_additional_panel(self) -> QWidget:
        """Build the collapsible 'Additional Sections' panel."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        toggle_row = QHBoxLayout()
        self._additional_toggle = QPushButton(f"▶  {ADDITIONAL_SECTIONS_LABEL}")
        self._additional_toggle.setProperty("flat", "true")
        self._additional_toggle.setCheckable(True)
        self._additional_toggle.toggled.connect(self._on_additional_toggle)
        toggle_row.addWidget(self._additional_toggle)
        toggle_row.addStretch(1)
        layout.addLayout(toggle_row)

        self._additional_body = QWidget()
        body_layout = QVBoxLayout(self._additional_body)
        body_layout.setContentsMargins(12, 8, 0, 8)
        body_layout.setSpacing(16)

        self._aux_editor = ItemEditorWidget(AUX_EDITOR_TITLE)
        self._aux_editor.items_changed.connect(self._on_aux_changed)
        body_layout.addWidget(self._aux_editor)

        self._punch_editor = ItemEditorWidget(PUNCH_EDITOR_TITLE)
        self._punch_editor.items_changed.connect(self._on_punch_changed)
        body_layout.addWidget(self._punch_editor)

        self._additional_body.setVisible(False)
        layout.addWidget(self._additional_body)
        return container
```

- [ ] **Step 5: Update `_build_ui()` to insert the panel**

In `_build_ui`, find the `button_row` block and insert the panel just before it:

```python
        content_layout.addWidget(self._build_additional_panel())

        button_row = QHBoxLayout()
        # ... existing button_row code ...
```

(Insert after `content_layout.addLayout(split_row, 1)` and before `button_row = QHBoxLayout()`)

- [ ] **Step 6: Add the toggle and change-handler methods**

```python
    def _on_additional_toggle(self, checked: bool) -> None:
        self._additional_body.setVisible(checked)
        self._additional_toggle.setText(
            f"▼  {ADDITIONAL_SECTIONS_LABEL}" if checked else f"▶  {ADDITIONAL_SECTIONS_LABEL}"
        )

    def _on_aux_changed(self, items: list[dict]) -> None:
        self._auxiliary_items = items
        self._on_changed()

    def _on_punch_changed(self, items: list[dict]) -> None:
        self._punchlist_items = items
        self._on_changed()
```

- [ ] **Step 7: Update `load_project()` to populate the editors**

In `load_project()`, after `self._export_pdf = config.export_pdf`, add:
```python
        self._auxiliary_items = [{"id": i.id, "description": i.description, "notes": i.notes} for i in config.auxiliary_items]
        self._punchlist_items = [{"id": i.id, "description": i.description, "notes": i.notes} for i in config.punchlist_items]
        self._aux_editor.set_items(self._auxiliary_items)
        self._punch_editor.set_items(self._punchlist_items)
```

- [ ] **Step 8: Update `_build_project_config()` to include the items**

In `_build_project_config()`, after `export_pdf=self._export_pdf`, add:
```python
            auxiliary_items=[
                AuxItem(id=i["id"], description=i["description"], notes=i.get("notes", ""))
                for i in self._auxiliary_items
            ],
            punchlist_items=[
                AuxItem(id=i["id"], description=i["description"], notes=i.get("notes", ""))
                for i in self._punchlist_items
            ],
```

- [ ] **Step 9: Run all tests**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add app/pages/reorder_page.py
git commit -m "Add collapsible Additional Sections panel to ReorderPage with aux/punchlist editors"
```

---

## Task 8 — Update help text

**Files:**
- Modify: `app/pages/reorder_page.py`

- [ ] **Step 1: Update `HELP_BODY`**

Replace the existing `HELP_BODY` constant with:

```python
HELP_BODY = """
<p>Drag sections in the list to change the order they'll appear in the
generated tracker.</p>
<p>Double-click a section name to rename it.</p>
<p>The <b>Tracker Title</b> is generated automatically from your TRACE export
files, but you can edit it to match how your company names trackers.</p>
<p>The preview on the right updates as you make changes. Your progress is
saved automatically.</p>
<p><b>Auxiliary Scope Items</b> are additional inspection tasks not part of
the standard tube sections (e.g. RT of economizer, SWUT sootblower welds).
<b>Punchlist Items</b> are carry-over action items from previous inspections.
Both sections are optional and will only appear in the tracker if you add items.</p>
"""
```

- [ ] **Step 2: Run all tests one final time**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 3: Final commit**

```bash
git add app/pages/reorder_page.py
git commit -m "Update Step 2 help text to document Auxiliary and Punchlist sections"
```

---

## Task 9 — Tag and release

- [ ] **Step 1: Verify `set_files()` resets aux/punchlist editors**

In `ReorderPage.set_files()`, after `self._export_pdf = False`, add:
```python
        self._auxiliary_items = []
        self._punchlist_items = []
        self._aux_editor.set_items([])
        self._punch_editor.set_items([])
```

- [ ] **Step 2: Run full test suite**

```
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit and tag**

```bash
git add -A
git commit -m "Phase 2 complete: Auxiliary Scope Items and Punchlist sections in tracker"
git tag v2.0.1
```
