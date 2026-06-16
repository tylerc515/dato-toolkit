# Phase 3 — Update Email Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Update Email Generator tool that produces a formatted .docx NDE status update email, pre-fillable from a loaded tracker project.

**Architecture:** `app/email_export.py` owns the `EmailData` model and `build_email_doc()` builder (python-docx, no Node.js dependency). `app/pages/email_page.py` is a standalone page accessible from the dashboard, the header nav, and the tracker success card. `HistoryEntry` gains a backward-compatible `entry_type` field to distinguish email exports from tracker exports. Dashboard gets a fourth stat card and an email quick-action button.

**Tech Stack:** Python 3.11, PyQt6, python-docx 1.1+, openpyxl (existing), lxml (pulled in by python-docx)

---

## Reference email structure (from Sample Update Email 2026.docx)

```
[0]  Normal     "All, "
[1]  Normal     ""
[2]  Normal     "Please see below for status of NDT inspection as of {time} on {date}. ..."
[3]  Normal     ""
[4]  Normal     "COMPLETE"         run fill=00FF00
[5]  Normal     "IN PROGRESS"      run fill=FFFF00
[6]  Normal     "ISSUES NOTED"     run fill=FF0000
[7]  Normal     "Other Issues"     no fill (spec: no background)
[8]  Normal     ""
[9]  Normal     "{boiler_name}"    bold
[10] Normal     ""
[11] Normal     "{overall_summary}"
[12] Normal     "Discovery based on scope work:"  bold
[13] List Para  "{finding}" (or "None reported at this time." if empty)
[14] Normal     ""
[15] Normal     "Discovery based on visual inspection:"  bold
[16] List Para  "{finding}"
[17] Normal     ""
[18] Normal     "Scope of work:"  bold
[19] Normal     "{section_name} – {status}"   (one per section)
     Normal     ""
     Normal     "Other scope items:"  bold  (only if aux items exist)
     Normal     ""
     List Para  "{description} – {status}"  (one per aux item)
     Normal     ""
     Normal     "Punchlist"  bold  (only if punchlist items exist)
     Normal     ""
     Normal     "{description} – {status}"  (one per punchlist item)
```

En-dash separator: U+2013 ` – `

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `requirements.txt` | Modify | Add python-docx>=1.1.0 |
| `app/history.py` | Modify | Add `entry_type: str = "tracker"` to HistoryEntry |
| `app/email_export.py` | Create | EmailData, ScopeSection, OtherItem, build_email_doc |
| `app/pages/email_page.py` | Create | EmailPage widget — full UI |
| `app/pages/dashboard_page.py` | Modify | 4th stat card + email quick-action button |
| `app/pages/generate_page.py` | Modify | "Generate Update Email →" button on success card |
| `app/window.py` | Modify | EmailPage at index 8, nav button, signal wiring |
| `tests/test_email.py` | Create | Tests for EmailData round-trip and build_email_doc output |
| `tests/test_history.py` | Modify | Test entry_type round-trip |

---

## Task 1 — Add python-docx dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add python-docx to requirements.txt**

```
PyQt6>=6.6.0
openpyxl>=3.1.0
pandas>=2.0.0
requests>=2.31.0
pyinstaller>=6.0.0
reportlab>=4.0.0
pillow>=10.0.0
python-docx>=1.1.0
```

- [ ] **Step 2: Verify import works**

```
python -m pytest --collect-only -q 2>&1 | head -5
```

Expected: no import errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "Add python-docx dependency for Update Email Generator"
```

---

## Task 2 — Add entry_type to HistoryEntry (tests first)

**Files:**
- Test: `tests/test_history.py`
- Modify: `app/history.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_history.py`:

```python
def test_history_entry_default_type():
    entry = HistoryEntry(
        title="Test", customer="", location="", equipment="",
        date="", elevation_count=0, output_path="/tmp/test.xlsx"
    )
    assert entry.entry_type == "tracker"


def test_history_entry_email_type():
    entry = HistoryEntry(
        title="Test", customer="", location="", equipment="",
        date="", elevation_count=0, output_path="/tmp/test.docx",
        entry_type="update_email",
    )
    assert entry.entry_type == "update_email"


