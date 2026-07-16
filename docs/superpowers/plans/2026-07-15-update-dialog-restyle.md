# Update Dialog Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `app/widgets/update_dialog.py` off its private hardcoded palette onto the design-token / property-based styling system, with five approved UX polish items, without changing behavior.

**Architecture:** The app applies its themed QSS at the `QApplication` level (`main.py:26`), so any top-level dialog inherits it. The restyle removes the dialog's inline overrides and drives appearance from `app.design.tokens` + property selectors (`accent`, `flat`, `variant="success"`) defined in `app/styles.py`. A new reusable `variant="success"` button rule is added to the design system first.

**Tech Stack:** Python 3.14, PyQt6, pytest (Qt offscreen).

## Global Constraints

- No hex color, pixel spacing, or font-size literal anywhere outside `app/design/tokens.py` (per `tokens.py` module docstring).
- App ships a single dark theme; do not add light-theme logic.
- No em dashes or en dashes in code/comments/copy - use hyphens.
- Commit author email for this repo: `4742780+tylerc515@users.noreply.github.com` (already set as local `user.email`).
- Run tests with `QT_QPA_PLATFORM=offscreen` so PyQt6 tests do not hang.
- Full suite must stay at 215+ passing on `feature/visual-redesign`.
- No behavior change to the download / install / install-later flow or the updater backend.

---

### Task 1: Add reusable `variant="success"` button style to the design system

**Files:**
- Modify: `app/design/tokens.py` (add `Color.SUCCESS_HOVER`)
- Modify: `app/styles.py` (add `QPushButton[variant="success"]` rules in `build_stylesheet`)
- Test: `tests/test_styles.py`

**Interfaces:**
- Produces: a global QSS rule so any `QPushButton` with `setProperty("variant", "success")` renders as a green primary button (`Color.SUCCESS`, hover `Color.SUCCESS_HOVER`). Consumed by Task 2's Install button.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_styles.py`:

```python
def test_build_stylesheet_has_success_variant_button():
    from app.styles import build_stylesheet
    qss = build_stylesheet("dark")
    assert 'QPushButton[variant="success"]' in qss
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_styles.py::test_build_stylesheet_has_success_variant_button -v`
Expected: FAIL (rule not present).

- [ ] **Step 3: Add the SUCCESS_HOVER token**

In `app/design/tokens.py`, under the `# Semantic` block of `class Color`, add `SUCCESS_HOVER` directly after `SUCCESS`:

```python
    # Semantic
    SUCCESS = "#00B050"
    SUCCESS_HOVER = "#009a45"
    WARNING = "#f4b13b"
    DANGER = "#ef4444"
```

- [ ] **Step 4: Add the success button rules**

In `app/styles.py` `build_stylesheet`, immediately after the existing `QPushButton[accent="true"]:disabled { ... }` rule (around line 137) and before `QPushButton[flat="true"]`, insert:

```python
QPushButton[variant="success"] {{
    background-color: {Color.SUCCESS};
    color: {Color.TEXT_PRIMARY};
    font-weight: 600;
    font-size: {FontSize.SECTION}px;
    padding: {Spacing.MD}px {Spacing.XXL}px;
    border: none;
    border-radius: {Radius.BUTTON}px;
}}

QPushButton[variant="success"]:hover {{
    background-color: {Color.SUCCESS_HOVER};
}}
```

- [ ] **Step 5: Run the styles tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_styles.py -v`
Expected: PASS - the new test passes, and the existing `test_build_stylesheet_contains_no_stray_hex_outside_tokens` still passes because `SUCCESS_HOVER` is now a defined `Color` token.

- [ ] **Step 6: Commit**

```bash
git add app/design/tokens.py app/styles.py tests/test_styles.py
git commit -m "Add reusable success-variant button style to design system"
```

---

### Task 2: Restyle update_dialog.py onto tokens and apply polish

**Files:**
- Modify: `app/widgets/update_dialog.py` (remove hardcoded palette, use tokens + properties)
- Test: `tests/test_update_dialog.py`

**Interfaces:**
- Consumes: `Color`, `FontSize`, `Radius`, `Spacing`, `FONT_FAMILY` from `app.design.tokens`; the `variant="success"` rule from Task 1.
- Produces: no new public API; `UpdateDialog` and `_MarkdownConverter` keep their existing signatures.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_update_dialog.py` (top of file, add imports; the module currently only imports `_MarkdownConverter` indirectly):

