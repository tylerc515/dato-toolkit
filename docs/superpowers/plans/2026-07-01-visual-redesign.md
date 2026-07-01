# DATO Toolkit Visual Redesign (TRACE-Inspired Design System) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace DATO Toolkit's entire visual design (dark navy `#1a1a2e` + red-pink `#e94560` theme, top header nav) with a TRACE-inspired design system (near-black surfaces, blue accent, left sidebar nav, a shared token file, and a `FixedGridTable` component that eliminates the column-alignment bug class seen on the converter page).

**Architecture:** A new `app/design/` package (`tokens.py`, `icons.py`) becomes the single source of truth for color/spacing/radius/type. `app/widgets/components.py` provides shared building blocks (`PrimaryButton`, `SecondaryButton`, `Card`, `StatCard`, `StatusBadge`, `FixedGridTable`) built from those tokens. `app/styles.py` is rewritten to emit QSS from tokens, keeping a transitional backward-compatible `color()` shim so pages not yet rebuilt in later phases don't break. Each subsequent phase rebuilds one page (or the app shell) to consume the new components, preserving 100% of existing functionality.

**Tech Stack:** PyQt6, qtawesome (new dependency, Phosphor icon set via `ph.` prefix), pytest + pytest-qt.

## Global Constraints

- Branch: all work happens on `feature/visual-redesign`, branched from `feature/data-converter` (already done — see "Branch setup already complete" below). Never commit to `feature/data-converter` or `main` from this plan.
- No hex color literal, pixel spacing/radius value, or font size literal may appear anywhere in `app/` outside `app/design/tokens.py`. Phase 9 greps for violations.
- This pass ships ONE theme (the new dark TRACE-inspired palette). No light-mode work. `THEME_LIGHT`/theme-switching machinery in `app/styles.py` and `app/settings.py` stays present at the function-signature level (so call sites don't break) but is not developed further — see Task 2's transitional design.
- Every phase must preserve 100% of existing functionality. This is a visual/structural rebuild, never a behavior change, except where a phase explicitly says otherwise (there are no such exceptions in this plan).
- Commit after every phase, not one giant commit at the end (`git add`, `git commit`, `git push origin feature/visual-redesign`).
- Write a session note to the Obsidian vault (`01-Projects/DATO-Toolkit/sessions/`) after completing each phase, not just at the end.
- Verified fact (checked 2026-07-01 in this environment, `qtawesome==1.4.2`): the `ph.` (Phosphor) prefix works, but two icon names from the original spec don't resolve and must use substitutes:
  - `ph.mail` → does not exist. Use `ph.envelope-simple` instead (confirmed resolves).
  - `ph.file-spreadsheet` → does not exist. Use `ph.table` instead (confirmed resolves) for the Tracksheet nav icon.
  - All other requested icon names (`house`, `arrows-left-right`, `clock-counter-clockwise`, `gear`, `caret-down`, `caret-right`, `play`, `folder`, `upload-simple`, `download-simple`, `trash`, `pencil-simple`, `check`, `x`, `plus`, `magnifying-glass`, `warning-circle`, `user-circle`) confirmed to resolve under `ph.` as-is.
- `qtawesome` was installed into the active environment during planning to verify the above (`pip install qtawesome`, version 1.4.2 resolved). Task 3 adds it to `requirements.txt` formally as part of the plan (not yet committed).

## Branch setup already complete

```bash
git checkout feature/data-converter
git pull origin feature/data-converter
git checkout -b feature/visual-redesign
```
Done — current branch is `feature/visual-redesign`, clean, branched from `feature/data-converter` at commit `4132c87`.

---

# PHASE 1 — Design token foundation

## Task 1: Design tokens (`app/design/tokens.py`)

**Files:**
- Create: `app/design/__init__.py` (empty package marker)
- Create: `app/design/tokens.py`
- Test: `tests/test_tokens.py`

**Interfaces:**
- Produces: `Color`, `Spacing`, `Radius`, `FontSize` classes and `FONT_FAMILY` constant, importable as `from app.design.tokens import Color, Spacing, Radius, FontSize, FONT_FAMILY`. Every later task in this plan imports from here.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tokens.py
"""Tests for the design token source of truth."""
from __future__ import annotations


def test_color_tokens_have_expected_values():
    from app.design.tokens import Color
    assert Color.PAGE_BG == "#0c0c0e"
    assert Color.SIDEBAR_BG == "#131316"
    assert Color.CARD_BG == "#151517"
    assert Color.TABLE_HEADER_BG == "#1a1a1d"
    assert Color.INPUT_BG == "#0f0f11"
    assert Color.BORDER == "#232326"
    assert Color.BORDER_STRONG == "#2f2f34"
    assert Color.TEXT_PRIMARY == "#f4f4f5"
    assert Color.TEXT_SECONDARY == "#d4d4d8"
    assert Color.TEXT_MUTED == "#8b8b90"
    assert Color.TEXT_FAINT == "#6b6b70"
    assert Color.ACCENT == "#2563eb"
    assert Color.ACCENT_HOVER == "#1d4ed8"
    assert Color.ACCENT_TEXT == "#7fb0ff"
    assert Color.ACCENT_BG_TINT == "#1a2c50"
    assert Color.SUCCESS == "#00B050"
    assert Color.WARNING == "#f4b13b"
    assert Color.DANGER == "#ef4444"


def test_spacing_tokens_have_expected_values():
    from app.design.tokens import Spacing
    assert (Spacing.XS, Spacing.SM, Spacing.MD, Spacing.LG, Spacing.XL, Spacing.XXL, Spacing.XXXL) == (
        4, 8, 12, 16, 20, 24, 32,
    )


def test_radius_tokens_have_expected_values():
    from app.design.tokens import Radius
    assert (Radius.INPUT, Radius.BUTTON, Radius.CARD, Radius.SIDEBAR_ITEM, Radius.PILL) == (
        7, 8, 10, 8, 999,
    )


def test_font_size_tokens_have_expected_values():
    from app.design.tokens import FontSize
    assert (FontSize.LABEL, FontSize.SMALL, FontSize.BODY, FontSize.SECTION, FontSize.PAGE_TITLE, FontSize.STAT_NUMBER) == (
        11, 12, 13, 14, 18, 22,
    )


def test_font_family_token():
    from app.design.tokens import FONT_FAMILY
    assert FONT_FAMILY == "Segoe UI"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tokens.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.design'`

- [ ] **Step 3: Write minimal implementation**

Create `app/design/__init__.py` (empty file).

```python
# app/design/tokens.py
"""
Single source of truth for all colors, spacing, radius, and typography
in the app. No hex color, pixel spacing value, or font size should
appear as a literal anywhere else in the codebase - everything
references these constants.
"""


class Color:
    # Surfaces
    PAGE_BG = "#0c0c0e"
    SIDEBAR_BG = "#131316"
    CARD_BG = "#151517"
    TABLE_HEADER_BG = "#1a1a1d"
    INPUT_BG = "#0f0f11"

    # Borders
    BORDER = "#232326"
    BORDER_STRONG = "#2f2f34"

    # Text
    TEXT_PRIMARY = "#f4f4f5"
    TEXT_SECONDARY = "#d4d4d8"
    TEXT_MUTED = "#8b8b90"
    TEXT_FAINT = "#6b6b70"

    # Accent (blue - replaces the old red-pink brand accent everywhere)
    ACCENT = "#2563eb"
    ACCENT_HOVER = "#1d4ed8"
    ACCENT_TEXT = "#7fb0ff"
    ACCENT_BG_TINT = "#1a2c50"

    # Semantic
    SUCCESS = "#00B050"
    WARNING = "#f4b13b"
    DANGER = "#ef4444"


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24
    XXXL = 32


class Radius:
    INPUT = 7
    BUTTON = 8
    CARD = 10
    SIDEBAR_ITEM = 8
    PILL = 999


class FontSize:
    LABEL = 11
    SMALL = 12
    BODY = 13
    SECTION = 14
    PAGE_TITLE = 18
    STAT_NUMBER = 22


FONT_FAMILY = "Segoe UI"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tokens.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add app/design/__init__.py app/design/tokens.py tests/test_tokens.py
git commit -m "Phase 1a: Add design token source of truth (app/design/tokens.py)"
```

---

## Task 2: Rewrite `app/styles.py` to consume tokens, with a transitional legacy shim

**Why the shim:** Phases 3-8 rebuild one page per phase. Until a page is rebuilt, it still calls the *old* `color("surface")`-style lookups (confirmed call sites below). If `color()` is deleted or its keys renamed in Phase 1, every unmigrated page crashes the moment Phase 2 makes it reachable again. So `color()` stays, remapped to point at the new tokens, and gets deleted in Phase 9 once a grep confirms no callers remain.

**Confirmed legacy keys actually called anywhere in `app/` today** (checked via repo-wide grep before writing this plan): `background`, `border`, `chrome_hover`, `error`, `muted_text`, `success`, `text`, `warning`, `accent`, `highlight`, `surface`. Every one of these must keep resolving.

**Files:**
- Modify: `app/styles.py` (full rewrite, `app/styles.py:1-252` today)
- Test: `tests/test_styles.py` (new)

**Interfaces:**
- Consumes: `Color` from `app.design.tokens` (Task 1).
- Produces: `color(name: str, theme: str | None = None) -> str` (signature unchanged, values remapped), `build_stylesheet(theme: str) -> str` (signature unchanged, body rewritten to emit token-driven QSS), `set_active_theme`, `get_active_theme`, `THEME_DARK`, `THEME_LIGHT`, `THEME_NAMES`, `DEFAULT_THEME` (all kept as no-op-compatible shims so `main.py` and `app/settings.py` don't need changes in this phase), `apply_card_shadow(widget)` (unchanged, no token dependency).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_styles.py
"""Tests for the token-driven stylesheet and the transitional color() shim."""
from __future__ import annotations

import re


def test_legacy_color_keys_still_resolve():
    from app.styles import color
    from app.design.tokens import Color as T
    assert color("surface") == T.CARD_BG
    assert color("border") == T.BORDER
    assert color("highlight") == T.ACCENT
    assert color("accent") == T.CARD_BG
    assert color("text") == T.TEXT_PRIMARY
    assert color("muted_text") == T.TEXT_MUTED
    assert color("success") == T.SUCCESS
    assert color("warning") == T.WARNING
    assert color("error") == T.DANGER
    assert color("background") == T.PAGE_BG
    assert color("chrome_hover") == T.BORDER_STRONG


def test_build_stylesheet_contains_no_old_palette_hex():
    from app.styles import build_stylesheet
    qss = build_stylesheet("dark")
    for old_hex in ("#1a1a2e", "#16213e", "#e94560", "#0f3460"):
        assert old_hex not in qss, f"Old palette color {old_hex} leaked into new stylesheet"


def test_build_stylesheet_contains_no_stray_hex_outside_tokens():
    """Every hex literal in the generated QSS must trace back to a Color token value."""
    from app.styles import build_stylesheet
    from app.design.tokens import Color as T
    qss = build_stylesheet("dark")
    token_hexes = {v for k, v in vars(T).items() if not k.startswith("_")}
    found_hexes = set(re.findall(r"#[0-9a-fA-F]{6}", qss))
    stray = found_hexes - token_hexes
    assert not stray, f"QSS contains hex values not defined in Color tokens: {stray}"


def test_build_stylesheet_same_regardless_of_theme_arg():
    """This pass ships one theme; build_stylesheet ignores the theme argument's palette."""
    from app.styles import build_stylesheet
    assert build_stylesheet("dark") == build_stylesheet("light")


def test_set_and_get_active_theme_still_work():
    from app.styles import set_active_theme, get_active_theme, DEFAULT_THEME
    set_active_theme("light")
    assert get_active_theme() == "light"
    set_active_theme(DEFAULT_THEME)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_styles.py -v`
Expected: FAIL — old hex values still present, legacy keys still return old palette values.

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `app/styles.py`:

```python
"""Theme palette and stylesheet generation for DATO Toolkit.

This app ships a single visual theme (the TRACE-inspired dark palette
defined in app.design.tokens). THEME_LIGHT / theme-switching machinery
is kept at the function-signature level only, so app/settings.py and
main.py don't need changes in this pass - see docs/superpowers/plans/
2026-07-01-visual-redesign.md Task 2 for why. Light mode is future work.

The color() function is a TRANSITIONAL SHIM: it maps the old semantic
palette key names (used by pages not yet rebuilt in this redesign) onto
the new Color tokens, so unmigrated pages keep rendering correctly
during the phased rollout. Delete it once every page has been rebuilt
(Phase 9) and a grep confirms no callers remain.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from app.design.tokens import Color, FontSize, FONT_FAMILY, Radius, Spacing

THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_NAMES = (THEME_DARK, THEME_LIGHT)
DEFAULT_THEME = THEME_DARK

# TRANSITIONAL: old semantic key -> new token. See module docstring.
_LEGACY_COLOR_MAP: dict[str, str] = {
    "background": Color.PAGE_BG,
    "surface": Color.CARD_BG,
    "accent": Color.CARD_BG,
    "button_hover": Color.BORDER_STRONG,
    "button_pressed": Color.SIDEBAR_BG,
    "button_disabled_bg": Color.CARD_BG,
    "highlight": Color.ACCENT,
    "highlight_hover": Color.ACCENT_HOVER,
    "highlight_disabled_bg": Color.BORDER_STRONG,
    "text": Color.TEXT_PRIMARY,
    "muted_text": Color.TEXT_MUTED,
    "border": Color.BORDER,
    "success": Color.SUCCESS,
    "warning": Color.WARNING,
    "error": Color.DANGER,
    "chrome_hover": Color.BORDER_STRONG,
}

_active_theme = DEFAULT_THEME


def set_active_theme(theme: str) -> None:
    """Set the theme used by `color()` lookups for newly built widgets."""
    global _active_theme
    _active_theme = theme if theme in THEME_NAMES else DEFAULT_THEME


def get_active_theme() -> str:
    return _active_theme


def color(name: str, theme: str | None = None) -> str:
    """TRANSITIONAL: look up a legacy palette key, mapped to its new token."""
    return _LEGACY_COLOR_MAP[name]


def build_stylesheet(theme: str) -> str:
    """Build the application-wide QSS. `theme` is accepted for call-site
    compatibility but ignored - this pass ships a single dark theme."""
    return f"""
* {{
    font-family: "{FONT_FAMILY}", "Calibri", sans-serif;
    color: {Color.TEXT_PRIMARY};
}}

QMainWindow, QWidget {{
    background-color: {Color.PAGE_BG};
}}

QLabel {{
    background: transparent;
}}

QLabel[role="muted"] {{
    color: {Color.TEXT_MUTED};
}}

QLabel[role="heading"] {{
    font-size: {FontSize.PAGE_TITLE}px;
    font-weight: 600;
}}

QFrame[card="true"] {{
    background-color: {Color.CARD_BG};
    border-radius: {Radius.CARD}px;
    border: 1px solid {Color.BORDER};
}}

QPushButton {{
    background-color: {Color.CARD_BG};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.BORDER_STRONG};
    border-radius: {Radius.BUTTON}px;
    padding: {Spacing.SM}px {Spacing.LG}px;
    font-size: {FontSize.SECTION}px;
}}

QPushButton:hover {{
    background-color: {Color.BORDER_STRONG};
}}

QPushButton:pressed {{
    background-color: {Color.SIDEBAR_BG};
}}

QPushButton:disabled {{
    background-color: {Color.CARD_BG};
    color: {Color.TEXT_MUTED};
}}

QPushButton[accent="true"] {{
    background-color: {Color.ACCENT};
    color: {Color.TEXT_PRIMARY};
    font-weight: 600;
    font-size: {FontSize.SECTION}px;
    padding: {Spacing.MD}px {Spacing.XXL}px;
    border: none;
    border-radius: {Radius.BUTTON}px;
}}

QPushButton[accent="true"]:hover {{
    background-color: {Color.ACCENT_HOVER};
}}

QPushButton[accent="true"]:disabled {{
    background-color: {Color.BORDER_STRONG};
    color: {Color.TEXT_MUTED};
}}

QPushButton[flat="true"] {{
    background-color: transparent;
    border: 1px solid {Color.BORDER};
}}

QPushButton[flat="true"]:hover {{
    background-color: {Color.CARD_BG};
}}

QLineEdit, QTextEdit, QComboBox {{
    background-color: {Color.INPUT_BG};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.INPUT}px;
    padding: {Spacing.SM}px {Spacing.MD}px;
    selection-background-color: {Color.ACCENT};
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {Color.ACCENT};
}}