def test_history_entry_type_round_trips(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr("app.history.get_app_data_dir", lambda: tmp_path)
    entry = HistoryEntry(
        title="RB2 Email", customer="EP", location="Anytown",
        equipment="Recovery Boiler #2", date="June 2026",
        elevation_count=0, output_path="/tmp/email.docx",
        entry_type="update_email",
    )
    add_history_entry(entry)
    loaded = load_history()
    assert loaded[0].entry_type == "update_email"


def test_history_entry_missing_type_defaults_to_tracker(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr("app.history.get_app_data_dir", lambda: tmp_path)
    old_data = {"entries": [{
        "title": "Old Entry", "customer": "", "location": "",
        "equipment": "", "date": "", "elevation_count": 0,
        "output_path": "/tmp/t.xlsx", "pdf_path": "", "generated_at": ""
    }]}
    (tmp_path / "history.json").write_text(json.dumps(old_data), encoding="utf-8")
    loaded = load_history()
    assert loaded[0].entry_type == "tracker"
```

Also check what imports are at the top of `tests/test_history.py`:

```python
from app.history import HistoryEntry, add_history_entry, load_history
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_history.py::test_history_entry_default_type -v
```

Expected: `TypeError` (unexpected keyword argument `entry_type`)

- [ ] **Step 3: Add entry_type to HistoryEntry in app/history.py**

In the `HistoryEntry` dataclass, add after `generated_at`:
```python
    entry_type: str = "tracker"
```

In `HistoryEntry.from_dict`, add:
```python
            entry_type=data.get("entry_type", "tracker"),
```

- [ ] **Step 4: Run tests**

```
python -m pytest tests/test_history.py -v
```

Expected: all pass.

- [ ] **Step 5: Run full suite to check nothing broke**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app/history.py tests/test_history.py
git commit -m "Add entry_type field to HistoryEntry for email vs tracker distinction"
```

---

## Task 3 — Write failing tests for email builder

**Files:**
- Create: `tests/test_email.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for the Update Email Generator (build_email_doc)."""

from pathlib import Path

import pytest

from app.email_export import EmailData, OtherItem, ScopeSection, build_email_doc


def _minimal_data(**overrides) -> EmailData:
    base = dict(
        boiler_name="RECOVERY BOILER #2",
        status_date="6/14/2026",
        status_time="7:30 PM",
        overall_summary="Total initial data turned over to BSI is 0%.",
        scope_work_findings=[],
        visual_findings=[],
        scope_sections=[
            ScopeSection(name="Floor UT", status="No initial data received."),
        ],
        other_scope_items=[],
        punchlist_items=[],
    )
    base.update(overrides)
    return EmailData(**base)


def test_build_email_doc_creates_file(tmp_path):
    data = _minimal_data()
    out = build_email_doc(data, tmp_path / "email.docx")
    assert out.exists()
    assert out.stat().st_size > 0


def test_build_email_doc_contains_boiler_name(tmp_path):
    from docx import Document
    data = _minimal_data()
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "RECOVERY BOILER #2" in texts


def test_build_email_doc_legend_paragraphs(tmp_path):
    from docx import Document
    data = _minimal_data()
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "COMPLETE" in texts
    assert "IN PROGRESS" in texts
    assert "ISSUES NOTED" in texts
    assert "Other Issues" in texts


def test_build_email_doc_scope_section_line(tmp_path):
    from docx import Document
    data = _minimal_data(scope_sections=[
        ScopeSection(name="Floor UT", status="No initial data received."),
        ScopeSection(name="Front Wall MLO", status="In progress."),
    ])
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "Floor UT – No initial data received." in texts
    assert "Front Wall MLO – In progress." in texts


def test_build_email_doc_findings_empty_shows_none(tmp_path):
    from docx import Document
    data = _minimal_data(scope_work_findings=[], visual_findings=[])
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert texts.count("None reported at this time.") == 2


def test_build_email_doc_findings_shown(tmp_path):
    from docx import Document
    data = _minimal_data(scope_work_findings=["Economizer tube 79 cut out."])
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "Economizer tube 79 cut out." in texts
    assert texts.count("None reported at this time.") == 1


def test_build_email_doc_aux_items_shown_when_present(tmp_path):
    from docx import Document
    data = _minimal_data(
        other_scope_items=[OtherItem(description="PT OF COMPOSITE PORTS", status="complete")]
    )
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "Other scope items:" in texts
    assert "PT OF COMPOSITE PORTS – complete" in texts


def test_build_email_doc_no_other_scope_heading_when_empty(tmp_path):
    from docx import Document
    data = _minimal_data(other_scope_items=[])
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "Other scope items:" not in texts


def test_build_email_doc_punchlist_shown_when_present(tmp_path):
    from docx import Document
    data = _minimal_data(
        punchlist_items=[OtherItem(description="Item 37 – UT spout 2 tube 38", status="complete")]
    )
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "Punchlist" in texts
    assert "Item 37 – UT spout 2 tube 38 – complete" in texts


def test_build_email_doc_no_punchlist_heading_when_empty(tmp_path):
    from docx import Document
    data = _minimal_data(punchlist_items=[])
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    texts = [p.text for p in doc.paragraphs]
    assert "Punchlist" not in texts


def test_build_email_doc_page_size_letter(tmp_path):
    from docx import Document
    from docx.shared import Inches
    data = _minimal_data()
    out = build_email_doc(data, tmp_path / "email.docx")
    doc = Document(str(out))
    section = doc.sections[0]
    assert abs(section.page_width.inches - 8.5) < 0.01
    assert abs(section.page_height.inches - 11.0) < 0.01
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_email.py -v
```

Expected: `ImportError: cannot import name 'EmailData' from 'app.email_export'`

---

## Task 4 — Implement app/email_export.py

**Files:**
- Create: `app/email_export.py`

- [ ] **Step 1: Create the file**

```python
"""Build formatted .docx update email documents using python-docx."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


@dataclass
class ScopeSection:
    """One boiler section and its current status line for the email."""

    name: str
    status: str = "No initial data received."


@dataclass
class OtherItem:
    """One auxiliary scope or punchlist item and its current status."""

    description: str
    status: str = "no report received"


@dataclass
class EmailData:
    """All data needed to render an NDE status update email."""

    boiler_name: str
    status_date: str
    status_time: str
    overall_summary: str
    scope_work_findings: list[str] = field(default_factory=list)
    visual_findings: list[str] = field(default_factory=list)
    scope_sections: list[ScopeSection] = field(default_factory=list)
    other_scope_items: list[OtherItem] = field(default_factory=list)
    punchlist_items: list[OtherItem] = field(default_factory=list)


# --- Separator ----------------------------------------------------------------

_SEP = " – "  # en-dash with spaces


# --- XML helpers for run shading ----------------------------------------------

def _shade_run(run, hex_color: str) -> None:
    """Apply character background shading to a run via XML."""
    rPr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    rPr.append(shd)


# --- Document construction ----------------------------------------------------

def _add_blank(doc: Document) -> None:
    doc.add_paragraph("")


def _add_bold(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True


def _add_shaded_legend(doc: Document, text: str, fill: str | None) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    if fill:
        _shade_run(run, fill)


def _add_findings(doc: Document, findings: list[str]) -> None:
    if not findings:
        doc.add_paragraph("None reported at this time.", style="List Paragraph")
    else:
        for finding in findings:
            doc.add_paragraph(finding, style="List Paragraph")


def _add_other_items(doc: Document, items: list[OtherItem]) -> None:
    for item in items:
        doc.add_paragraph(item.description + _SEP + item.status, style="List Paragraph")


def build_email_doc(data: EmailData, output_path: str | Path) -> Path:
    """Generate a formatted update email .docx and save to output_path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    # Page setup: US Letter, 1" margins
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    # Default font
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Opening
    doc.add_paragraph("All,")
    _add_blank(doc)
    doc.add_paragraph(
        f"Please see below for status of NDT inspection as of "
        f"{data.status_time} on {data.status_date}. "
        f"If you have any questions, please don't hesitate to reach out."
    )
    _add_blank(doc)

    # Legend
    _add_shaded_legend(doc, "COMPLETE", "00FF00")
    _add_shaded_legend(doc, "IN PROGRESS", "FFFF00")
    _add_shaded_legend(doc, "ISSUES NOTED", "FF0000")
    _add_shaded_legend(doc, "Other Issues", None)
    _add_blank(doc)

    # Boiler heading
    _add_bold(doc, data.boiler_name)
    _add_blank(doc)

    # Overall summary
    doc.add_paragraph(data.overall_summary)
    _add_blank(doc)

    # Discovery — scope work
    _add_bold(doc, "Discovery based on scope work:")
    _add_findings(doc, data.scope_work_findings)
    _add_blank(doc)

    # Discovery — visual
    _add_bold(doc, "Discovery based on visual inspection:")
    _add_findings(doc, data.visual_findings)
    _add_blank(doc)

    # Scope of work
    _add_bold(doc, "Scope of work:")
    for s in data.scope_sections:
        doc.add_paragraph(s.name + _SEP + s.status)
    _add_blank(doc)

    # Other scope items
    if data.other_scope_items:
        _add_bold(doc, "Other scope items:")
        _add_blank(doc)
        _add_other_items(doc, data.other_scope_items)
        _add_blank(doc)

    # Punchlist
    if data.punchlist_items:
        _add_bold(doc, "Punchlist")
        _add_blank(doc)
        for item in data.punchlist_items:
            doc.add_paragraph(item.description + _SEP + item.status)

    doc.save(str(output_path))
    return output_path
```

- [ ] **Step 2: Run the tests**

```
python -m pytest tests/test_email.py -v
```

Expected: all pass.

- [ ] **Step 3: Run full suite**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add app/email_export.py tests/test_email.py
git commit -m "Add EmailData model and build_email_doc (python-docx) for Update Email Generator"
```

---

## Task 5 — Create EmailPage UI

**Files:**
- Create: `app/pages/email_page.py`

- [ ] **Step 1: Create the file**

```python
"""Update Email Generator page."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from PyQt6.QtCore import QUrl

from app.email_export import EmailData, OtherItem, ScopeSection, build_email_doc
from app.history import HistoryEntry, add_history_entry
from app.project import ProjectConfig, sanitize_filename
from app.styles import apply_card_shadow, color
from app.widgets import HelpPanel

logger = logging.getLogger(__name__)

# --- UI text ------------------------------------------------------------------

TITLE_TEXT = "Update Email Generator"
BACK_TEXT = "← Back"
GENERATE_TEXT = "Generate Email Document"
GENERATING_TEXT = "Generating document…"
SUCCESS_TITLE = "Document Generated"
SUCCESS_TEXT = "Your update email document was generated successfully."
OPEN_DOC_TEXT = "Open Document"
OPEN_FOLDER_TEXT = "Open Folder"
GENERATE_ANOTHER_TEXT = "Generate Another"
BROWSE_TEXT = "Browse…"
DOCX_SUFFIX = ".docx"
STATUS_HINT = "Tip: Load a tracker project first so sections are pre-filled automatically."

STATUS_OPTIONS = [
    "No initial data received.",
    "In progress.",
    "100% of initial data received. Verifications complete. No issues noted.",
    "100% of initial data received. Verifications complete. Issues noted — see below.",
    "Custom...",
]

HELP_TITLE = "Update Email Generator"
HELP_BODY = """
<p>The Update Email Generator creates a formatted Word document (.docx)
with the standard BSI NDE status update structure.</p>
<p>If you have already generated a tracker for this project, load it first
and the sections and auxiliary items will be pre-filled automatically.</p>
<p>Fill in the discovery findings and adjust each section status as data
comes in during the outage. Generate a new email at any time — each
generation creates a new file.</p>
<p><b>Tip:</b> Use the status dropdown on each scope section to quickly
update from "No initial data received" to "100% complete" as work progresses.</p>
"""


# --- Worker -------------------------------------------------------------------

class _EmailWorker(QThread):
    finished_ok = pyqtSignal(Path)
    failed = pyqtSignal(str)

    def __init__(self, data: EmailData, output_path: Path, parent=None):
        super().__init__(parent)
        self._data = data
        self._output_path = output_path

    def run(self) -> None:
        try:
            result = build_email_doc(self._data, self._output_path)
            self.finished_ok.emit(result)
        except Exception as exc:
            logger.exception("Email generation failed")
            self.failed.emit(str(exc))


# --- Sub-widgets --------------------------------------------------------------

class _FindingList(QWidget):
    """Simple add/remove list for free-text findings."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._list = QListWidget()
        self._list.setFixedHeight(100)
        layout.addWidget(self._list)

        entry_row = QHBoxLayout()
        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Enter finding and press Add")
        self._entry.returnPressed.connect(self._add)
        entry_row.addWidget(self._entry, 1)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add)
        entry_row.addWidget(add_btn)
        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("flat", "true")
        remove_btn.clicked.connect(self._remove)
        entry_row.addWidget(remove_btn)
        layout.addLayout(entry_row)

    def _add(self) -> None:
        text = self._entry.text().strip()
        if text:
            self._list.addItem(text)
            self._entry.clear()
            self.changed.emit()

    def _remove(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self.changed.emit()

    def get_findings(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]

    def set_findings(self, findings: list[str]) -> None:
        self._list.clear()
        for f in findings:
            self._list.addItem(f)


class _SectionStatusRow(QWidget):
    """One row: section name label + status dropdown + optional custom text."""

    changed = pyqtSignal()

    def __init__(self, section_name: str, initial_status: str = STATUS_OPTIONS[0], parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        name_label = QLabel(section_name)
        name_label.setMinimumWidth(200)
        name_label.setWordWrap(False)
        layout.addWidget(name_label, 1)

        self._combo = QComboBox()
        for opt in STATUS_OPTIONS:
            self._combo.addItem(opt)
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self._combo, 2)

        self._custom = QLineEdit()
        self._custom.setPlaceholderText("Custom status text…")
        self._custom.setVisible(False)
        self._custom.textChanged.connect(self.changed)
        layout.addWidget(self._custom, 2)

        self._name = section_name
        self._set_status(initial_status)

    def _set_status(self, status: str) -> None:
        if status in STATUS_OPTIONS[:-1]:
            idx = STATUS_OPTIONS.index(status)
            self._combo.setCurrentIndex(idx)
            self._custom.setVisible(False)
        else:
            self._combo.setCurrentIndex(len(STATUS_OPTIONS) - 1)
            self._custom.setText(status)
            self._custom.setVisible(True)

    def _on_combo_changed(self, idx: int) -> None:
        is_custom = (idx == len(STATUS_OPTIONS) - 1)
        self._custom.setVisible(is_custom)
        self.changed.emit()

    def get_status(self) -> str:
        if self._combo.currentIndex() == len(STATUS_OPTIONS) - 1:
            return self._custom.text().strip() or STATUS_OPTIONS[0]
        return self._combo.currentText()

    def get_name(self) -> str:
        return self._name


class _OtherItemRow(QWidget):
    """One row: description label + status text field."""

    changed = pyqtSignal()

    def __init__(self, description: str, initial_status: str = "no report received", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        label = QLabel(description[:80] + ("…" if len(description) > 80 else ""))
        label.setWordWrap(False)
        label.setToolTip(description)
        layout.addWidget(label, 1)

        self._status = QLineEdit(initial_status)
        self._status.setMinimumWidth(220)
        self._status.textChanged.connect(self.changed)
        layout.addWidget(self._status, 1)

        self._description = description

    def get_status(self) -> str:
        return self._status.text().strip() or "no report received"

    def get_description(self) -> str:
        return self._description


# --- Main page ----------------------------------------------------------------

class EmailPage(QWidget):
    """Standalone Update Email Generator page."""

    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: Optional[_EmailWorker] = None
        self._last_output: Optional[Path] = None
        self._section_rows: list[_SectionStatusRow] = []
        self._aux_rows: list[_OtherItemRow] = []
        self._punch_rows: list[_OtherItemRow] = []
        self._build_ui()

    # --- UI construction ------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)

        content_wrapper = QWidget()
        content_wrapper_layout = QVBoxLayout(content_wrapper)
        content_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_row = QHBoxLayout()
        back_btn = QPushButton(BACK_TEXT)
        back_btn.setProperty("flat", "true")
        back_btn.clicked.connect(self.back_requested.emit)
        header_row.addWidget(back_btn)
        title = QLabel(TITLE_TEXT)
        title.setProperty("role", "heading")
        header_row.addWidget(title)
        header_row.addStretch(1)
        help_btn = QPushButton("?")
        help_btn.setFixedSize(32, 32)
        help_btn.setProperty("flat", "true")
        help_btn.clicked.connect(self._toggle_help)
        header_row.addWidget(help_btn)
        content_wrapper_layout.addLayout(header_row)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        self._form_layout = QVBoxLayout(scroll_content)
        self._form_layout.setSpacing(16)
        scroll.setWidget(scroll_content)
        content_wrapper_layout.addWidget(scroll, 1)

        self._build_project_info()
        self._build_overall_status()
        self._build_findings_section("Discovery Based on Scope Work", "scope_work")
        self._build_findings_section("Discovery Based on Visual Inspection", "visual")
        self._build_scope_section()
        self._build_other_items_section()
        self._build_punchlist_section()
        self._build_output_section()
        self._form_layout.addStretch(1)

        outer.addWidget(content_wrapper, 1)
        self.help_panel = HelpPanel(HELP_TITLE, HELP_BODY)
        outer.addWidget(self.help_panel)

    def _section_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("card", "true")
        apply_card_shadow(card)
        layout = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setProperty("role", "heading")
        layout.addWidget(heading)
        return card, layout

    def _build_project_info(self) -> None:
        card, layout = self._section_card("Project Info")
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Boiler Name"))
        self._boiler_edit = QLineEdit()
        self._boiler_edit.setPlaceholderText("e.g. RECOVERY BOILER #2")
        row1.addWidget(self._boiler_edit, 1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Status Date"))
        self._date_edit = QLineEdit(date.today().strftime("%-m/%-d/%Y") if hasattr(date, "strftime") else date.today().isoformat())
        row2.addWidget(self._date_edit, 1)
        row2.addWidget(QLabel("Status Time"))
        self._time_edit = QLineEdit(datetime.now().strftime("%I:%M %p").lstrip("0"))
        row2.addWidget(self._time_edit, 1)
        layout.addLayout(row2)
        self._form_layout.addWidget(card)

    def _build_overall_status(self) -> None:
        card, layout = self._section_card("Overall Status")
        layout.addWidget(QLabel("Summary text (auto-filled, editable):"))
        self._summary_edit = QPlainTextEdit()
        self._summary_edit.setFixedHeight(80)
        self._summary_edit.setPlainText("No initial data received.")
        layout.addWidget(self._summary_edit)
        self._form_layout.addWidget(card)

    def _build_findings_section(self, title: str, key: str) -> None:
        card, layout = self._section_card(title)
        finder = _FindingList()
        if key == "scope_work":
            self._scope_work_list = finder
        else:
            self._visual_list = finder
        layout.addWidget(finder)
        self._form_layout.addWidget(card)

    def _build_scope_section(self) -> None:
        card, layout = self._section_card("Scope of Work")
        self._scope_container = QVBoxLayout()
        self._scope_container.setSpacing(4)
        layout.addLayout(self._scope_container)
        self._no_sections_label = QLabel("No sections loaded. Load a tracker project to pre-fill.")
        self._no_sections_label.setProperty("role", "muted")
        self._scope_container.addWidget(self._no_sections_label)
        self._form_layout.addWidget(card)

    def _build_other_items_section(self) -> None:
        card, layout = self._section_card("Other Scope Items")
        self._aux_container = QVBoxLayout()
        self._aux_container.setSpacing(4)
        layout.addLayout(self._aux_container)
        self._no_aux_label = QLabel("No auxiliary items. Load a tracker project with auxiliary items.")
        self._no_aux_label.setProperty("role", "muted")
        self._aux_container.addWidget(self._no_aux_label)
        self._other_items_card = card
        self._form_layout.addWidget(card)

    def _build_punchlist_section(self) -> None:
        card, layout = self._section_card("Punchlist")
        self._punch_container = QVBoxLayout()
        self._punch_container.setSpacing(4)
        layout.addLayout(self._punch_container)
        self._no_punch_label = QLabel("No punchlist items.")
        self._no_punch_label.setProperty("role", "muted")
        self._punch_container.addWidget(self._no_punch_label)
        self._punch_card = card
        self._form_layout.addWidget(card)

    def _build_output_section(self) -> None:
        card, layout = self._section_card("Output")

        fn_row = QHBoxLayout()
        fn_row.addWidget(QLabel("Filename"))
        self._filename_edit = QLineEdit()
        fn_row.addWidget(self._filename_edit, 1)
        layout.addLayout(fn_row)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder"))
        self._folder_edit = QLineEdit(str(Path.home() / "Documents"))
        folder_row.addWidget(self._folder_edit, 1)
        browse_btn = QPushButton(BROWSE_TEXT)
        browse_btn.setProperty("flat", "true")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._success_card = QFrame()
        self._success_card.setProperty("card", "true")
        success_layout = QVBoxLayout(self._success_card)
        success_heading = QLabel(SUCCESS_TITLE)
        success_heading.setProperty("role", "heading")
        success_layout.addWidget(success_heading)
        success_text = QLabel(SUCCESS_TEXT)
        success_layout.addWidget(success_text)
        success_btns = QHBoxLayout()
        self._open_doc_btn = QPushButton(OPEN_DOC_TEXT)
        self._open_doc_btn.setProperty("accent", "true")
        self._open_doc_btn.clicked.connect(self._open_document)
        success_btns.addWidget(self._open_doc_btn)
        self._open_folder_btn = QPushButton(OPEN_FOLDER_TEXT)
        self._open_folder_btn.setProperty("flat", "true")
        self._open_folder_btn.clicked.connect(self._open_folder)
        success_btns.addWidget(self._open_folder_btn)
        self._again_btn = QPushButton(GENERATE_ANOTHER_TEXT)
        self._again_btn.setProperty("flat", "true")
        self._again_btn.clicked.connect(self._reset)
        success_btns.addWidget(self._again_btn)
        success_layout.addLayout(success_btns)
        self._success_card.setVisible(False)
        layout.addWidget(self._success_card)

        self._generate_btn = QPushButton(GENERATE_TEXT)
        self._generate_btn.setProperty("accent", "true")
        self._generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(self._generate_btn)

        self._form_layout.addWidget(card)

    # --- Public API -----------------------------------------------------------

    def set_project(self, config: ProjectConfig) -> None:
        """Pre-fill from a loaded ProjectConfig (linked mode)."""
        self._boiler_edit.setText(config.equipment or config.title)
        self._update_filename()
        self._populate_scope_sections(config.sections)
        self._populate_aux_items(config.auxiliary_items)
        self._populate_punchlist_items(config.punchlist_items)

    def clear_project(self) -> None:
        """Reset to standalone (blank) mode."""
        self._boiler_edit.clear()
        self._populate_scope_sections([])
        self._populate_aux_items([])
        self._populate_punchlist_items([])
        self._update_filename()

    # --- Internals ------------------------------------------------------------

    def _toggle_help(self) -> None:
        self.help_panel.toggle()

    def _populate_scope_sections(self, sections) -> None:
        self._section_rows.clear()
        while self._scope_container.count():
            item = self._scope_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not sections:
            self._scope_container.addWidget(self._no_sections_label)
            self._no_sections_label.setParent(None)
            # re-add to container
            no_lbl = QLabel("No sections loaded. Load a tracker project to pre-fill.")
            no_lbl.setProperty("role", "muted")
            self._scope_container.addWidget(no_lbl)
            return

        for section in sections:
            name = getattr(section, "display_name", None) or getattr(section, "name", str(section))
            row = _SectionStatusRow(name)
            self._section_rows.append(row)
            self._scope_container.addWidget(row)

    def _populate_aux_items(self, items) -> None:
        self._aux_rows.clear()
        while self._aux_container.count():
            item = self._aux_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            no_lbl = QLabel("No auxiliary items. Load a tracker project with auxiliary items.")
            no_lbl.setProperty("role", "muted")
            self._aux_container.addWidget(no_lbl)
            return

        for item in items:
            desc = getattr(item, "description", str(item))
            row = _OtherItemRow(desc)
            self._aux_rows.append(row)
            self._aux_container.addWidget(row)

    def _populate_punchlist_items(self, items) -> None:
        self._punch_rows.clear()
        while self._punch_container.count():
            item = self._punch_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            no_lbl = QLabel("No punchlist items.")
            no_lbl.setProperty("role", "muted")
            self._punch_container.addWidget(no_lbl)
            return

        for item in items:
            desc = getattr(item, "description", str(item))
            row = _OtherItemRow(desc)
            self._punch_rows.append(row)
            self._punch_container.addWidget(row)

    def _update_filename(self) -> None:
        boiler = self._boiler_edit.text()
        today = date.today().strftime("%Y%m%d")
        name = sanitize_filename(boiler) if boiler else "UpdateEmail"
        self._filename_edit.setText(f"{name}_Update_Email_{today}{DOCX_SUFFIX}")

    def _browse_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output folder", self._folder_edit.text())
        if directory:
            self._folder_edit.setText(directory)

    def _build_email_data(self) -> EmailData:
        return EmailData(
            boiler_name=self._boiler_edit.text() or "BOILER",
            status_date=self._date_edit.text(),
            status_time=self._time_edit.text(),
            overall_summary=self._summary_edit.toPlainText(),
            scope_work_findings=self._scope_work_list.get_findings(),
            visual_findings=self._visual_list.get_findings(),
            scope_sections=[
                ScopeSection(name=r.get_name(), status=r.get_status())
                for r in self._section_rows
            ],
            other_scope_items=[
                OtherItem(description=r.get_description(), status=r.get_status())
                for r in self._aux_rows
            ],
            punchlist_items=[
                OtherItem(description=r.get_description(), status=r.get_status())
                for r in self._punch_rows
            ],
        )

    def _on_generate(self) -> None:
        filename = self._filename_edit.text().strip()
        folder = self._folder_edit.text().strip()
        if not filename or not folder:
            return

        output_path = Path(folder) / filename
        data = self._build_email_data()

        self._success_card.setVisible(False)
        self._progress_bar.setVisible(True)
        self._generate_btn.setEnabled(False)

        self._worker = _EmailWorker(data, output_path)
        self._worker.finished_ok.connect(self._on_generate_finished)
        self._worker.failed.connect(self._on_generate_failed)
        self._worker.start()

    def _on_generate_finished(self, output_path: Path) -> None:
        self._last_output = output_path
        self._progress_bar.setVisible(False)
        self._generate_btn.setEnabled(True)
        self._success_card.setVisible(True)

        entry = HistoryEntry(
            title=self._boiler_edit.text() or "Update Email",
            customer="",
            location="",
            equipment=self._boiler_edit.text() or "",
            date=self._date_edit.text(),
            elevation_count=0,
            output_path=str(output_path),
            entry_type="update_email",
        )
        add_history_entry(entry)

    def _on_generate_failed(self, message: str) -> None:
        self._progress_bar.setVisible(False)
        self._generate_btn.setEnabled(True)
        logger.error("Email generation failed: %s", message)

    def _open_document(self) -> None:
        if self._last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output)))

    def _open_folder(self) -> None:
        if self._last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output.parent)))

    def _reset(self) -> None:
        self._success_card.setVisible(False)
        self._last_output = None
