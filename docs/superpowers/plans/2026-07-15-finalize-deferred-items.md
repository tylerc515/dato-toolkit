# Finalize Deferred Redesign Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the three deferred redesign items - retire the `color()` shim, fix the F1 help-panel toggle, and three minor cleanups - so `feature/visual-redesign` is fully finished before merge.

**Architecture:** All styling flows from `app.design.tokens`. The `color()` shim in `app/styles.py` maps legacy palette keys to those tokens; this plan migrates its remaining callers to the tokens directly and deletes it. F1 is fixed by replacing a fragile hardcoded page-index dict with an attribute lookup.

**Tech Stack:** Python 3.14, PyQt6, pytest (Qt offscreen).

## Global Constraints

- No hex color, pixel, or font-size literal outside `app/design/tokens.py`.
- Single dark theme; no light-theme logic. Do not remove `set_active_theme`/`get_active_theme`/`THEME_*` - `main.py` uses them.
- No em dashes or en dashes in code/comments - use hyphens.
- Commit author email: `4742780+tylerc515@users.noreply.github.com` (already the repo's local `user.email`).
- Run tests with `QT_QPA_PLATFORM=offscreen`.
- Full suite must stay green (currently 218) on `feature/visual-redesign`.
- The `color()` -> token migration is value-identical (1:1 per the map below); no pixel/visual change is intended.

Legacy-key -> token map (from `_LEGACY_COLOR_MAP`, for reference in Task 1):
`border`->`Color.BORDER`, `muted_text`->`Color.TEXT_MUTED`, `text`->`Color.TEXT_PRIMARY`, `warning`->`Color.WARNING`, `success`->`Color.SUCCESS`, `error`->`Color.DANGER`, `highlight`->`Color.ACCENT`, `surface`->`Color.CARD_BG`.

---

### Task 1: Retire the `color()` shim

**Files:**
- Modify: `app/window.py`, `app/pages/batch_page.py`, `app/pages/converter_page.py`, `app/pages/projects_page.py` (migrate call sites)
- Modify: `app/styles.py` (delete shim + map)
- Test: `tests/test_styles.py`

**Interfaces:**
- Consumes: `Color` tokens from `app.design.tokens`.
- Produces: `app/styles.py` no longer exports `color` or `_LEGACY_COLOR_MAP`.

- [ ] **Step 1: Write the failing guard test**

Add to `tests/test_styles.py`:

```python
import re
from pathlib import Path


def test_no_color_shim_calls_remain():
    app_dir = Path(__file__).resolve().parent.parent / "app"
    offenders = []
    for py in app_dir.rglob("*.py"):
        if re.search(r"\bcolor\(['\"]", py.read_text(encoding="utf-8")):
            offenders.append(str(py.relative_to(app_dir)))
    assert offenders == [], f"color() shim still called in: {offenders}"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_styles.py::test_no_color_shim_calls_remain -v`
Expected: FAIL - offenders list is non-empty (window/batch/converter/projects).

- [ ] **Step 3: Migrate `app/window.py`**

Delete the import line `from app.styles import color` (line ~52). `Color` is already imported. Then replace:
- `{color('border')}` -> `{Color.BORDER}` (in the `QFrame#AppFrame` border stylesheet)
- `{color('warning')}` -> `{Color.WARNING}` (update_available_label)
- `{color('text')}` -> `{Color.TEXT_PRIMARY}`
- `color("warning")` -> `Color.WARNING` (the `set_color(...)` call)
- `color("success")` -> `Color.SUCCESS` (the `set_color(...)` call)

- [ ] **Step 4: Migrate `app/pages/batch_page.py`**

Change the import line `from app.styles import apply_card_shadow, color` to `from app.styles import apply_card_shadow`, and add a new import line `from app.design.tokens import Color`. Then replace:
- `{color('muted_text')}` -> `{Color.TEXT_MUTED}`
- `{color('error')}` -> `{Color.DANGER}` (three occurrences: the status error line, the card border, the name label)
- `{color('warning')}` -> `{Color.WARNING}`
- `{color('success')}` -> `{Color.SUCCESS}`

- [ ] **Step 5: Migrate `app/pages/converter_page.py`**

Delete the import line `from app.styles import color` (`Color` is already imported at the line above it). Then replace:
- `{color('border')}` -> `{Color.BORDER}`
- `{color('highlight')}` -> `{Color.ACCENT}` (two occurrences: the drop-zone `border-color` hover and the active-state border)
- `{color('muted_text')}` -> `{Color.TEXT_MUTED}`
- `color("success") if success else color("error")` -> `Color.SUCCESS if success else Color.DANGER`

- [ ] **Step 6: Migrate `app/pages/projects_page.py`**

Change `from app.styles import apply_card_shadow, color` to `from app.styles import apply_card_shadow`, and add `from app.design.tokens import Color`. Then replace:
- `{color('muted_text')}` -> `{Color.TEXT_MUTED}`

- [ ] **Step 7: Delete the shim from `app/styles.py`**

Remove the `_LEGACY_COLOR_MAP` dict definition and the `color()` function entirely. Keep `set_active_theme`, `get_active_theme`, `DEFAULT_THEME`, `THEME_*`, `build_stylesheet`, and `apply_card_shadow`. Update the module docstring: delete the paragraph describing the `color()` transitional shim.

- [ ] **Step 8: Delete the obsolete legacy-color test**

In `tests/test_styles.py`, delete `test_legacy_color_keys_still_resolve` (it imports and asserts on `color`, which no longer exists).

- [ ] **Step 9: Run styles tests + full suite**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_styles.py -v`
Expected: PASS - guard test passes, no import errors.
Run: `QT_QPA_PLATFORM=offscreen python -m pytest -q`
Expected: PASS - full suite green (218 minus the one deleted test, plus the one new = 218).

- [ ] **Step 10: Commit**

```bash
git add app/window.py app/pages/batch_page.py app/pages/converter_page.py app/pages/projects_page.py app/styles.py tests/test_styles.py
git commit -m "Retire the transitional color() shim, migrate callers to tokens"
```

---

### Task 2: Fix the F1 help-panel toggle

**Files:**
- Modify: `app/window.py` (`_toggle_current_help`)
- Test: `tests/test_window_sidebar_wiring.py`

**Interfaces:**
- Consumes: `self.stack.currentWidget()`, each page's `help_panel` attribute (a `HelpPanel` with `toggle()` and an `_expanded` bool).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_window_sidebar_wiring.py` (it already has the `_make_window()` helper and module-level `_qapp`):

```python
def test_f1_toggles_help_on_history_page():
    win = _make_window()
    win._go_to_history()
    assert win.history_page.help_panel._expanded is False
    win._toggle_current_help()
    assert win.history_page.help_panel._expanded is True


def test_f1_toggles_help_on_settings_page():
    win = _make_window()
    win._go_to_settings()
    assert win.settings_page.help_panel._expanded is False
    win._toggle_current_help()
    assert win.settings_page.help_panel._expanded is True
```

- [ ] **Step 2: Run to verify failure**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_window_sidebar_wiring.py::test_f1_toggles_help_on_history_page tests/test_window_sidebar_wiring.py::test_f1_toggles_help_on_settings_page -v`
Expected: FAIL - `_expanded` stays False because History/Settings are not in the current hardcoded dict.

- [ ] **Step 3: Replace `_toggle_current_help`**

In `app/window.py`, replace the entire `_toggle_current_help` method body (the hardcoded index->page dict) with:

```python
    def _toggle_current_help(self) -> None:
        panel = getattr(self.stack.currentWidget(), "help_panel", None)
        if panel is not None:
            panel.toggle()
```

- [ ] **Step 4: Run to verify pass**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_window_sidebar_wiring.py -v`
Expected: PASS - both new tests pass; existing window tests still pass.

- [ ] **Step 5: Commit**

```bash
git add app/window.py tests/test_window_sidebar_wiring.py
git commit -m "Fix F1 to toggle help on every page via currentWidget lookup"
```

---

### Task 3: Minor cleanups (dead import, disabled-state QSS, version bump)

**Files:**
- Modify: `app/pages/dashboard_page.py` (dead import)
- Modify: `app/styles.py` (`build_stylesheet` disabled rules)
- Modify: `pyproject.toml` (version)
- Test: `tests/test_styles.py`

**Interfaces:**
- Consumes: `Color.TEXT_MUTED`, `Color.CARD_BG`, `Color.BORDER` (existing tokens).

- [ ] **Step 1: Write failing tests**

Add to `tests/test_styles.py`:

```python
def test_build_stylesheet_has_disabled_state_rules():
    from app.styles import build_stylesheet
    qss = build_stylesheet("dark")
    assert "QComboBox:disabled" in qss
    assert "QCheckBox::indicator:disabled" in qss


def test_pyproject_version_matches_app_version():
    from pathlib import Path
    from app import __version__
    text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in text
```

- [ ] **Step 2: Run to verify failure**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_styles.py::test_build_stylesheet_has_disabled_state_rules tests/test_styles.py::test_pyproject_version_matches_app_version -v`
Expected: FAIL - no disabled rules yet; pyproject still says `2.0.0` while `app.__version__` is `2.3.0`.

- [ ] **Step 3: Add disabled-state rules to `build_stylesheet`**

In `app/styles.py`, in the `build_stylesheet` QSS, add after the `QLineEdit:focus, QTextEdit:focus, QComboBox:focus { ... }` rule:

```python
QComboBox:disabled {{
    color: {Color.TEXT_MUTED};
    background-color: {Color.CARD_BG};
}}
```

And after the `QCheckBox::indicator:checked { ... }` rule:

```python
QCheckBox:disabled {{
    color: {Color.TEXT_MUTED};
}}

QCheckBox::indicator:disabled {{
    background: {Color.CARD_BG};
    border: 1px solid {Color.BORDER};
}}
```

- [ ] **Step 4: Remove the dead import**

In `app/pages/dashboard_page.py`, change:
`from app.history import HistoryEntry, NEVER_TEXT, format_timestamp, load_history`
to:
`from app.history import HistoryEntry, format_timestamp, load_history`

- [ ] **Step 5: Bump the version**

In `pyproject.toml`, change `version = "2.0.0"` to `version = "2.3.0"`.

- [ ] **Step 6: Run styles tests + full suite**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_styles.py -v`
Expected: PASS - both new tests pass; existing `test_build_stylesheet_contains_no_stray_hex_outside_tokens` still passes (only token values used).
Run: `QT_QPA_PLATFORM=offscreen python -m pytest -q`
Expected: PASS - full suite green.

- [ ] **Step 7: Commit**

```bash
git add app/pages/dashboard_page.py app/styles.py pyproject.toml tests/test_styles.py
git commit -m "Add disabled-state QSS, drop dead import, sync pyproject version"
```

---

## Self-Review

**Spec coverage:**
- Bucket 1 (shim retirement) - Task 1: all 4 caller files migrated per the map, shim + `_LEGACY_COLOR_MAP` deleted, legacy test removed, guard test added. Covered.
- Bucket 2 (F1 fix) - Task 2: `getattr(currentWidget, "help_panel")` replacement + History/Settings tests. Covered.
- Bucket 3 (minor) - Task 3: dead `NEVER_TEXT` import removed, `QComboBox:disabled` + `QCheckBox::indicator:disabled` rules added, `pyproject.toml` bumped to 2.3.0, tests for the last two. Covered.

**Placeholder scan:** No TBD/TODO. Every migration lists its exact `color('key')` -> `Color.TOKEN` substitution and exact import edits. Disabled QSS and F1 body shown in full.

**Type consistency:** `_toggle_current_help` defined in Task 2 Step 3 matches the test in Step 1 (`_expanded` bool asserted). Tokens used in Task 1/3 (`Color.BORDER`, `TEXT_MUTED`, `TEXT_PRIMARY`, `WARNING`, `SUCCESS`, `DANGER`, `ACCENT`, `CARD_BG`) all exist in `app/design/tokens.py`. Guard-test regex `\bcolor\(['\"]` matches shim calls but not `set_color(`, `QColor(`, or `background-color`.