QListWidget {{
    background-color: {Color.CARD_BG};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.CARD}px;
    padding: {Spacing.SM}px;
}}

QListWidget::item {{
    background-color: {Color.INPUT_BG};
    border-radius: {Radius.BUTTON}px;
    padding: {Spacing.SM}px;
    margin: {Spacing.XS}px;
}}

QListWidget::item:selected {{
    background-color: {Color.ACCENT_BG_TINT};
    border: 1px solid {Color.ACCENT};
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: {Color.PAGE_BG};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {Color.BORDER_STRONG};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Color.ACCENT};
}}

QProgressBar {{
    background-color: {Color.CARD_BG};
    border: 1px solid {Color.BORDER};
    border-radius: {Radius.BUTTON}px;
    text-align: center;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {Color.ACCENT};
    border-radius: 7px;
}}

QStatusBar {{
    background-color: {Color.SIDEBAR_BG};
    color: {Color.TEXT_MUTED};
    border-top: 1px solid {Color.BORDER};
}}

QToolTip {{
    background-color: {Color.CARD_BG};
    color: {Color.TEXT_PRIMARY};
    border: 1px solid {Color.ACCENT};
    border-radius: 6px;
    padding: 4px 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {Color.BORDER};
    background: {Color.INPUT_BG};
}}

QCheckBox::indicator:checked {{
    background: {Color.ACCENT};
    border: 1px solid {Color.ACCENT};
}}
"""


def apply_card_shadow(widget: QWidget) -> None:
    """Apply a subtle drop shadow to a card-style widget."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(24)
    effect.setOffset(0, 4)
    effect.setColor(QColor(0, 0, 0, 160))
    widget.setGraphicsEffect(effect)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_styles.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the FULL suite to check for regressions from the color() key removals**

Run: `pytest -q`
Expected: PASS. Any failure here means some page calls a `color("...")` key not in `_LEGACY_COLOR_MAP` above — add the missing key (map it to the closest matching token) and re-run.

- [ ] **Step 6: Commit**

```bash
git add app/styles.py tests/test_styles.py
git commit -m "Phase 1b: Rewrite styles.py to consume design tokens, keep transitional color() shim"
```