```

- [ ] **Step 2: Run full test suite to confirm nothing broke**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add app/pages/email_page.py
git commit -m "Add EmailPage UI for Update Email Generator"
```

---

## Task 6 — Update DashboardPage (4th stat + email button)

**Files:**
- Modify: `app/pages/dashboard_page.py`

- [ ] **Step 1: Add the email_requested signal and button constants**

Add `email_requested = pyqtSignal()` to the signal list in `DashboardPage`:

```python
    new_tracker_requested = pyqtSignal()
    project_selected = pyqtSignal(Path)
    view_history_requested = pyqtSignal()
    view_projects_requested = pyqtSignal()
    batch_requested = pyqtSignal()
    email_requested = pyqtSignal()
```

Add constant at top of file:
```python
GENERATE_EMAIL_TEXT = "Generate Update Email"
STAT_EMAILS_LABEL = "Update Emails"
```

- [ ] **Step 2: Add the email button to the header row in _build_ui**

In `_build_ui`, after the `self.batch_button` block and before the `self.new_tracker_button` block:

```python
        self.email_button = QPushButton(GENERATE_EMAIL_TEXT)
        self.email_button.setProperty("flat", "true")
        self.email_button.setToolTip("Generate a formatted NDE status update email document")
        self.email_button.clicked.connect(self.email_requested.emit)
        header_row.addWidget(self.email_button)
```