```python
import re
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_update_dialog_module_has_no_hardcoded_hex():
    src = Path(__file__).resolve().parent.parent / "app" / "widgets" / "update_dialog.py"
    text = src.read_text(encoding="utf-8")
    hexes = re.findall(r"#[0-9A-Fa-f]{6}\b", text)
    assert hexes == [], f"hardcoded hex literals remain in update_dialog.py: {hexes}"


def test_update_dialog_instantiates_and_uses_token_properties():
    from app.updater import UpdateCheckResult
    from app.widgets.update_dialog import UpdateDialog

    info = UpdateCheckResult(
        update_available=True,
        current_version="2.2.4",
        latest_version="2.3.0",
        release_notes="## What's New\n- **Item** one\n- item two",
        download_url="https://example.invalid/DATOToolkit_v2.3.0.exe",
        release_url="https://example.invalid/release",
        published_at="2026-07-15T00:00:00Z",
    )
    dlg = UpdateDialog(info)
    assert dlg._download_btn.property("accent") == "true"
    assert dlg._install_btn.property("variant") == "success"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_update_dialog.py::test_update_dialog_module_has_no_hardcoded_hex tests/test_update_dialog.py::test_update_dialog_instantiates_and_uses_token_properties -v`
Expected: FAIL - the no-hex test fails (8 constants + inline hex present); the instantiation test fails (`_download_btn` has no `accent` property yet).

- [ ] **Step 3: Replace imports and delete the hardcoded constants**

In `app/widgets/update_dialog.py`, add the token import after the existing `from app.logo import get_pixmap` line:

```python
from app.design.tokens import Color, FONT_FAMILY, FontSize, Radius, Spacing
```

Delete these eight lines entirely (lines 47-54):

```python
_BG = "#1a1a2e"
_SURFACE = "#16213e"
_BORDER = "#2c3759"
_NOTES_BG = "#0d1117"
_NOTES_TEXT = "#eaeaea"
_MUTED = "#9aa0b4"
_ACCENT_RED = "#e94560"
_ACCENT_GREEN = "#00B050"
```

- [ ] **Step 4: Tokenize the markdown converter**

In `_MarkdownConverter.to_html`, replace the heading line's inline style. Change:

```python
                parts.append(
                    f'<h3 style="color:{_NOTES_TEXT};font-size:12pt;'
                    f'font-weight:bold;margin-top:8px;margin-bottom:4px;">'
                    f"{heading}</h3>"
                )
```

to:

```python
                parts.append(
                    f'<h3 style="color:{Color.TEXT_PRIMARY};font-size:{FontSize.SECTION}px;'
                    f'font-weight:bold;margin-top:8px;margin-bottom:4px;">'
                    f"{heading}</h3>"
                )
```

- [ ] **Step 5: Restyle `__init__` (background + height polish)**

Replace the two size/style lines in `__init__`. Change `self.setFixedSize(620, 520)` to `self.setFixedSize(620, 560)`, change the stylesheet line to use the token, and update the centering math. The block becomes:

```python
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(620, 560)
        self.setStyleSheet(f"QDialog {{ background-color: {Color.PAGE_BG}; }}")
        self.setModal(True)

        if parent is not None:
            g = parent.geometry()
            self.move(g.x() + (g.width() - 620) // 2, g.y() + (g.height() - 560) // 2)
```

- [ ] **Step 6: Restyle `_build_header` (bands, labels, close hover polish)**

Replace the styled lines in `_build_header`:

```python
        header.setStyleSheet(
            f"QFrame {{ background-color: {Color.SIDEBAR_BG}; "
            f"border-bottom: 1px solid {Color.BORDER}; }}"
        )
```

```python
        title_lbl.setStyleSheet(
            f"font-size: {FontSize.PAGE_TITLE}px; font-weight: 600; color: {Color.TEXT_PRIMARY};"
        )
```

```python
        ver_lbl.setStyleSheet(f"font-size: {FontSize.BODY}px; color: {Color.TEXT_MUTED};")
```

```python
            date_lbl.setStyleSheet(f"font-size: {FontSize.SMALL}px; color: {Color.TEXT_MUTED};")
```

```python
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"color: {Color.TEXT_MUTED}; font-size: {FontSize.PAGE_TITLE}px; }}"
            f"QPushButton:hover {{ color: {Color.TEXT_PRIMARY}; }}"
        )
```

- [ ] **Step 7: Restyle `_build_notes_section`**

Replace the label and browser styling:

```python
        label.setStyleSheet(
            f"font-size: {FontSize.LABEL}px; font-weight: bold; color: {Color.TEXT_MUTED};"
        )
```

```python
        self._notes_browser.setStyleSheet(
            f"QTextBrowser {{ background: {Color.INPUT_BG}; color: {Color.TEXT_PRIMARY}; "
            f"border: 1px solid {Color.BORDER}; border-radius: {Radius.CARD}px; "
            f"padding: {Spacing.MD}px; font-family: '{FONT_FAMILY}'; font-size: {FontSize.BODY}px; }}"
        )
```

(Remove the two `QScrollBar` lines from the old browser stylesheet - the global QSS themes the scrollbar.)

- [ ] **Step 8: Restyle `_build_install_section`**

```python
        card.setStyleSheet(
            f"QFrame {{ background-color: {Color.SIDEBAR_BG}; "
            f"border-top: 1px solid {Color.BORDER}; border-bottom: 1px solid {Color.BORDER}; }}"
        )
```