---

## Task 3: Icon system (`app/design/icons.py`)

**Files:**
- Modify: `requirements.txt` (add `qtawesome`)
- Create: `app/design/icons.py`
- Test: `tests/test_icons.py`

**Interfaces:**
- Consumes: `Color` from `app.design.tokens`.
- Produces: `icon(name: str, color: str = Color.TEXT_MUTED, size: int | None = None) -> QIcon`, importable as `from app.design.icons import icon`.

- [ ] **Step 1: Add the dependency**

Add a line to `requirements.txt`:
```
qtawesome
```

Install: `pip install qtawesome` (already done during planning verification; re-run is a no-op if already installed).

- [ ] **Step 2: Write the failing test**

```python
# tests/test_icons.py
"""Tests for the qtawesome-based icon helper."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_icon_returns_non_null_qicon_for_known_names():
    from app.design.icons import icon
    # Every name actually used by the sidebar/components in this redesign,
    # confirmed to resolve under the ph. prefix (see plan Global Constraints
    # for the two substitutions: mail -> envelope-simple, file-spreadsheet -> table).
    names = [
        "house", "table", "envelope-simple", "arrows-left-right",
        "clock-counter-clockwise", "gear", "caret-down", "caret-right",
        "play", "folder", "upload-simple", "download-simple", "trash",
        "pencil-simple", "check", "x", "plus", "magnifying-glass",
        "warning-circle", "user-circle",
    ]
    for name in names:
        result = icon(name)
        assert not result.isNull(), f"icon({name!r}) returned a null QIcon"


def test_icon_accepts_custom_color():
    from app.design.icons import icon
    from app.design.tokens import Color
    result = icon("house", color=Color.ACCENT_TEXT)
    assert not result.isNull()


def test_icon_default_color_is_text_muted():
    import inspect
    from app.design.icons import icon
    from app.design.tokens import Color
    sig = inspect.signature(icon)
    assert sig.parameters["color"].default == Color.TEXT_MUTED
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_icons.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.design.icons'`

- [ ] **Step 4: Write minimal implementation**

```python
# app/design/icons.py
"""Icon helper wrapping qtawesome's Phosphor ("ph.") icon set.

Verified against qtawesome 1.4.2: the `ph.` prefix resolves for every
name used in this app EXCEPT `mail` and `file-spreadsheet`, which don't
exist in this version's Phosphor font map. Use `envelope-simple` and
`table` instead - see docs/superpowers/plans/2026-07-01-visual-redesign.md
Global Constraints for the full list of confirmed names.
"""

import qtawesome as qta
from PyQt6.QtGui import QIcon

from app.design.tokens import Color


def icon(name: str, color: str = Color.TEXT_MUTED, size: int | None = None) -> QIcon:
    """Return a QIcon for the given Phosphor icon name (without the
    'ph.' prefix - pass just 'house', 'gear', etc).
    Use color=Color.ACCENT_TEXT for active/selected states.
    """
    return qta.icon(f"ph.{name}", color=color)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_icons.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt app/design/icons.py tests/test_icons.py
git commit -m "Phase 1c: Add qtawesome icon system (app/design/icons.py)"
```

---

## Task 4: Reusable component widgets (`app/widgets/components.py`)

**Files:**
- Create: `app/widgets/components.py`
- Test: `tests/test_components.py`

**Interfaces:**
- Consumes: `Color`, `Spacing`, `Radius`, `FontSize` from `app.design.tokens`.
- Produces (used by every later phase): `PrimaryButton(text: str, parent=None)`, `SecondaryButton(text: str, parent=None)`, `Card(parent=None)` (a `QFrame` with a `QVBoxLayout` accessible as `.layout()`), `StatCard(label: str, value: str, value_color: str = Color.TEXT_PRIMARY, parent=None)` with a `set_value(value: str) -> None` method, `StatusBadge(text: str, semantic: str, parent=None)` where `semantic` is one of `"success" | "warning" | "danger"` with a `set_status(text: str, semantic: str) -> None` method, `FixedGridTable(columns: list[dict], parent=None)` with `add_row(values: list[QWidget]) -> None` and `clear_rows() -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_components.py
"""Tests for the shared component library built from design tokens."""
from __future__ import annotations

import sys

import pytest
from PyQt6.QtWidgets import QApplication, QLabel

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_primary_button_uses_accent_property():
    from app.widgets.components import PrimaryButton
    btn = PrimaryButton("Convert All")
    assert btn.text() == "Convert All"
    assert btn.property("accent") == "true"


def test_secondary_button_is_flat_styled():
    from app.widgets.components import SecondaryButton
    btn = SecondaryButton("Browse...")
    assert btn.text() == "Browse..."
    assert btn.property("flat") == "true"


def test_card_is_a_styled_frame_with_layout():
    from app.widgets.components import Card
    card = Card()
    assert card.property("card") == "true"
    assert card.layout() is not None
    label = QLabel("hello")
    card.layout().addWidget(label)
    assert card.layout().count() == 1


def test_stat_card_shows_label_and_value():
    from app.widgets.components import StatCard
    stat = StatCard("Files loaded", "3")
    assert stat._value_label.text() == "3"
    assert stat._label_label.text() == "Files loaded"


def test_stat_card_set_value_updates_display():
    from app.widgets.components import StatCard
    stat = StatCard("Files loaded", "0")
    stat.set_value("5")
    assert stat._value_label.text() == "5"


def test_stat_card_accepts_color_override():
    from app.widgets.components import StatCard
    from app.design.tokens import Color
    stat = StatCard("Flags needing review", "2", value_color=Color.WARNING)
    assert Color.WARNING in stat._value_label.styleSheet()


def test_status_badge_accepts_known_semantics():
    from app.widgets.components import StatusBadge
    for semantic in ("success", "warning", "danger"):
        badge = StatusBadge("Auto-mapped", semantic)
        assert badge.text() == "Auto-mapped"


def test_status_badge_rejects_unknown_semantic():
    from app.widgets.components import StatusBadge
    with pytest.raises(ValueError):
        StatusBadge("Bad", "not-a-real-semantic")


def test_status_badge_set_status_updates_text():
    from app.widgets.components import StatusBadge
    badge = StatusBadge("Needs mapping", "warning")
    badge.set_status("Auto-mapped", "success")
    assert badge.text() == "Auto-mapped"


def test_fixed_grid_table_requires_exactly_one_stretch_column():
    from app.widgets.components import FixedGridTable
    with pytest.raises(ValueError):
        FixedGridTable([{"label": "A", "width": 90}, {"label": "B", "width": 90}])
    with pytest.raises(ValueError):
        FixedGridTable([{"label": "A", "stretch": True}, {"label": "B", "stretch": True}])


def test_fixed_grid_table_header_and_row_share_column_count():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([
        {"label": "Code", "width": 90},
        {"label": "Description", "stretch": True},
        {"label": "Status", "width": 130},
    ])
    table.add_row([QLabel("NC"), QLabel("Not Clean"), QLabel("Auto-mapped")])
    table.add_row([QLabel("RF"), QLabel("Refractory"), QLabel("Auto-mapped")])
    # 1 header row + 2 data rows, 3 columns each = 9 grid items
    assert table._grid.count() == 9


def test_fixed_grid_table_fixed_columns_have_zero_stretch():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([
        {"label": "Code", "width": 90},
        {"label": "Description", "stretch": True},
    ])
    assert table._grid.columnStretch(0) == 0
    assert table._grid.columnStretch(1) == 1
    assert table._grid.columnMinimumWidth(0) == 90


def test_fixed_grid_table_clear_rows_keeps_header():
    from app.widgets.components import FixedGridTable
    table = FixedGridTable([{"label": "A", "width": 90}, {"label": "B", "stretch": True}])
    table.add_row([QLabel("1"), QLabel("2")])
    table.add_row([QLabel("3"), QLabel("4")])
    table.clear_rows()
    # Header row only = 2 columns
    assert table._grid.count() == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_components.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.widgets.components'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/widgets/components.py
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
            if isinstance(widget, QLabel):
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_components.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add app/widgets/components.py tests/test_components.py
git commit -m "Phase 1d: Add shared component library (PrimaryButton, SecondaryButton, Card, StatCard, StatusBadge, FixedGridTable)"
```

---

## Task 5: Phase 1 verification

- [ ] **Step 1: Render every component in a blank window and screenshot**

Write and run a throwaway script (do not commit it - use the scratchpad directory) that builds one instance of each: `PrimaryButton`, `SecondaryButton`, `Card` (with a label inside), `StatCard`, `StatusBadge` (one per semantic), and a `FixedGridTable` with 3 sample columns (one fixed-width, one stretch, one fixed-width) and 2 sample rows, all inside a themed `QMainWindow` (`app.setStyleSheet(build_stylesheet("dark"))`). Grab a screenshot (`widget.grab().save(...)`) and view it. Confirm:
- Colors visually match the token values (near-black surfaces, blue accent on PrimaryButton).
- `FixedGridTable` columns are pixel-aligned between the header row and both data rows (compare x-coordinates of column boundaries in the screenshot).

- [ ] **Step 2: Grep for stray literals**

```bash
grep -rnE "#[0-9a-fA-F]{6}" app/ --include=*.py | grep -v "app[\\/]design[\\/]tokens.py"
```
Expected: every hit is inside `app/styles.py`'s f-string references to `Color.*` (i.e., no bare hex digits, only `{Color.X}` interpolations) or inside files not yet touched by this redesign (expected - later phases handle those). Confirm no hit is a genuinely new hardcoded hex introduced by Phase 1's own new files.