- [ ] **Step 3: Add email count to _refresh_stats**

In `_refresh_stats`, change the stats list to add an email count card:

```python
    def _refresh_stats(self, total_projects: int, history: list[HistoryEntry]) -> None:
        _clear_layout(self.stats_row)

        tracker_history = [e for e in history if e.entry_type != "update_email"]
        email_count = sum(1 for e in history if e.entry_type == "update_email")
        total_elevations = sum(entry.elevation_count for entry in tracker_history)
        last_generated = format_timestamp(tracker_history[0].generated_at) if tracker_history else NEVER_TEXT

        stats = [
            (str(total_projects), STAT_PROJECTS_LABEL),
            (str(len(tracker_history)), STAT_GENERATED_LABEL),
            (str(total_elevations), STAT_ELEVATIONS_LABEL),
            (str(email_count), STAT_EMAILS_LABEL),
        ]
        for value, label in stats:
            self.stats_row.addWidget(self._make_stat_card(value, label), 1)
```

- [ ] **Step 4: Run full test suite**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/pages/dashboard_page.py
git commit -m "Add Update Emails stat card and email quick-action button to dashboard"
```

---

## Task 7 — Wire EmailPage into window.py + add nav button

**Files:**
- Modify: `app/window.py`

- [ ] **Step 1: Add imports and constants**

Add to the import block:
```python
from app.pages.email_page import EmailPage
from app.pages.email_page import STATUS_HINT as EMAIL_STATUS_HINT
```

Add to constants block after `PROJECTS_PAGE_INDEX = 7`:
```python
EMAIL_PAGE_INDEX = 8
EMAIL_BUTTON_TEXT = "✉ Update Email"
```

Add `EMAIL_STATUS_HINT` to the `STATUS_HINTS` list (after `PROJECTS_STATUS_HINT`):
```python
STATUS_HINTS = [
    DASHBOARD_STATUS_HINT,
    IMPORT_STATUS_HINT,
    REORDER_STATUS_HINT,
    GENERATE_STATUS_HINT,
    HISTORY_STATUS_HINT,
    SETTINGS_STATUS_HINT,
    BATCH_STATUS_HINT,
    PROJECTS_STATUS_HINT,
    EMAIL_STATUS_HINT,
]
```

- [ ] **Step 2: Add EmailPage to the stack in _build_ui**

In `_build_ui`, after `self.projects_page = ProjectsPage()` and its `addWidget` call:
```python
        self.email_page = EmailPage()
        self.stack.addWidget(self.email_page)
