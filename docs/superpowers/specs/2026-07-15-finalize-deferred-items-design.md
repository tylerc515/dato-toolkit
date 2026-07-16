# Finalize Deferred Redesign Items - Design

**Date:** 2026-07-15
**Branch:** `feature/visual-redesign`
**Scope:** Clear the three remaining deferred items from the visual redesign before merge: retire the transitional `color()` shim, fix the F1 help-panel toggle, and three minor cleanups.

## Background

The 28-task visual redesign and the update-dialog restyle are complete and
approved. Three items were deliberately deferred during that work
(documented in the 2026-07-01 phase-9 session note and the SDD ledger).
This change finalizes them. No user-facing behavior changes except that F1
now works on all pages and disabled combo boxes / checkboxes render muted.

## Goals

- Delete the transitional `color()` shim and migrate its remaining callers
  to direct design tokens.
- Fix F1 so it toggles the help panel on every page that has one.
- Apply three minor cleanups (dead import, disabled-state QSS gaps, stale
  version string).

## Non-goals

- No visual redesign of any page beyond what the token migration implies
  (the migration is a 1:1 value substitution, so it is visually identical).
- No merge to main in this change (handled separately; see "Merge" below).
- No light-theme work.

## Bucket 1: Retire the `color()` shim

`app/styles.py` defines a transitional shim: `color(name)` looks a legacy
palette key up in `_LEGACY_COLOR_MAP` and returns the mapped new token.
19 call sites remain, all of which resolve to a single token each:

| File | `color()` calls |
|---|---|
| `app/window.py` | 8 |
| `app/pages/batch_page.py` | 6 |
| `app/pages/converter_page.py` | 4 |
| `app/pages/projects_page.py` | 1 |

The legacy-key -> token mapping (from `_LEGACY_COLOR_MAP`):

| Legacy key | Token |
|---|---|
| `background` | `Color.PAGE_BG` |
| `surface` | `Color.CARD_BG` |
| `accent` | `Color.CARD_BG` |
| `button_hover` | `Color.BORDER_STRONG` |
| `button_pressed` | `Color.SIDEBAR_BG` |
| `button_disabled_bg` | `Color.CARD_BG` |
| `highlight` | `Color.ACCENT` |
| `highlight_hover` | `Color.ACCENT_HOVER` |
| `highlight_disabled_bg` | `Color.BORDER_STRONG` |
| `text` | `Color.TEXT_PRIMARY` |
| `muted_text` | `Color.TEXT_MUTED` |
| `border` | `Color.BORDER` |
| `success` | `Color.SUCCESS` |
| `warning` | `Color.WARNING` |
| `error` | `Color.DANGER` |
| `chrome_hover` | `Color.BORDER_STRONG` |

Approach:
- In each caller, replace `color('key')` with the mapped `Color.TOKEN`
  (each file must add `from app.design.tokens import Color` if not already
  importing it). This is a value-identical substitution - no pixel changes.
- Delete `color()` and `_LEGACY_COLOR_MAP` from `app/styles.py`.
- Keep `set_active_theme` / `get_active_theme` / `THEME_*` constants -
  `main.py` still calls them; they are not part of the shim.
- Delete the obsolete `test_legacy_color_keys_still_resolve` test in
  `tests/test_styles.py`.
- Add a guard test asserting no `color(` shim calls remain in `app/`
  (grep-style over the source tree).

## Bucket 2: Fix F1 help-panel toggle

F1 is already registered at the window level
(`app/window.py`: `self._add_shortcut("F1", self._toggle_current_help)`),
but `_toggle_current_help` maps the stacked-page index to a page through a
hardcoded dict that only includes import/reorder/generate/batch/converter.
History, Settings, and Email are absent, so F1 silently does nothing there.

Replace the hardcoded dict with a lookup that works for any page exposing a
`help_panel` attribute:

```python
def _toggle_current_help(self) -> None:
    panel = getattr(self.stack.currentWidget(), "help_panel", None)
    if panel is not None:
        panel.toggle()
```

Every page's help panel is stored as `self.help_panel` (a `HelpPanel` with a
`toggle()` method), so this covers all current and future pages and removes
the maintenance trap.

Test: construct the window (or the relevant pages), switch to a page that was
previously missing (e.g. History or Settings), invoke `_toggle_current_help`,
and assert that page's `help_panel` visibility flips.

## Bucket 3: Minor cleanups

1. **Dead import:** `app/pages/dashboard_page.py` imports `NEVER_TEXT` from
   `app.history` but never uses it. Remove it from the import list (leave the
   other imported names). `NEVER_TEXT` stays defined and used in
   `app/history.py`.
2. **Disabled-state QSS gaps:** `build_stylesheet` has no `QComboBox:disabled`
   or `QCheckBox::indicator:disabled` rule (found in Task 23, worked around
   locally in `settings_page.py`). Add:
   - `QComboBox:disabled` - muted text/background using existing tokens
     (`Color.TEXT_MUTED` text, `Color.CARD_BG` background).
   - `QCheckBox::indicator:disabled` - muted indicator using existing tokens.
   Use only defined `Color` tokens so the stray-hex test stays green.
3. **Stale version:** `pyproject.toml` `version = "2.0.0"`; bump to `"2.3.0"`
   to match `app.__version__`.

## Testing

- `tests/test_styles.py`: remove the legacy-color test; add a test asserting
  the new `QComboBox:disabled` and `QCheckBox::indicator:disabled` rules are
  present; the existing stray-hex and no-old-palette tests must stay green.
- New guard test that no `color(` shim call remains under `app/`.
- New window F1 test (Bucket 2).
- Full suite stays green (currently 218) with Qt offscreen.

## Global constraints

- No hex/pixel/font-size literal outside `app/design/tokens.py`.
- Single dark theme; no light-theme logic.
- No em dashes or en dashes in code/comments.
- Commit email `4742780+tylerc515@users.noreply.github.com`.
- Run tests with `QT_QPA_PLATFORM=offscreen`.

## Merge (separate, after this lands)

`feature/visual-redesign` is built on top of `feature/data-converter`. The
original redesign plan sequences `feature/data-converter` -> main first,
gated on Tyler's TRACE acceptance testing of the ATS converter, then
`feature/visual-redesign`. The merge is not part of this change; the
sequencing and its dependency will be resolved with Tyler once this work is
reviewed and pushed.

## Files touched

- `app/styles.py` - delete shim + map; add disabled rules.
- `app/window.py` - F1 fix; shim-call migration.
- `app/pages/batch_page.py`, `app/pages/converter_page.py`,
  `app/pages/projects_page.py` - shim-call migration.
- `app/pages/dashboard_page.py` - dead import removal.
- `pyproject.toml` - version bump.
- `tests/test_styles.py` (+ new tests) - coverage.