- [ ] **Step 3: Full test suite**

Run: `pytest -q`
Expected: all tests pass (existing suite + the new Phase 1 tests). Report the final count.

- [ ] **Step 4: Commit is already done per-task above; push the branch**

```bash
git push -u origin feature/visual-redesign
```

- [ ] **Step 5: Write a Phase 1 session note to the Obsidian vault**

Note explicitly: Phase 1 complete (tokens, styles.py rewrite + transitional `color()` shim, icons, components), Phase 2 not started, full test count, and the qtawesome icon-name substitutions discovered.

**Do not proceed to Phase 2 until Steps 1-3 above are confirmed.**

---

# PHASE 2 — Application shell: sidebar navigation + window chrome

Grounded against the current `app/window.py` (861 lines, read in full during planning). Key facts that shape this phase:
- `MainWindow._build_ui()` (`app/window.py:209-290`) currently stacks: `_build_header()` (full-width top bar with logo, nav buttons, and window control buttons in one `_DragHeader`) → update/pending banners → `step_container` (step indicator) → `self.stack` (QStackedWidget, 10 pages) → `FooterBar()`.
- `_DragHeader` (`app/window.py:130-162`) is BOTH the branding/nav bar AND the frameless window's drag handle (mouse press/move/release + double-click-to-maximize). This phase must preserve that drag behavior while visually splitting branding out into the sidebar.
- Window resize-by-edge-drag logic (`app/window.py:750-830`, `eventFilter`/`_resize_direction_at`/`_perform_resize`) operates on `self` (the whole window), not the header - unaffected by this phase, do not touch.
- Nav destinations today: `_go_to_dashboard`, `_go_to_history`, `_go_to_settings`, `_go_to_batch` (not in the new sidebar's initial 5 items - Batch Generate stays reachable only via Dashboard's Quick Actions for now, per the spec's explicit nav item list), `_go_to_projects` (same - not a top-level sidebar item), `_go_to_email`, `_go_to_converter`. The spec's 5 primary nav items map to: Dashboard → `_go_to_dashboard`, Tracksheet → step 0 (`_go_to_step(0)`, i.e. Import page), Update email → `_go_to_email`, Data converter → `_go_to_converter`, History → `_go_to_history`. Settings is a separate "System" section item → `_go_to_settings`.
- `STATUS_HINTS` / `_on_page_changed` (`app/window.py:639-648`) drives the status bar hint text and step-indicator visibility by stack index - unchanged by this phase.

## Task 6: Sidebar widget (`app/widgets/sidebar.py`)

**Files:**
- Create: `app/widgets/sidebar.py`
- Test: `tests/test_sidebar.py`

**Interfaces:**
- Consumes: `Color`, `Spacing`, `Radius`, `FontSize` from `app.design.tokens`; `icon` from `app.design.icons`; `get_pixmap` from `app.logo`.
- Produces: `Sidebar(QWidget)` with signal `nav_item_clicked = pyqtSignal(str)` emitting a stable string id per item (`"dashboard"`, `"tracksheet"`, `"email"`, `"converter"`, `"history"`, `"settings"`), and a method `set_active(item_id: str) -> None` that applies the active-state styling to exactly one item and clears it from the rest.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sidebar.py
"""Tests for the left sidebar navigation widget."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def test_sidebar_has_expected_nav_items():
    from app.widgets.sidebar import Sidebar
    sidebar = Sidebar()
    assert set(sidebar._nav_buttons.keys()) == {
        "dashboard", "tracksheet", "email", "converter", "history", "settings",
    }


def test_sidebar_fixed_width():
    from app.widgets.sidebar import Sidebar, SIDEBAR_WIDTH
    sidebar = Sidebar()
    assert SIDEBAR_WIDTH == 220
    assert sidebar.minimumWidth() == 220
    assert sidebar.maximumWidth() == 220


def test_clicking_nav_item_emits_signal_with_item_id(qtbot):
    from app.widgets.sidebar import Sidebar
    sidebar = Sidebar()
    qtbot.addWidget(sidebar)
    with qtbot.waitSignal(sidebar.nav_item_clicked, timeout=1000) as blocker:
        sidebar._nav_buttons["history"].click()
    assert blocker.args[0] == "history"


def test_set_active_marks_exactly_one_item_active():
    from app.widgets.sidebar import Sidebar
    sidebar = Sidebar()
    sidebar.set_active("converter")
    assert sidebar._nav_buttons["converter"].property("active") == "true"
    for item_id, btn in sidebar._nav_buttons.items():
        if item_id != "converter":
            assert btn.property("active") != "true"

    sidebar.set_active("dashboard")
    assert sidebar._nav_buttons["dashboard"].property("active") == "true"
    assert sidebar._nav_buttons["converter"].property("active") != "true"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sidebar.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.widgets.sidebar'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/widgets/sidebar.py
"""Left sidebar navigation - replaces the old top header nav bar."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.design.icons import icon
from app.design.tokens import Color, FontSize, Radius, Spacing
from app.logo import get_pixmap

SIDEBAR_WIDTH = 220

# (item_id, label, icon name, section) - icon names confirmed to resolve
# under the ph. prefix; see docs/superpowers/plans/2026-07-01-visual-redesign.md
_TOOLS_ITEMS = [
    ("dashboard", "Dashboard", "house"),
    ("tracksheet", "Tracksheet", "table"),
    ("email", "Update email", "envelope-simple"),
    ("converter", "Data converter", "arrows-left-right"),
    ("history", "History", "clock-counter-clockwise"),
]
_SYSTEM_ITEMS = [
    ("settings", "Settings", "gear"),
]

USER_NAME = "Tyler Chambers"


class _NavButton(QPushButton):
    def __init__(self, item_id: str, label: str, icon_name: str, parent: QWidget | None = None):
        super().__init__(f"  {label}", parent)
        self.item_id = item_id
        self._icon_name = icon_name
        self._apply_inactive_icon()
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                background: transparent;
                border: none;
                border-radius: {Radius.SIDEBAR_ITEM}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                color: {Color.TEXT_MUTED};
                font-size: {FontSize.SECTION}px;
            }}
            QPushButton:hover {{
                background-color: {Color.CARD_BG};
            }}
            QPushButton[active="true"] {{
                background-color: {Color.ACCENT_BG_TINT};
                color: {Color.ACCENT_TEXT};
                font-weight: 500;
            }}
            """
        )

    def _apply_inactive_icon(self) -> None:
        self.setIcon(icon(self._icon_name, color=Color.TEXT_MUTED))

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.setIcon(icon(self._icon_name, color=Color.ACCENT_TEXT if active else Color.TEXT_MUTED))
        self.style().unpolish(self)
        self.style().polish(self)


class Sidebar(QWidget):
    """Persistent left navigation. Emits nav_item_clicked(item_id) on click."""

    nav_item_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setStyleSheet(
            f"background-color: {Color.SIDEBAR_BG}; border-right: 1px solid {Color.BORDER};"
        )
        self._nav_buttons: dict[str, _NavButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.LG, Spacing.MD, Spacing.LG)
        layout.setSpacing(Spacing.XS)

        brand_row = QHBoxLayout()
        logo_label = QLabel()
        logo_label.setPixmap(get_pixmap(28, 28))
        brand_row.addWidget(logo_label)
        brand_row.addSpacing(Spacing.SM)
        name_label = QLabel("DATO Toolkit")
        name_label.setStyleSheet(f"color: {Color.TEXT_PRIMARY}; font-size: {FontSize.SECTION}px; font-weight: 600;")
        brand_row.addWidget(name_label)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(Spacing.LG)

        layout.addWidget(self._section_label("Tools"))
        for item_id, label, icon_name in _TOOLS_ITEMS:
            layout.addWidget(self._add_nav_button(item_id, label, icon_name))

        layout.addSpacing(Spacing.LG)
        layout.addWidget(self._section_label("System"))
        for item_id, label, icon_name in _SYSTEM_ITEMS:
            layout.addWidget(self._add_nav_button(item_id, label, icon_name))

        layout.addStretch(1)

        user_row = QFrame()
        user_row.setStyleSheet(f"border-top: 1px solid {Color.BORDER};")
        user_layout = QHBoxLayout(user_row)
        user_layout.setContentsMargins(Spacing.SM, Spacing.MD, Spacing.SM, 0)
        avatar = QLabel("TC")
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background-color: {Color.ACCENT_BG_TINT}; color: {Color.ACCENT_TEXT}; "
            f"border-radius: 14px; font-size: {FontSize.SMALL}px; font-weight: 600;"
        )
        user_layout.addWidget(avatar)
        user_layout.addSpacing(Spacing.SM)
        user_label = QLabel(USER_NAME)
        user_label.setStyleSheet(f"color: {Color.TEXT_SECONDARY}; font-size: {FontSize.SMALL}px;")
        user_layout.addWidget(user_label)
        user_layout.addStretch(1)
        layout.addWidget(user_row)

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setStyleSheet(
            f"color: {Color.TEXT_FAINT}; font-size: {FontSize.LABEL}px; font-weight: 600; "
            f"padding: {Spacing.SM}px {Spacing.MD}px 4px {Spacing.MD}px;"
        )
        return label

    def _add_nav_button(self, item_id: str, label: str, icon_name: str) -> _NavButton:
        btn = _NavButton(item_id, label, icon_name)
        btn.clicked.connect(lambda: self.nav_item_clicked.emit(item_id))
        self._nav_buttons[item_id] = btn
        return btn

    def set_active(self, item_id: str) -> None:
        for current_id, btn in self._nav_buttons.items():
            btn.set_active(current_id == item_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sidebar.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/widgets/sidebar.py tests/test_sidebar.py
git commit -m "Phase 2a: Add Sidebar navigation widget"
```

---

## Task 7: Wire the sidebar into `app/window.py`, restyle chrome, restyle footer

This task restructures `MainWindow._build_ui` and `_build_header`. Because `_DragHeader` currently carries both branding AND drag/window-button responsibilities, the drag header becomes a **slim top strip** (window controls + drag handle only, no logo/nav), and a new horizontal row holds `Sidebar` (left) + a content column (breadcrumb + step indicator + stack) on the right. `FooterBar` stays full-width at the very bottom, below that row — matching the spec's "position unchanged - bottom of the window, below the sidebar+content row."

**Files:**
- Modify: `app/window.py` (`_build_ui` at `window.py:209-290`, `_build_header` at `window.py:292-373`, `_on_page_changed` at `window.py:639-648`)
- Modify: `app/widgets/footer.py` (restyle only — read current file first; replace any `color("...")`/hardcoded hex calls with `Color.*` token references, no structural change)
- Test: `tests/test_window_sidebar_wiring.py` (new)

**Interfaces:**
- Consumes: `Sidebar` (Task 6), `Color`/`Spacing` tokens.
- Produces: `MainWindow` gains a `self.sidebar: Sidebar` attribute and a `self.breadcrumb_label: QLabel` attribute (shows e.g. "Tools > Data converter"). Page-switch methods (`_go_to_dashboard`, `_go_to_converter`, etc.) are unchanged in what they do, but each must now also call `self.sidebar.set_active(item_id)` and update `self.breadcrumb_label`. `_on_page_changed` gains a stack-index → `(item_id, breadcrumb_text)` lookup so the sidebar stays in sync even when navigation happens indirectly (e.g. finishing the wizard, or a page-internal `back_requested` signal).

- [ ] **Step 1: Read `app/widgets/footer.py` in full** to identify every `color(...)`/hex literal call site before touching it (do not guess at its contents).

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_window_sidebar_wiring.py
"""Tests that MainWindow's sidebar navigation stays in sync with page switches."""
from __future__ import annotations