```

Connect signals:
```python
        self.email_page.back_requested.connect(self._go_to_dashboard)
        self.dashboard_page.email_requested.connect(self._go_to_email)
        self.generate_page.email_requested.connect(self._go_to_email_with_config)
```

- [ ] **Step 3: Add the Update Email nav button in _build_header**

In `_build_header`, after the `self.settings_button` block and before `layout.addStretch(1)`:

```python
        self.email_nav_button = QPushButton(EMAIL_BUTTON_TEXT)
        self.email_nav_button.setProperty("flat", "true")
        self.email_nav_button.setToolTip("Generate a formatted NDE status update email")
        self.email_nav_button.clicked.connect(self._go_to_email)
        layout.addWidget(self.email_nav_button)
```

- [ ] **Step 4: Add navigation methods**

```python
    def _go_to_email(self) -> None:
        self.stack.setCurrentIndex(EMAIL_PAGE_INDEX)

    def _go_to_email_with_config(self, config: ProjectConfig) -> None:
        self.email_page.set_project(config)
        self.stack.setCurrentIndex(EMAIL_PAGE_INDEX)
```

- [ ] **Step 5: Update _on_page_changed to handle the email page**

In `_on_page_changed`, update the `step_container.setVisible` line:
```python
        self.step_container.setVisible(0 < index < HISTORY_PAGE_INDEX)
