# Footer + Wiki Documentation - Design Spec

**Date:** 2026-06-29
**Version target:** 2.2.4

---

## Overview

Two independent deliverables:

1. A persistent `FooterBar` widget added to the main window -- visible on every page.
2. Full GitHub wiki populated with 9 documentation pages.

---

## Part 1 - App Footer

### Widget: `app/widgets/footer.py`

Create `FooterBar(QWidget)`. The class is self-contained; `window.py` imports and mounts it.

**Visual spec:**
- Height: 28px fixed
- Background: `#0d1117`
- Top border: `1px solid #2f3650`
- Font: Segoe UI 9pt
- Content: horizontally and vertically centered

**Content:**

Two `QLinkLabel` instances (see below) separated by a muted ` · ` divider:

| Label | URL | Muted color | Hover color |
|---|---|---|---|
| Developed by Tyler Chambers | https://github.com/tylerc515 | `#6e7681` | `#eaeaea` |
| Documentation | https://github.com/tylerc515/dato-toolkit/wiki | `#6e7681` | `#2f80ed` |

**`QLinkLabel` subclass** (defined in `footer.py`):
- Inherits `QLabel`
- Constructor takes `text`, `url`, `hover_color`
- Sets `PointingHandCursor`
- Applies QSS with both normal and `:hover` color in one `setStyleSheet` call
- Calls `webbrowser.open(url)` on `mousePressEvent`

### Wiring in `window.py`

In `_build_ui()`, after `layout.addWidget(self.stack, 1)` and before `self.setCentralWidget(central)`:

```python
from app.widgets.footer import FooterBar
...
layout.addWidget(FooterBar())
```

The footer is added to the same `QVBoxLayout` as the header and page stack. Because the stack has stretch factor 1 and the footer has none, the footer is always pinned to the bottom and never overlapped.

`size_grip` is repositioned in `resizeEvent` (already present); it sits in the bottom-right corner of the window chrome and does not overlap the footer.

### Constraints
- No existing page files are modified.
- No visibility toggling -- the footer is always shown.
- Must remain visible at minimum window size (900x600).

---

## Part 2 - GitHub Wiki

**Repo:** `https://github.com/tylerc515/dato-toolkit.wiki.git`
**Branch:** `master` (wiki repos default to master)

### Pages (9 total)

| File | Title |
|---|---|
| `Home.md` | DATO Toolkit |
| `Installation.md` | Installation |
| `Tracksheet-Generator.md` | Tracksheet Generator |
| `Update-Email-Generator.md` | Update Email Generator |
| `Project-Files.md` | Project Files |
| `Settings.md` | Settings |
| `Updating-the-App.md` | Updating the App |
| `Troubleshooting.md` | Troubleshooting |
| `For-Developers.md` | For Developers |

All content is specified verbatim in the implementation prompt. No content decisions remain.

**Workflow:**
1. Clone wiki repo to `%TEMP%\dato-toolkit.wiki`
2. Write all 9 files
3. `git add -A && git commit -m "Add full documentation wiki" && git push origin master`

---

## Post-implementation checklist

1. Run `python main.py` -- verify footer on every page, links open correct URLs, no overlap at 900x600.
2. Visit `https://github.com/tylerc515/dato-toolkit/wiki` -- verify all 9 pages present and linked.
3. Run `pytest` -- all existing tests pass.
4. Bump `__version__` to `2.2.4` in `app/__init__.py`.
5. `build.bat` -> `git commit` -> `git tag v2.2.4` -> `git push origin main --tags` -> `gh release create`.