import sys
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication(sys.argv)


def _make_window():
    from app.window import MainWindow
    with patch("app.window.QSettings") as MockSettings:
        instance = MockSettings.return_value
        instance.value.return_value = None
        return MainWindow()


def test_window_has_sidebar_attribute():
    win = _make_window()
    from app.widgets.sidebar import Sidebar
    assert isinstance(win.sidebar, Sidebar)


def test_go_to_converter_activates_converter_sidebar_item():
    win = _make_window()
    win._go_to_converter()
    assert win.sidebar._nav_buttons["converter"].property("active") == "true"


def test_go_to_dashboard_activates_dashboard_sidebar_item():
    win = _make_window()
    win._go_to_converter()  # move away from dashboard first
    win._go_to_dashboard()
    assert win.sidebar._nav_buttons["dashboard"].property("active") == "true"


def test_go_to_history_activates_history_sidebar_item():
    win = _make_window()
    win._go_to_history()
    assert win.sidebar._nav_buttons["history"].property("active") == "true"


def test_sidebar_nav_click_switches_stack_page():
    from app.pages.converter_page import ConverterPage
    win = _make_window()
    win.sidebar.nav_item_clicked.emit("converter")
    assert isinstance(win.stack.currentWidget(), ConverterPage)


def test_breadcrumb_updates_on_navigation():
    win = _make_window()
    win._go_to_converter()
    assert "Data converter" in win.breadcrumb_label.text()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_window_sidebar_wiring.py -v`
Expected: FAIL (`MainWindow` has no attribute `sidebar`).

- [ ] **Step 4: Implement**

In `app/window.py`:

1. Add imports: `from app.widgets.sidebar import Sidebar` and `from app.design.tokens import Color, Spacing`.
2. Add a module-level lookup table (near `STATUS_HINTS`):
   ```python
   SIDEBAR_ITEM_BY_INDEX = {
       0: ("dashboard", "Dashboard"),
       1: ("tracksheet", "Tools > Tracksheet > Import"),
       2: ("tracksheet", "Tools > Tracksheet > Arrange"),
       3: ("tracksheet", "Tools > Tracksheet > Generate"),
       HISTORY_PAGE_INDEX: ("history", "Tools > History"),
       SETTINGS_PAGE_INDEX: ("settings", "System > Settings"),
       BATCH_PAGE_INDEX: ("dashboard", "Tools > Batch Generate"),
       PROJECTS_PAGE_INDEX: ("dashboard", "Tools > All Projects"),
       EMAIL_PAGE_INDEX: ("email", "Tools > Update email"),
       CONVERTER_PAGE_INDEX: ("converter", "Tools > Data converter"),
   }
   ```
   (Batch/Projects pages aren't top-level sidebar items per the spec, so they highlight "dashboard" as the closest parent while showing their own breadcrumb — same pattern TRACE-style apps use for pages reached via a dashboard quick action rather than primary nav.)
3. Replace the body of `_build_header()` (`window.py:292-373`) with a slim version that keeps ONLY: the `_DragHeader` subclassing/drag behavior, the update indicator + update-available label, and the three window control buttons (minimize/maximize/close). Remove the `logo_label`, `name_label`, `version_label`, `self.home_button`, `self.settings_button`, `self.email_nav_button`, `self.converter_nav_button` — that branding+nav now lives in `Sidebar`. Keep the `_DragHeader` background restyled: `header.setStyleSheet(f"background-color: {Color.SIDEBAR_BG};")`.
4. Add a new method `_build_breadcrumb() -> QWidget` returning a slim `QWidget` with a `QHBoxLayout` containing `self.breadcrumb_label = QLabel()` styled `f"color: {Color.TEXT_FAINT}; font-size: {FontSize.SMALL}px;"`, margins `(Spacing.LG, Spacing.SM, Spacing.LG, Spacing.SM)`.
5. In `_build_ui()` (`window.py:209-290`), restructure so the layout becomes:
   ```python
   layout.addWidget(self._build_header())        # slim drag/window-control strip, full width
   layout.addWidget(self.update_banner)
   layout.addWidget(self.pending_banner)

   body_row = QHBoxLayout()
   body_row.setContentsMargins(0, 0, 0, 0)
   body_row.setSpacing(0)
   self.sidebar = Sidebar()
   self.sidebar.nav_item_clicked.connect(self._on_sidebar_nav)
   body_row.addWidget(self.sidebar)

   content_col = QVBoxLayout()
   content_col.setContentsMargins(0, 0, 0, 0)
   content_col.setSpacing(0)
   content_col.addWidget(self._build_breadcrumb())
   content_col.addWidget(self.step_container)  # existing step indicator, unchanged
   content_col.addWidget(self.stack, 1)         # existing QStackedWidget, unchanged
   body_row.addLayout(content_col, 1)

   layout.addLayout(body_row, 1)
   layout.addWidget(FooterBar())
   ```
   (Everything from `self.step_container = QWidget()` through the ten `self.stack.addWidget(...)` calls, and every `*.connect(...)` wiring line in the existing `_build_ui`, stays exactly as-is — only where these widgets get added to a layout changes.)
6. Add a method:
   ```python
   def _on_sidebar_nav(self, item_id: str) -> None:
       {
           "dashboard": self._go_to_dashboard,
           "tracksheet": lambda: self._go_to_step(0),
           "email": self._go_to_email,
           "converter": self._go_to_converter,
           "history": self._go_to_history,
           "settings": self._go_to_settings,
       }[item_id]()
   ```
7. In `_on_page_changed(self, index: int)` (`window.py:639-648`), after the existing body, add:
   ```python
   item_id, breadcrumb_text = SIDEBAR_ITEM_BY_INDEX.get(index, ("dashboard", "Dashboard"))
   self.sidebar.set_active(item_id)
   self.breadcrumb_label.setText(breadcrumb_text)
   ```
   This single hook covers every navigation path (sidebar click, keyboard shortcut, `back_requested` signals, wizard step completion) because they all funnel through `self.stack.setCurrentIndex(...)`, which already fires `currentChanged` → `_on_page_changed`.
8. Restyle window control buttons: in `_make_window_button`, the hover-color parameter callers (`color("chrome_hover")`, `WINDOW_CLOSE_HOVER = "#e94560"`) — change `WINDOW_CLOSE_HOVER` to `Color.DANGER` and the `_make_window_button` calls' `color("chrome_hover")` argument to `Color.BORDER_STRONG` (or import `Color` directly and drop the legacy `color()` call here since this file is being actively edited anyway).
9. Restyle `_build_update_banner`/`_build_pending_banner`'s hardcoded hex values (`#1a3a2a`, `#00B050`→keep (matches `Color.SUCCESS` exactly, already correct), `#e94560`, `#ff5c75`, `#1a2a3a`, `#2f80ed`, `#4a94f5`, `#9aa0b4`) to their `Color.*` token equivalents (`Color.CARD_BG`-ish tint for banner backgrounds is fine as literal semantic banner colors — these are one-off status banners, not part of the core token palette; keep them AS SEPARATE named constants near the top of `window.py` the way `UPDATE_BANNER_BG`/`UPDATE_BANNER_BORDER_COLOR` already are today, just point the CTA buttons inside them at `Color.ACCENT`/`Color.ACCENT_HOVER` instead of the old red-pink so they're visually consistent with the new brand color).
10. In `app/widgets/footer.py`: replace every `color(...)` / hardcoded hex call found in Step 1 with the matching `Color.*` token (no structural changes — same widgets, same text, same layout).

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_window_sidebar_wiring.py -v`
Expected: PASS (6 tests)

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: all pass. This is the highest-regression-risk task in the whole plan (touches the main window wiring every page depends on) — do not skip this check.

- [ ] **Step 7: Commit**

```bash
git add app/window.py app/widgets/footer.py tests/test_window_sidebar_wiring.py
git commit -m "Phase 2b/2c/2d: Wire Sidebar into MainWindow, restyle window chrome and footer"
```

---

## Task 8: Phase 2 verification

- [ ] **Step 1: Run the app** (`python main.py`) and confirm: sidebar renders with Tools/System sections and correct icons; clicking each of the 6 nav items switches to the correct page (pages will look unstyled/old until their own phase — that's expected, confirm navigation works structurally); the active nav item highlights (`Color.ACCENT_BG_TINT` background, blue text); window still drags by the top strip and resizes by edge, minimize/maximize/close still work; footer still renders and its links still work.
- [ ] **Step 2:** Screenshot the app with the sidebar visible.
- [ ] **Step 3:** `pytest -q`, report final count.
- [ ] **Step 4:** `git push origin feature/visual-redesign`.
- [ ] **Step 5:** Write a Phase 2 session note to the Obsidian vault. Note explicitly: Phase 1-2 complete, Phase 3 not started.

**Do not proceed to Phase 3 until Steps 1-3 above are confirmed.**

---

# PHASE 3 — Rebuild Data Converter page (reference implementation)

Grounded against the current `app/pages/converter_page.py` and `app/widgets/flag_review_widget.py`, both fully read and modified earlier this session (2026-07-01) for the overwrite-confirmation, friendly-error, and field-width fixes — those behaviors are the ones this phase must preserve byte-for-byte in logic, restyled only.

## Task 9: Rebuild `FlagReviewWidget` using `FixedGridTable` + `StatusBadge`

**Files:**
- Modify: `app/widgets/flag_review_widget.py` (full rebuild of `_build_ui`, `_make_combo` keeps its logic, only visual constants change)
- Modify: `tests/test_flag_review_widget.py` (existing 12 tests must all still pass unmodified in behavior — only widget-lookup internals may need small adjustments if the row-building mechanism changes how `self._code_inputs`/`self._leave_checks` are populated; the *public* signal contract, `mappings_confirmed`, does not change)

**Interfaces:**
- Consumes: `FixedGridTable`, `StatusBadge` (Task 4).
- Produces: same public API as today — `FlagReviewWidget(mapping_result, ats_flags=None, parent=None)`, signal `mappings_confirmed(dict)`. `self._code_inputs: dict[str, QComboBox]` and `self._leave_checks: dict[str, QCheckBox]` must keep the same names and semantics — 9 existing tests reference them directly (`widget._code_inputs["XX"]`, `widget._leave_checks["XX"]`).

- [ ] **Step 1: Re-run the existing test suite first as a baseline**

Run: `pytest tests/test_flag_review_widget.py -v`
Expected: 10 PASS (the 10 tests present as of commit `4132c87`, including this session's `test_combo_field_width_is_constrained` and `test_combo_popup_stays_wide_enough_for_long_descriptions`).

- [ ] **Step 2: Rebuild `_build_ui`**

Column definition matching the spec exactly:
```python
_COLUMNS = [
    {"label": "ATS Code", "width": 90},
    {"label": "ATS Description", "stretch": True},
    {"label": "Standard Symbol", "width": 260},
    {"label": "Status", "width": 130},
    {"label": "Leave as-is", "width": 90},
]
```
Replace the per-row `QHBoxLayout` construction (today's `row = QHBoxLayout(); row.addWidget(...)` blocks for known/suggested/unknown flags) with a single `FixedGridTable(_COLUMNS)` instance built once in `_build_ui`, then one `table.add_row([...])` call per flag (known/suggested/unknown), each row's Status cell built as a `StatusBadge(text, semantic)` instead of a plain `QLabel` with manual `setStyleSheet` (map `AUTO_MAPPED_LABEL`→`"success"`, `SUGGESTED_MATCH_LABEL`→`"warning"`... check against the mockup's actual color for "Suggested," likely `"warning"` given `SUGGESTED_MATCH_COLOR` was blue before — re-derive from the approved mockup if the exact suggested-state color differs from plain warning-amber, note the decision in the session note either way, and `NEEDS_MAPPING_LABEL`→`"warning"`). The Standard Symbol column's cell is the existing `_make_combo()` result, right-aligned in its 260px-fixed cell (this session's `COMBO_MAX_WIDTH = 340` must shrink to fit inside 260px — change `COMBO_MAX_WIDTH` to `230` in this task, leaving headroom inside the 260px column with `Spacing.MD` horizontal padding on each side; keep `COMBO_POPUP_MIN_WIDTH = 400` unchanged since the popup is allowed to be wider than its column, per this session's already-verified behavior). "Leave as-is" checkbox goes in the last 90px column, right-aligned via the checkbox's own alignment flag, not a stretch trick.
Known-flag rows keep the existing read-only rendering (code, description, resolved symbol, "Auto-mapped" `StatusBadge`, empty last cell) but now go through `table.add_row(...)` too, for a fully consistent grid — this eliminates the pre-redesign special case where known rows and suggested/unknown rows were built by different code paths.

- [ ] **Step 3: Run the existing tests, fix any that reference removed internals**

Run: `pytest tests/test_flag_review_widget.py -v`
Expected: all pass. If any fails because it inspected a `QHBoxLayout`/`row` internal that no longer exists, adjust that test's internals-lookup to go through `widget._code_inputs`/`widget._leave_checks` (unchanged) or `widget._table` (new) — never change what a test asserts about *behavior*, only how it reaches the widget under test.

- [ ] **Step 4: Commit**

```bash
git add app/widgets/flag_review_widget.py tests/test_flag_review_widget.py
git commit -m "Phase 3a: Rebuild FlagReviewWidget using FixedGridTable + StatusBadge"
```

---

## Task 10: Rebuild `ConverterPage` using `Card`/`StatCard`/`PrimaryButton`/`SecondaryButton`

**Files:**
- Modify: `app/pages/converter_page.py` (`_build_ui` and its sub-builders; `_ConvertWorker`, `_on_convert`, `_existing_output_paths`, `_confirm_overwrite`, `_import_file`, `_on_file_done`, etc. keep their exact logic — this task only touches widget construction/layout, never the methods verified earlier this session)

**Interfaces:**
- Consumes: `Card`, `StatCard`, `PrimaryButton`, `SecondaryButton` (Task 4), `icon` (Task 3).
- Produces: same public API — `ConverterPage()`, signal `back_requested`, all existing attributes (`_imported`, `_errors`, `_flag_mapping`, `_flags_confirmed`, `_worker`, `_output_folder_edit`, `_convert_btn`, etc.) keep their exact names since `tests/test_converter_page.py`'s 9 tests reach them directly.

- [ ] **Step 1: Baseline**

Run: `pytest tests/test_converter_page.py -v`
Expected: 9 PASS.

- [ ] **Step 2: Rebuild layout**

- Page header: breadcrumb (already provided globally by `MainWindow`'s new breadcrumb bar from Phase 2 — do not duplicate it on the page itself) + `TITLE_TEXT` heading with the `arrows-left-right` icon prefixed, + the existing ATS/TEAM/TDS tab row restyled as pill buttons (`Radius.PILL`, active tab `Color.ACCENT` background, disabled tabs keep their existing `COMING_SOON_TOOLTIP` behavior unchanged).
- Stat card row: build 3 `StatCard`s — "Files loaded" (`len(self._imported)`), "Elevations" (`sum(len(r.elevations) for r in self._imported.values())`), "Flags needing review" (`len(mapping_result.unknown) + len(mapping_result.suggested)` from the most recent `build_flag_mapping` call, `value_color=Color.WARNING` when > 0 else `Color.TEXT_PRIMARY`). Store these as `self._stat_files`, `self._stat_elevations`, `self._stat_flags` and call `.set_value(...)` on them from `_import_file`/`_on_remove_file`/`_on_clear_all`/`_refresh_flag_widget` (the existing methods that already recompute this state) — do not add new state tracking, only new display calls at the point each existing method already mutates `self._imported`.
- `_FileCard` (`converter_page.py:169-179` today, a hand-built `QFrame`) becomes a `Card` subclass or wraps a `Card` instance — same content (filename, section/tubes/elevations detail line, remove button), restyled.
- Flag Review section: unchanged wiring (`self._flag_widget_layout`, `FlagReviewWidget` instantiation) — it now renders using Task 9's rebuilt widget automatically, nothing to change here beyond confirming the container `QWidget` doesn't fight the new `FixedGridTable`'s sizing.
- Output section becomes a `Card`: output folder `QLineEdit` (unchanged, still `INPUT_BG`-styled via the global QSS) + `SecondaryButton(BROWSE_TEXT)` replacing today's flat `QPushButton`, and `PrimaryButton(CONVERT_ALL_TEXT)` with a `play` icon (`btn.setIcon(icon("play", color=Color.TEXT_PRIMARY))`) replacing today's `accent`-property `QPushButton` — functionally identical, `self._convert_btn.setEnabled(...)`/`.clicked.connect(self._on_convert)` unchanged.
- `_ErrorCard` restyled with `Color.DANGER` accents, same content/behavior.

- [ ] **Step 3: Verify the 260px Standard Symbol column doesn't clip the combo**

Run the app, open Flag Review with a real unknown flag, screenshot the closed combo field and confirm it renders fully inside its 260px column with `Spacing.MD` breathing room on both sides (per Task 9's `COMBO_MAX_WIDTH = 230` change) — measure `combo.width()` the same way this session's earlier width investigation did, report the actual pixel value.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_converter_page.py tests/test_flag_review_widget.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/pages/converter_page.py
git commit -m "Phase 3b: Rebuild ConverterPage using Card/StatCard/PrimaryButton/SecondaryButton"
```