```
This already hides the step indicator for index >= 4, which includes index 8. No change needed.

The `if index == 0: self.dashboard_page.refresh()` block already handles dashboard refresh. No additional refresh needed for EmailPage.

- [ ] **Step 6: Run full test suite**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add app/window.py
git commit -m "Add EmailPage to main window stack with nav button and dashboard/generate-page wiring"
```

---

## Task 8 — Add "Generate Update Email →" button to generate_page success card

**Files:**
- Modify: `app/pages/generate_page.py`

- [ ] **Step 1: Add the signal and constant**

Add to the signal list in `GeneratePage`:
```python
    email_requested = pyqtSignal(object)  # ProjectConfig
```

Add constant near other button text constants:
```python
GEN_EMAIL_TEXT = "Generate Update Email →"
```

- [ ] **Step 2: Add the button to the success card**

In `_build_ui`, in the `success_buttons` layout block, after `self.new_project_button`:

```python
        self.gen_email_button = QPushButton(GEN_EMAIL_TEXT)
        self.gen_email_button.setProperty("accent", "true")
        self.gen_email_button.setToolTip("Generate a formatted status update email for this project")
        self.gen_email_button.clicked.connect(self._on_email_requested)
        success_buttons.addWidget(self.gen_email_button)
```

- [ ] **Step 3: Add the handler**

```python
    def _on_email_requested(self) -> None:
        if self._config is not None:
            self.email_requested.emit(self._config)
```

- [ ] **Step 4: Run full test suite**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/pages/generate_page.py
git commit -m "Add Generate Update Email button to tracker success card"
```

---

## Task 9 — Bump version, tag v2.1.0

**Files:**
- Modify: `app/__init__.py`

- [ ] **Step 1: Bump version**

```python
__version__ = "2.1.0"
__app_name__ = "DATO Toolkit"
```

- [ ] **Step 2: Run full test suite**

```
python -m pytest --tb=short -q
```

Expected: all pass.

- [ ] **Step 3: Commit and tag**

```bash
git add app/__init__.py
git commit -m "Bump version to 2.1.0 — Update Email Generator (Phase 3)"
git tag v2.1.0
```