```python
        loc_lbl.setStyleSheet(f"color: {Color.TEXT_PRIMARY};")
```

```python
        fn_lbl.setStyleSheet(f"color: {Color.TEXT_PRIMARY};")
```

```python
        self._filename_edit.setStyleSheet(f"color: {Color.TEXT_MUTED};")
```

```python
        self._remove_checkbox.setStyleSheet(f"color: {Color.TEXT_PRIMARY};")
```

```python
        helper.setStyleSheet(
            f"font-size: {FontSize.LABEL}px; font-style: italic; color: {Color.TEXT_MUTED};"
        )
```

- [ ] **Step 9: Restyle `_build_progress_section` (drop inline progress-bar + cancel color)**

```python
        self._progress_label.setStyleSheet(f"color: {Color.TEXT_PRIMARY};")
```

Delete the entire `self._progress_bar.setStyleSheet(...)` call (two lines) so the bar uses the global `QProgressBar` rule (chunk is `Color.ACCENT`).

```python
        self._speed_label.setStyleSheet(f"font-size: {FontSize.LABEL}px; color: {Color.TEXT_MUTED};")
```

For the cancel button, keep the `flat` property and delete its inline color override. The block becomes:

```python
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("flat", "true")
        self._cancel_btn.clicked.connect(self._on_cancel_download)
        cancel_row.addWidget(self._cancel_btn)
```

- [ ] **Step 10: Restyle `_build_action_section` (accent + success buttons, flat cleanup)**

Download button - replace inline stylesheet with the accent property:

```python
        self._download_btn = QPushButton("Download & Install")
        self._download_btn.setProperty("accent", "true")
        self._download_btn.clicked.connect(self._on_download_clicked)
        layout.addWidget(self._download_btn)
```

Install button - use the success variant:

```python
        self._install_btn = QPushButton("Install Now & Restart")
        self._install_btn.setProperty("variant", "success")
        self._install_btn.clicked.connect(self._on_install_now)
        self._install_btn.setVisible(False)
        layout.addWidget(self._install_btn)
```

View / Later buttons - keep `flat`, drop inline color:

```python
        view_btn = QPushButton("View on GitHub")
        view_btn.setProperty("flat", "true")
        view_btn.clicked.connect(self._open_github)
        bottom_row.addWidget(view_btn)
        bottom_row.addStretch(1)
        self._later_btn = QPushButton("Install Later")
        self._later_btn.setProperty("flat", "true")
        self._later_btn.clicked.connect(self._on_install_later)
        self._later_btn.setVisible(False)
        bottom_row.addWidget(self._later_btn)
```

- [ ] **Step 11: Run the full update-dialog + styles tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_update_dialog.py tests/test_styles.py -v`
Expected: PASS - the 6 markdown tests, the new no-hex test, and the instantiation test all pass.

- [ ] **Step 12: Run the whole suite**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest -q`
Expected: PASS at 217+ (215 prior + 2 new; Task 1 added 1 more).

- [ ] **Step 13: Visual check**

Run `python main.py`, open the update dialog path in dev if reachable, or capture the dialog widget in-process. Confirm: dark page background, blue "Download & Install", green "Install Now & Restart", neutral close-hover, no leftover blue-purple/red. Hand the compiled-exe look to Tyler (no safe automated OS-level exe capture; see 2026-07-01 session note).

- [ ] **Step 14: Commit**

```bash
git add app/widgets/update_dialog.py tests/test_update_dialog.py
git commit -m "Restyle update dialog onto design tokens with UX polish"
```

---

## Self-Review

**Spec coverage:**
- Token migration (all 8 constants + inline styles) - Task 2 Steps 3-10. Covered.
- `variant="success"` reusable rule - Task 1. Covered.
- Polish 1 (blue primary) - Task 2 Step 10. Polish 2 (neutral close hover) - Step 6. Polish 3 (success button) - Task 1 + Step 10. Polish 4 (height 520->560) - Step 5. Polish 5 (flat cleanup) - Steps 9-10. Covered.
- Markdown tokenization keeping tags - Step 4; existing tag-based tests remain green. Covered.
- Tests extend existing files - Task 1 (styles), Task 2 (update_dialog). Covered.
- No behavior change - only styling lines touched; all `_on_*` handlers untouched. Covered.

**Placeholder scan:** No TBD/TODO; every code step shows concrete code. The only deferred value (final height) is set to a concrete 560 with a visual confirmation step.

**Type consistency:** `variant="success"` string property is set in Task 2 Step 10 and asserted in Task 2 Step 1; the rule producing it is Task 1 Step 4. `Color.SUCCESS_HOVER` defined Task 1 Step 3, used Task 1 Step 4. `UpdateCheckResult` fields match `app/updater.py`. `_qapp` module-level pattern matches `tests/test_components.py`.