---

## Task 11: Phase 3 verification

- [ ] **Step 1:** Convert a real ATS file end to end via the running app (use one from `examples/ats/` — confirm the exact path by listing that directory first, do not assume a filename). Confirm: drag-and-drop import still works, the overwrite-confirmation dialog still appears/blocks correctly when re-converting into a folder with existing output, friendly permission-error messages still appear when a target file is locked (open one in Excel first to trigger it, same manual check as earlier this session), batch conversion still continues past one failed file, output-folder persistence (QSettings) still works.
- [ ] **Step 2:** Screenshot the rebuilt page and compare structurally against the approved mockup (stat cards, tab pills, card-based file list, fixed-grid flag review table, output card).
- [ ] **Step 3:** `pytest -q`, report final count.
- [ ] **Step 4:** `git push origin feature/visual-redesign`.
- [ ] **Step 5:** Write a Phase 3 session note to the Obsidian vault. Note explicitly: Phase 1-3 complete, Phase 4 not started, and record the actual measured Standard Symbol field width from Task 10 Step 3.

**Do not proceed to Phase 4 until Steps 1-3 above are confirmed.**

---

# PHASE 4 — Rebuild Dashboard page

Current file: `app/pages/dashboard_page.py` (`DashboardPage` class at line 54, `STATUS_HINT`/`TITLE_TEXT` at lines 17/36). Not yet read in full during this planning pass — **first step of this phase is to read it completely** before writing any code, same discipline Phase 3 used.

