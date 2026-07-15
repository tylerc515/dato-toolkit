# Update Dialog Restyle - Design

**Date:** 2026-07-15
**Branch:** `feature/visual-redesign`
**Scope:** Visual migration of `app/widgets/update_dialog.py` onto the design-token / property-based styling system, plus five small UX polish items.

## Background

The 28-task visual redesign (`docs/superpowers/plans/2026-07-01-visual-redesign.md`)
restyled every page and the app shell onto `app.design.tokens` +
`app/styles.py`'s property-based global QSS. `app/widgets/update_dialog.py`
was explicitly out of that plan's page scope and still carries its own
old palette: 8 hardcoded hex constants (blue-purple surfaces, the retired
red-pink brand accent) and ~20 inline `setStyleSheet` calls. It is the
last significant screen not matching the app.

The global stylesheet is applied at the `QApplication` level
(`main.py:26`), so any top-level dialog inherits it automatically once its
own overrides are removed. `UpdateDialog` is created with the main window
as parent (`app/window.py:542`).

## Goals

- Remove every hardcoded color, font-size literal, and inline style from
  `update_dialog.py`; drive appearance from `app.design.tokens` and the
  property-based global QSS.
- Apply five small UX polish items (below).
- No change to layout structure, the download/install/later flow, or the
  markdown converter's output structure.

## Non-goals

- No behavior changes to download, install, "install later", or the
  updater backend.
- No light-theme work (app ships a single dark theme).
- No changes to other deferred items (F1 help toggle, batch/projects pages).

## Visual migration

Delete the module-level constants `_BG`, `_SURFACE`, `_BORDER`,
`_NOTES_BG`, `_NOTES_TEXT`, `_MUTED`, `_ACCENT_RED`, `_ACCENT_GREEN`.
Import `Color`, `FontSize`, `Spacing`, `Radius` from `app.design.tokens`.

Token mapping:

| Old literal | New token |
|---|---|
| `_BG #1a1a2e` | `Color.PAGE_BG` |
| `_SURFACE #16213e` (header / install bands) | `Color.SIDEBAR_BG` |
| `_BORDER #2c3759` | `Color.BORDER` |
| `_NOTES_BG #0d1117` | `Color.INPUT_BG` |
| `_NOTES_TEXT #eaeaea` | `Color.TEXT_PRIMARY` |
| `_MUTED #9aa0b4` | `Color.TEXT_MUTED` |
| `_ACCENT_RED #e94560` (retired brand red) | `Color.ACCENT` (blue) |
| `_ACCENT_GREEN #00B050`, progress chunk `#2f80ed`, hovers `#ff5c75`/`#00c85a`/`#5b3641` | `Color.SUCCESS`, `Color.ACCENT`, `Color.ACCENT_HOVER`, token-derived |
| pt font sizes (16/12/11/10/9pt) | `FontSize` tokens (px) |

Styling approach per element:

- **Dialog background:** remove the `QDialog` inline stylesheet; inherits
  `Color.PAGE_BG` from global QSS. Keep the frameless + fixed-size window.
- **Header / install bands:** full-width bands with top/bottom borders
  (not rounded cards), so style with minimal token-based inline CSS
  (`background-color: {Color.SIDEBAR_BG}; border: 1px solid {Color.BORDER}`).
- **Labels:** use `role="heading"` / `role="muted"` properties where they
  map; otherwise token `FontSize` + `Color` inline.
- **Buttons:**
  - "Download & Install" -> `setProperty("accent", "true")` (global blue accent).
  - "Install Now & Restart" -> new `variant="success"` global rule (below).
  - close "x", "View on GitHub", "Install Later", "Cancel" -> `flat="true"`
    (already set); remove the redundant inline `color` overrides.
- **Notes browser (`QTextBrowser`):** token-based (`Color.INPUT_BG` bg,
  `Color.TEXT_PRIMARY` text, `Color.BORDER` scrollbar).
- **Markdown HTML inline styles** (`_MarkdownConverter.to_html`): swap the
  `_NOTES_TEXT` / pt literals for token values; keep the tag structure
  (`<h3>`, `<ul>`, `<li>`, `<b>`, `<p>`) so existing tests stay green.
- **Progress bar:** rely on the global `QProgressBar` rule; chunk uses
  `Color.ACCENT`.

## UX polish (approved)

1. Primary button red -> blue accent (inherent to the migration; noted for
   visual-weight change).
2. Close "x" hover: red -> `Color.TEXT_PRIMARY` neutral brighten.
3. Add a reusable `QPushButton[variant="success"]` rule to
   `build_stylesheet` (green `Color.SUCCESS`, hover slightly darker),
   used by the Install button and available for future use.
4. Nudge fixed dialog height `520 -> ~560px` so larger post-redesign fonts
   do not crowd the notes area and stacked action buttons; exact value
   confirmed visually.
5. Drop redundant inline `color` on the flat buttons (already themed).

## Testing

- Extend `tests/test_update_dialog.py`:
  - Smoke test: `UpdateDialog` instantiates under a `QApplication` with a
    stub `UpdateCheckResult` and does not raise (Qt offscreen).
  - Guard: the module source contains no hardcoded `#rrggbb` hex literals.
- Extend `tests/test_styles.py`:
  - Assert `build_stylesheet` output contains a `variant="success"` rule.
  - Existing `test_build_stylesheet_contains_no_stray_hex_outside_tokens`
    already guards that the new rule uses only token hex.
- Keep the 6 `_MarkdownConverter` tests green.
- Full suite stays at 215+ passing (Qt offscreen).
- Visual verification: render the dialog in-process via `python main.py`
  (safe Qt capture). Final compiled-exe look verified by Tyler, per the
  2026-07-01 session note (no safe automated OS-level exe capture).

## Files touched

- `app/widgets/update_dialog.py` - the restyle.
- `app/styles.py` - add the `variant="success"` button rule.
- `tests/test_update_dialog.py`, `tests/test_styles.py` - extended coverage.