**Files:**
- Modify: `app/pages/dashboard_page.py`
- Test: extend/adjust `tests/test_*dashboard*.py` if it exists, or add one if the page currently has no dedicated test file (check first: `ls tests/ | grep -i dashboard`).

## Task 12: Rebuild Dashboard
- [ ] Read `app/pages/dashboard_page.py` in full; note every signal it emits (`new_tracker_requested`, `project_selected`, `view_history_requested`, `view_projects_requested`, `batch_requested`, `email_requested`, `converter_requested` — all confirmed from `window.py`'s connect calls at `window.py:257-263`) and every method `MainWindow` calls on it (`.refresh()`, confirmed from `window.py:644`). These are the preserved-functionality contract for this phase — none may change name or signature.
- [ ] Stat card row using `StatCard`: Trackers Generated, Last Generated, Sections Processed, Update Emails Generated — source these from wherever the current implementation reads `history.json` (read `app/history.py` if the current page doesn't compute these inline).
- [ ] Recent Projects list: one `Card` per project, preserving the existing Open/Regenerate actions and their exact click-handler wiring, restyled buttons (`SecondaryButton` for Regenerate, plain clickable card or `SecondaryButton` for Open — match whichever the mockup shows).
- [ ] Quick Actions row: `SecondaryButton` per action with an appropriate `icon(...)` (batch → none listed in the icon set explicitly, reuse `table` or `play`; projects → `folder`; confirm against the mockup rather than guessing if ambiguous).
- [ ] Empty state (no projects yet): restyle colors only, preserve exact copy and the condition that triggers it.
- [ ] Preserve `.refresh()` behavior exactly — this is called by `MainWindow._on_page_changed` every time the dashboard becomes visible; a regression here breaks stat freshness silently (no test failure, just stale numbers on screen), so manually verify by generating a tracker, returning to Dashboard, and confirming the stat updates.

## Task 13: Phase 4 verification
- [ ] Run the app with and without existing project history (temporarily rename the history/projects data dir to test the empty state if no clean-slate environment is available — restore it after).
- [ ] Confirm every button navigates correctly (Dashboard is the hub every other page's `back_requested` returns to — a regression here is high-blast-radius).
- [ ] `pytest -q`, report final count. `git push`. Write Phase 4 session note (Phase 1-4 complete, Phase 5 not started).

**Do not proceed to Phase 5 until verification above is confirmed.**

---

# PHASE 5 — Rebuild Tracksheet wizard (Import / Arrange / Generate)

Current files: `app/pages/import_page.py` (`ImportPage` at line 179, `_DropZone`/`_FileCard` helper classes), `app/pages/reorder_page.py` (`ReorderPage` at line 80, `_SectionCountDelegate`), `app/pages/generate_page.py` (`GeneratePage` at line 109, `GenerateWorker` QThread). None read in full during this planning pass — **read each file completely before touching it**, same discipline as every prior phase.

This is the highest-functional-risk phase in the plan: drag-and-drop reordering (`reorder_page.py`), a background `QThread` worker (`generate_page.py`), and the step-indicator wiring in `window.py` (`step_indicator.step_clicked`, `self._completed_steps`, `_go_to_step`) all have to keep working exactly as today.

## Task 14: Rebuild Import step
- [ ] Read `import_page.py` in full. Note the `ImportResult` dataclass, `_DropZone`/`_FileCard` classes, and `files_ready`/`project_load_requested` signals (both confirmed wired in `window.py:267-268`).
- [ ] Restyle drop zone as a `Card`-based dashed-border drop target (keep drag-enter/leave/drop event handlers verbatim). Restyle `_FileCard` using `Card`. Error cards get `Color.DANGER` accents (mirroring Task 10's `_ErrorCard` pattern from Phase 3 — reuse that exact visual pattern for consistency, don't invent a new one).

## Task 15: Rebuild Arrange step
- [ ] Read `reorder_page.py` in full, including `_SectionCountDelegate` (a `QStyledItemDelegate` — restyle its `paint()` token colors only, do not touch its drag/drop reordering logic, which is almost certainly implemented via `QListWidget` internal move mode or a custom model — confirm which before editing).
- [ ] Restyle the section list, title field, Additional Sections panel (Auxiliary/Punchlist item editors — these live in `app/widgets/item_editor.py`, read that file too since it's shared with Phase 6/Email page), and the live preview panel (`app/widgets/tracker_preview.py`, read before touching).
- [ ] Preserve drag-and-drop reordering, double-click-to-rename (per `STATUS_HINT` text: "drag sections to reorder them, or double-click to rename"), and the `continue_requested`/`back_requested` signals (confirmed wired at `window.py:269-270`).

## Task 16: Rebuild Generate step
- [ ] Read `generate_page.py` in full, including `GenerateWorker(QThread)`.
- [ ] Summary `Card`, output options restyled, `PrimaryButton` for "Generate Tracker", progress bar (`Color.ACCENT` fill — already the global QSS default from Task 2, confirm no page-local override needs removing), success card with `Color.SUCCESS` accents.
- [ ] Preserve `email_requested`, `back_requested`, `new_project_requested`, `tracker_generated` signals (all confirmed wired at `window.py:266,271-273`) and the `generate_button`/`back_button` attribute names (`window.py:702,713` reach them directly via `_activate_primary_action`/`_activate_back_action`).
- [ ] **This phase never touches `app/builder.py` or `app/parser.py`** — if generating a tracker produces a different output file than before this phase, that's a regression, stop and investigate rather than proceeding.

## Task 17: Restyle the step indicator itself
- [ ] Find the `StepIndicator` widget (imported in `window.py:55` from `app.widgets`) and restyle: active step `Color.ACCENT` background (replacing the old red-pink), completed step checkmark `Color.SUCCESS`. Preserve `step_clicked` signal and `set_current_step(index, completed_steps)` method signature exactly (`window.py:229,612` call it).

## Task 18: Phase 5 verification
- [ ] Full wizard run end to end with real data: import real CSVs (check `examples/` for a suitable sample set first), reorder a section via drag, double-click-rename a section, add an auxiliary/punchlist item, generate a tracker.
- [ ] Confirm the generated output file is byte-for-byte what the pre-redesign code would have produced (this phase must not touch `builder.py`/`parser.py` — if you're unsure, diff a tracker generated on `feature/data-converter` against one generated here from identical input).
- [ ] `pytest -q`, report final count. `git push`. Write Phase 5 session note.

**Do not proceed to Phase 6 until verification above is confirmed.**

---

# PHASE 6 — Rebuild Update Email Generator page

Current file: `app/pages/email_page.py` (`EmailPage` at line 244, `_EmailWorker` QThread, `_FindingList`/`_SectionStatusRow`/`_OtherItemRow` helper widgets). Not yet read in full — read completely before touching.

## Task 19: Rebuild Email page
- [ ] Read `email_page.py` in full. Note `back_requested` signal (wired `window.py:264`) and `set_project`/`clear_project` methods (called `window.py:636,673`).
- [ ] Project link/auto-link card using `Card`. Discovery sections reuse the item-editor restyle pattern established in Phase 5 Task 15 (`item_editor.py` is shared — if Phase 5 already restyled it, this phase inherits that restyle for free; if the two phases run in the same session, restyle `item_editor.py` once in whichever phase reaches it first and note the reuse in this phase's session note rather than re-doing the work).
- [ ] Scope of Work / Other Scope Items / Punchlist sections (`_SectionStatusRow`, `_OtherItemRow`) restyled to token colors, structure unchanged.
- [ ] Output section: `PrimaryButton` for document generation, preserving `_EmailWorker` wiring exactly.
- [ ] Preserve: auto-link from active project, manual load fallback, all form fields and their pre-fill behavior, document generation via `app/email_export.py` (do not touch that file).

## Task 20: Phase 6 verification
- [ ] Generate a real update email end to end (auto-linked from an active project, then again via manual load fallback — both paths).
- [ ] Confirm the output `.docx` is unaffected (this phase never touches `app/email_export.py`).
- [ ] `pytest -q`, report final count. `git push`. Write Phase 6 session note.

**Do not proceed to Phase 7 until verification above is confirmed.**

---

# PHASE 7 — Rebuild History page

Current file: `app/pages/history_page.py` (`HistoryPage` at line 27). Confirmed via repo-wide grep during planning: **no `QTableWidget`/`QHeaderView` usage exists anywhere in `app/pages/` today** — History's list is currently hand-rolled (same bug-class root cause the spec calls out), making this phase the direct stress-test of `FixedGridTable` under real, variable-length data.

## Task 21: Rebuild History list with `FixedGridTable`
- [ ] Read `history_page.py` in full first.
- [ ] Columns: `Date` (fixed width, e.g. 100px), `Title` (the one `stretch: True` column — titles vary most in length), `Customer` (fixed, e.g. 140px), `Location` (fixed, e.g. 140px), `Sections` (fixed, narrow, e.g. 80px), `Elevations` (fixed, narrow, e.g. 90px), `Output File` (fixed, e.g. 90px — likely an icon/button cell, not raw text, confirm against current implementation), `PDF` (fixed, narrow, e.g. 70px — likely a status icon).
- [ ] Preserve search/filter (confirmed via `STATUS_HINT`: "Browse every tracker you've generated and reopen its file or folder" — read the actual filter implementation in `app/search.py`, do not touch that module), sort-by-column, Open File / Open Folder actions, empty state.

## Task 22: Phase 7 verification
- [ ] Run with real history data (this device should already have generated trackers from prior sessions — if not, generate a couple first via the wizard).
- [ ] **This is the direct test that FixedGridTable holds up under real data**: confirm columns stay pixel-aligned regardless of content length — specifically test with a very long project title and a very short one in the same list, screenshot and visually confirm the Customer/Location/Sections columns start at identical x-coordinates on both rows.
- [ ] Confirm search still filters correctly, sort still works, Open File/Open Folder still work.
- [ ] `pytest -q`, report final count. `git push`. Write Phase 7 session note.

**Do not proceed to Phase 8 until verification above is confirmed.**

---

# PHASE 8 — Rebuild Settings page

Current file: `app/pages/settings_page.py` (`SettingsPage` at line 52). Not yet read in full — read completely before touching. Almost certainly contains the theme selector referenced in `app/settings.py`'s `get_theme()`/`set_theme()` (grep that module for `theme` before starting, to find every call site this decision affects).

## Task 23: Rebuild Settings
- [ ] Read `settings_page.py` and `app/settings.py` in full.
- [ ] `Card` per section: General, Appearance, Updates, About.
- [ ] Restyle all form controls (text fields, checkboxes, dropdowns) — these already inherit token colors for free from Task 2's rewritten global QSS (`QLineEdit`, `QCheckBox::indicator`, `QComboBox` rules) unless Settings applies page-local style overrides; remove any such overrides found.
- [ ] **Theme selector decision required by the spec**: pick ONE —
  (a) remove the Dark/Light/System theme selector entirely, or
  (b) leave it present but visually disabled with the note "Light theme coming in a future update."
  Pick whichever is less code churn once the actual current implementation is visible (if it's a simple 3-item `QComboBox` bound directly to `set_theme()`/`get_theme()`, (b) — disable the combo, add the note label — is almost certainly less churn than removing the control and all its wiring; if it turns out to be deeply wired into multiple call sites, reconsider). **Record which option was chosen and why in this phase's session note — the spec explicitly requires this.**
- [ ] Preserve: default output folder, filename pattern, PDF default, update-check settings — all unchanged in behavior, restyled only.

## Task 24: Phase 8 verification
- [ ] Confirm settings save and load correctly (change a value, navigate away, navigate back, confirm persistence).
- [ ] Confirm all sections render in the new style.
- [ ] `pytest -q`, report final count. `git push`. Write Phase 8 session note (note the theme-selector decision explicitly here too, not just buried in Task 23).

**Do not proceed to Phase 9 until verification above is confirmed.**

---

# PHASE 9 — Final consistency pass

## Task 25: Grep sweeps
- [ ] Run: `grep -rnE "#[0-9a-fA-F]{6}" app/ --include=*.py | grep -v "app[\\/]design[\\/]tokens.py"` — every remaining hit must be a deliberate one-off (e.g. the update-banner status colors kept as named constants in `window.py` per Phase 2 Task 7 Step 9) or a bug to fix. List and resolve every hit that isn't an already-documented exception.
- [ ] Run: `grep -rn "#1a1a2e\|#16213e\|#e94560\|#0f3460" app/` — expected zero hits anywhere, including `app/splash.py` and any logo-usage context (`app/logo.py`) that might reference the old palette for background compositing. If `splash.py` draws its own background color for the splash screen, restyle it to `Color.PAGE_BG`/`Color.SIDEBAR_BG` as part of this task (read the file first — it wasn't touched by any earlier phase).
- [ ] Run: `grep -rn "def color(" app/styles.py` and `grep -rn "\.color(" app/ --include=*.py` (and the double/single-quote variants used in Task 2's own audit) — if this returns zero call sites outside `app/styles.py` itself, delete the `_LEGACY_COLOR_MAP`/`color()` shim entirely (it was always meant to be temporary — see Task 2). If any call sites remain, leave the shim in place and note which page still needs migration (this would mean an earlier phase's "read the file first" step missed something — investigate before deleting anything).

## Task 26: Visual consistency screenshots
- [ ] Screenshot every page: Dashboard, Tracksheet wizard (all 3 steps), Update Email, Data Converter, History, Settings.
- [ ] Confirm consistent fonts (`FONT_FAMILY` everywhere), consistent spacing rhythm (`Spacing.*` multiples, no stray odd pixel values), consistent button styles (`PrimaryButton`/`SecondaryButton` used everywhere a button appears, no leftover raw `QPushButton` with ad-hoc styling except the window-chrome minimize/maximize/close buttons, which are intentionally special-cased in Phase 2).

## Task 27: Full suite + exe build + version bump
- [ ] `pytest -q` — all tests must pass. Report final count.
- [ ] Run `build.bat`. Confirm it launches and every page is reachable via the new sidebar (repeat the Phase 2 Task 8 Step 1 navigation check against the built exe, not just `python main.py`).
- [ ] Bump `__version__` in `app/__init__.py` to the next MINOR version (read the current value first — do not guess it).

## Task 28: Final commit

```bash
git add -A
git commit -m "Phase 9: Final consistency pass - remove legacy color() shim if unused, restyle splash screen, bump version"
git push origin feature/visual-redesign
```

Do not tag a release or merge this branch anywhere — see the plan header's Global Constraints and the original spec's "Branch setup" section for the intended merge order relative to `feature/data-converter`. Only Tyler decides when to merge.

- [ ] Write a final session note to the Obsidian vault summarizing all 9 phases, final test count, the theme-selector decision from Phase 8, and explicitly stating this branch is complete but unmerged, awaiting Tyler's go-ahead.

---

## Self-Review Notes (from plan authoring)

- **Spec coverage:** Every phase (1-9) and every sub-item in the original spec has a corresponding task above. The two icon-name corrections (`mail`→`envelope-simple`, `file-spreadsheet`→`table`) are the one place this plan deviates from the literal spec text, and that deviation is verified-fact-driven, called out in Global Constraints, and carried through every task that references those icons.
- **Known gap, by necessity:** Phases 4-8 (Dashboard, Wizard, Email, History, Settings) are scoped as task groups with concrete file paths, preserved-signal contracts (cross-checked against `window.py`'s actual `.connect()` call sites), column/component choices, and verification steps — but not full line-by-line code, because those five source files were not read during this planning pass (Phase 1-3's foundation and reference implementation consumed the available grounding budget). Each of those phases' first step is explicitly "read the file in full before writing code," matching the exact discipline Phase 3 used. This is a deliberate, documented scope boundary, not a placeholder — flagged here per this skill's self-review requirement rather than silently glossed over.
- **Type/interface consistency check:** `FixedGridTable.add_row(values: list[QWidget])` (Task 4) is used identically in Task 9 (flag review) and Task 21 (history) — same signature, same column-count validation. `Color`/`Spacing`/`Radius`/`FontSize` names are used consistently by their Task 1 definitions across every later task. `Sidebar.nav_item_clicked(str)` → `MainWindow._on_sidebar_nav(item_id: str)` (Task 7) matches the six `item_id` strings defined in Task 6's `_TOOLS_ITEMS`/`_SYSTEM_ITEMS`.
