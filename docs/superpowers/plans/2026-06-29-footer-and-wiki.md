# Footer + Wiki Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent 28px footer bar to every page in the app and populate the GitHub wiki with 9 documentation pages, then release v2.2.4.

**Architecture:** `FooterBar(QWidget)` lives in `app/widgets/footer.py` with a private `_LinkLabel(QLabel)` subclass. It is mounted once in `window.py`'s `_build_ui()` below the page stack (stretch=1), so it is always pinned to the bottom. The wiki is a separate git repo cloned to `%TEMP%\dato-toolkit.wiki`; 9 markdown files are written and pushed to `master`.

**Tech Stack:** PyQt6, Python `webbrowser`, git CLI, gh CLI

## Global Constraints

- Python 3.11+ / PyQt6 -- no new pip dependencies
- Footer fixed height: 28px; visible at minimum window size 900x600
- No existing page files modified -- only `app/window.py` and new `app/widgets/footer.py`
- Footer never hidden or toggled -- always shown
- Wiki branch: `master` (GitHub wiki repos default to master, not main)
- Version bump: `2.2.3` -> `2.2.4`

---

### Task 1: Create FooterBar widget

**Files:**
- Create: `app/widgets/footer.py`
- Create: `tests/test_footer.py`

**Interfaces:**
- Produces: `FooterBar` (importable as `from app.widgets.footer import FooterBar`), a `QWidget` subclass with `minimumHeight() == maximumHeight() == 28`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_footer.py
import sys
from PyQt6.QtWidgets import QApplication


def _app():
    return QApplication.instance() or QApplication(sys.argv)


def test_link_label_stores_url():
    _app()
    from app.widgets.footer import _LinkLabel
    label = _LinkLabel("Click me", "https://example.com", "#eaeaea")
    assert label._url == "https://example.com"
    assert label.text() == "Click me"


def test_footer_bar_fixed_height():
    _app()
    from app.widgets.footer import FooterBar
    footer = FooterBar()
    assert footer.minimumHeight() == 28
    assert footer.maximumHeight() == 28
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_footer.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.widgets.footer'`

- [ ] **Step 3: Write `app/widgets/footer.py`**

```python
"""Persistent footer bar shown on every page."""

from __future__ import annotations

import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class _LinkLabel(QLabel):
    """QLabel that opens a URL on left-click and changes color on hover via QSS."""

    def __init__(self, text: str, url: str, hover_color: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self._url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QLabel { color: #6e7681; font-family: 'Segoe UI'; font-size: 9pt; }"
            f"QLabel:hover {{ color: {hover_color}; }}"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            webbrowser.open(self._url)
        super().mousePressEvent(event)


class FooterBar(QWidget):
    """Persistent 28px footer bar with developer attribution and documentation link."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setObjectName("FooterBar")
        self.setStyleSheet(
            "#FooterBar { background-color: #0d1117; border-top: 1px solid #2f3650; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        dev_link = _LinkLabel(
            "Developed by Tyler Chambers",
            "https://github.com/tylerc515",
            "#eaeaea",
        )
        separator = QLabel(" · ")
        separator.setStyleSheet(
            "QLabel { color: #6e7681; font-family: 'Segoe UI'; font-size: 9pt; }"
        )
        docs_link = _LinkLabel(
            "Documentation",
            "https://github.com/tylerc515/dato-toolkit/wiki",
            "#2f80ed",
        )

        layout.addStretch(1)
        layout.addWidget(dev_link)
        layout.addWidget(separator)
        layout.addWidget(docs_link)
        layout.addStretch(1)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_footer.py -v
```

Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add app/widgets/footer.py tests/test_footer.py
git commit -m "Add FooterBar widget with attribution and docs links"
```

---

### Task 2: Wire FooterBar into window.py

**Files:**
- Modify: `app/window.py` -- add one import line and one `layout.addWidget` call

**Interfaces:**
- Consumes: `FooterBar` from `app.widgets.footer`

- [ ] **Step 1: Add import to `window.py`**

In `app/window.py`, find the existing widgets import at line 53:

```python
from app.widgets import OnboardingDialog, StepIndicator
```

Add one line below it:

```python
from app.widgets.footer import FooterBar
```

- [ ] **Step 2: Add FooterBar to layout in `_build_ui()`**

In `_build_ui()`, find this line (currently line 246):

```python
        layout.addWidget(self.stack, 1)
```

Insert immediately after it:

```python
        layout.addWidget(FooterBar())
```

The surrounding block in context, so you know exactly where this goes:

```python
        self.stack.addWidget(self.email_page)
        layout.addWidget(self.stack, 1)

        layout.addWidget(FooterBar())  # pinned to bottom, always visible

        self.dashboard_page.new_tracker_requested.connect(self._on_new_project)
```

- [ ] **Step 3: Run the full test suite**

```
pytest tests/ -v
```

Expected: All 96 existing tests pass, plus the 2 new footer tests = 98 total. Zero failures.

- [ ] **Step 4: Commit**

```bash
git add app/window.py
git commit -m "Mount FooterBar in main window below page stack"
```

---

### Task 3: Populate GitHub wiki

**Files:** (cloned wiki repo, outside main project directory)
- `Home.md`
- `Installation.md`
- `Tracksheet-Generator.md`
- `Update-Email-Generator.md`
- `Project-Files.md`
- `Settings.md`
- `Updating-the-App.md`
- `Troubleshooting.md`
- `For-Developers.md`

- [ ] **Step 1: Clone the wiki repo**

Run in PowerShell:

```powershell
cd $env:TEMP
git clone https://github.com/tylerc515/dato-toolkit.wiki.git
cd dato-toolkit.wiki
```

- [ ] **Step 2: Write Home.md**

```markdown
# DATO Toolkit

DATO Toolkit is a suite of desktop tools for NDE inspection teams at
Boiler Services and Inspection LLC. It parses TRACE system export files
and generates formatted Excel tracksheets and Word update emails for
outage inspections.

Built and maintained by [Tyler Chambers](https://github.com/tylerc515).

## Tools

- **Tracksheet Generator** - Import TRACE export CSV files, arrange
  sections, and generate a formatted Excel tracksheet matching the
  BSI standard template
- **Update Email Generator** - Generate formatted Word document status
  update emails pre-filled from your tracksheet project

## Quick Start

1. Download the latest `DATOToolkit_vX.X.X.exe` from
   [Releases](https://github.com/tylerc515/dato-toolkit/releases)
2. Double-click to run - no installation required
3. Import your TRACE export CSV files
4. Arrange sections and generate your tracksheet

## Pages

- [Installation](Installation)
- [Tracksheet Generator](Tracksheet-Generator)
- [Update Email Generator](Update-Email-Generator)
- [Project Files](Project-Files)
- [Settings](Settings)
- [Updating the App](Updating-the-App)
- [Troubleshooting](Troubleshooting)
- [For Developers](For-Developers)
```

- [ ] **Step 3: Write Installation.md**

```markdown
# Installation

DATO Toolkit is a portable application. No installation is required.

## Download

1. Go to the
   [Releases page](https://github.com/tylerc515/dato-toolkit/releases)
2. Download the latest `DATOToolkit_vX.X.X.exe` file
3. Save it anywhere on your computer (Desktop, shared drive, etc.)
4. Double-click to run

## System Requirements

- Windows 10 or Windows 11
- No Python or other software required
- Internet connection recommended for automatic updates

## Windows SmartScreen Warning

The first time you run the app, Windows may show a SmartScreen warning
saying "Windows protected your PC." This is normal for unsigned
applications.

To proceed:
1. Click **More info**
2. Click **Run anyway**

The app is safe to run. This warning appears because the executable
is not yet code-signed.

## Sharing with Your Team

Because the app is portable, you can share it by:
- Sending the .exe file directly
- Placing it on a shared network drive
- Linking your team to the Releases page

Everyone will be notified of updates automatically when they open the app.
```

- [ ] **Step 4: Write Tracksheet-Generator.md**

```markdown
# Tracksheet Generator

The Tracksheet Generator imports TRACE export CSV files and produces
a formatted Excel tracksheet matching the BSI standard template.

## Step 1 - Import Files

Drag and drop your TRACE export CSV files onto the import area, or
click to browse. You can import multiple files at once.

Each CSV file represents one boiler section. The app detects the section
name, customer, location, equipment, and date automatically from the file.

Supported files: `.csv` exports from the TRACE system only.

If a saved project exists for the same customer and equipment, the app
will offer to load it automatically.

## Step 2 - Arrange Sections

Drag section cards to set the order they appear in the tracksheet.
The live preview updates as you reorder.

**Title** - Auto-generated from customer, location, equipment, and year.
Editable directly.

**Additional Sections** - Expand this panel to add:
- Auxiliary Scope Items: additional inspection tasks outside standard
  tube sections (e.g. PT of composite ports, RT of economizer)
- Punchlist: carry-over action items from previous inspections

Click **+ Add Item** to add entries. Each item has a description
and optional notes field.

## Step 3 - Generate Tracker

Choose your output folder and filename, then click **Generate Tracker**.

Options:
- Output folder - defaults to your Desktop
- Filename - pre-filled from the project title
- Also export PDF - generates a PDF alongside the Excel file

After generation, click **Open File** to open the tracksheet in Excel.

## Tracksheet Format

The generated tracksheet includes:
- Customer, location, equipment, and date in the header
- Color-coded legend (Started = yellow, Complete = green)
- BSI logo in the top-left
- All boiler sections with elevation rows
- Status columns: Received, Verifications Run, Verifications Received,
  Final Printed, Wear Printed, Forecasting Printed, Trending Printed,
  Exec Updated, Notes
- Auxiliary scope items and punchlist at the bottom (if added)

## Saving and Reloading Projects

Projects save automatically as you work. To reload:
1. Import the same CSV files
2. The app detects the matching saved project and offers to load it
3. Click Yes to restore your section order, title, and additional items
```

- [ ] **Step 5: Write Update-Email-Generator.md**

```markdown
# Update Email Generator

The Update Email Generator creates a formatted Word document (.docx)
using the standard BSI NDE status update email structure.

## Accessing the Generator

- From the dashboard: click **Generate Update Email**
- After generating a tracksheet: click **Generate Update Email**
  on the success card
- From the navigation bar at the top of the app

## Linking a Tracker Project

If you have already generated a tracksheet for this project, the email
generator links to it automatically and pre-fills scope of work sections,
other scope items, and punchlist items.

If no project is linked, click **Load Project File** to browse for a
saved project (.json), or **Browse Recent Projects** to pick from
your recent history.

## Filling in the Email

**Project Info**
- Boiler name (auto-filled from linked project)
- Status date and time (defaults to today)

**Overall Status**
- Total initial data percentage (0-100)
- Summary text (auto-filled based on percentage, fully editable)

**Discovery Based on Scope Work**
- Add bullet items for findings from tube work
- Leave empty for "None reported at this time."

**Discovery Based on Visual Inspection**
- Same structure as scope work findings

**Scope of Work**
- One line per section, pre-filled from the linked project
- Status options per section:
  - No initial data received (default)
  - In progress
  - 100% of initial data received. Verifications complete. No issues noted.
  - Custom (free text)

**Other Scope Items**
- Pre-filled from Auxiliary Scope Items in the linked project
- Set a status line for each item

**Punchlist**
- Pre-filled from punchlist items in the linked project

## Generating the Document

Set your output filename and folder, then click **Generate Email Document**.
The output is a `.docx` file ready to open in Word and send.

## Email Format

- Opening paragraph with inspection date and time
- Color-coded legend (Complete = green, In Progress = yellow,
  Issues Noted = red)
- Boiler name heading (bold)
- Overall status summary
- Discovery sections
- Scope of work with per-section status lines
- Other scope items (purple heading)
- Punchlist (purple heading)
```

- [ ] **Step 6: Write Project-Files.md**

```markdown
# Project Files

DATO Toolkit saves project configurations so you can reload and
regenerate tracksheets without re-importing your CSV files.

## Where Projects Are Saved

```
%APPDATA%\DATOToolkit\projects\
```

On most Windows machines:

```
C:\Users\{YourName}\AppData\Roaming\DATOToolkit\projects\
```

Each project is a `.json` file named after the project title.

## What Is Saved

- Project title
- Customer, location, equipment, and date
- Section order and display names
- File paths to the original CSV files
- Auxiliary scope items and punchlist items
- Last used output folder and filename
- PDF export preference

## Reloading a Project

When you import CSV files matching a saved project (same customer,
location, equipment, and date), the app offers to load it automatically.
You can also load manually from the Update Email Generator using
**Load Project File**.

## If CSV Files Have Moved

If the app cannot find the original CSV files, it shows a warning with
a **Re-link** button for each missing file. Click **Re-link** to browse
to the file at its new location.

## Export History

Every generated file is logged at:

```
%APPDATA%\DATOToolkit\history.json
```

View the full history from the dashboard or the History nav item.
```

- [ ] **Step 7: Write Settings.md**

```markdown
# Settings

Access settings from the dashboard quick actions or the gear icon
in the header bar.

## General

**Default output folder** - Where generated files are saved.
Defaults to your Desktop.

**Default filename pattern** - Template for auto-generated filenames.
Tokens: `{customer}`, `{location}`, `{equipment}`, `{year}`.

**Default PDF export** - Whether to export a PDF alongside Excel by default.

**Remember window size and position** - Restores window position on next launch.

## Appearance

**Theme** - Dark, Light, or System.

**Font size** - Small, Medium, or Large.

## Updates

**Check for updates on launch** - Recommended to leave enabled.

**Check Now** - Manually trigger an update check.

## About

Shows the current version and a link to the GitHub repository.
```

- [ ] **Step 8: Write Updating-the-App.md**

```markdown
# Updating the App

DATO Toolkit checks for updates automatically on every launch.

## Update Notification

When a new version is available:
- The indicator dot in the top-right header turns yellow and pulses
- A banner appears: "DATO Toolkit vX.X.X is available"

## Installing an Update

Click **View & Install** on the banner. The update dialog shows:
- Current and new version numbers
- Release notes for the new version
- Install location (defaults to same folder as current .exe)
- Option to remove the old version after installing

Click **Download & Install** to begin. The download runs in the background
while you keep working. When complete, click **Install Now & Restart**.

The app closes, installs the new version, and relaunches automatically.

## Install Later

Click **Install Later** to download without installing immediately.
The next launch will offer to install the downloaded update.

## Manual Update

Download the latest version from the
[Releases page](https://github.com/tylerc515/dato-toolkit/releases)
and replace your existing .exe file.
```

- [ ] **Step 9: Write Troubleshooting.md**

```markdown
# Troubleshooting

## "Windows protected your PC" on launch

Click **More info** then **Run anyway**.
See [Installation](Installation) for details.

## "Generation Failed - Permission denied"

The output file is already open in Excel. Close it and try again.
If the issue persists, choose a different output folder in Step 3.

## CSV file shows an error on import

Check that:
- The file is a direct export from the TRACE system
- The file is not corrupted or partially downloaded
- The file extension is .csv

## Sections are missing elevations

Make sure you are using the latest version of DATO Toolkit.
Check [Releases](https://github.com/tylerc515/dato-toolkit/releases).

## Update check fails silently

The update check requires an internet connection. On restricted networks
the check fails silently and the dot stays gray. Check for updates manually
at the [Releases page](https://github.com/tylerc515/dato-toolkit/releases).

## App crashes on launch

Try running as Administrator (right-click the .exe, Run as administrator).
If the issue persists, check the log file:

```
%APPDATA%\DATOToolkit\logs\app.log
```

Send the log contents to Tyler Chambers for support.

## Saved project won't load - CSV files missing

Use the **Re-link** button next to each missing file and browse to
the new location.

## Contact

GitHub: [tylerc515](https://github.com/tylerc515)
```

- [ ] **Step 10: Write For-Developers.md**

```markdown
# For Developers

## Repository

https://github.com/tylerc515/dato-toolkit

## Stack

- Python 3.11+
- PyQt6 - GUI framework
- openpyxl - Excel generation
- python-docx - Word document generation
- PyInstaller - portable .exe packaging
- requests - GitHub Releases API
- pandas - CSV parsing

## Project Structure

```
dato-toolkit/
├── main.py
├── app/
│   ├── __init__.py        # Version string - only place to set version
│   ├── window.py          # Main window, frameless, custom title bar
│   ├── splash.py          # Launch splash screen
│   ├── logo.py            # SVG logo rendering via QSvgRenderer
│   ├── parser.py          # TRACE CSV parsing (dynamic row detection)
│   ├── builder.py         # Excel tracksheet generation
│   ├── updater.py         # Update checker and downloader
│   ├── project.py         # Project config save/load
│   ├── history.py         # Export history log
│   ├── styles.py          # QSS stylesheet
│   └── pages/             # One file per app page
├── scripts/
│   ├── generate_icon.py   # Icon generation via PyQt6 (no Cairo needed)
│   └── generate_email_py.py  # Word email generation via python-docx
├── assets/
│   ├── logo.svg           # TC mark (wide aspect ratio)
│   └── icon.ico           # App icon
├── reference_template.xlsx   # Excel format reference (bundled in exe)
├── bsi_logo.jpg              # BSI logo for tracksheet header
└── build.bat                 # PyInstaller build script
```

## Building from Source

```bash
pip install -r requirements.txt
python main.py        # Run in development
pytest                # Run tests
build.bat             # Build portable .exe
```

## Versioning

Version is defined only in `app/__init__.py`:

```python
__version__ = "2.x.x"
```

Use semantic versioning. Tag every release and attach the .exe to
the GitHub release.

## Releasing

```bash
git tag vX.X.X
git push origin main --tags
gh release create vX.X.X dist/DATOToolkit_vX.X.X.exe \
  --title "vX.X.X" \
  --notes "## What's New
- Change one
- Change two"
```

## Design Tokens

| Token | Value |
|---|---|
| Background | #1a1a2e |
| Surface | #16213e |
| Accent blue | #2f80ed |
| Accent red-pink | #e94560 |
| Success green | #00B050 |
| Text | #eaeaea |
| Font | Segoe UI |
```

- [ ] **Step 11: Commit and push the wiki**

```bash
git add -A
git commit -m "Add full documentation wiki"
git push origin master
```

- [ ] **Step 12: Verify in browser**

Visit https://github.com/tylerc515/dato-toolkit/wiki and confirm all 9 pages appear in the sidebar:
Home, Installation, Tracksheet Generator, Update Email Generator, Project Files, Settings, Updating the App, Troubleshooting, For Developers.

---

### Task 4: Bump version, build, and release

**Files:**
- Modify: `app/__init__.py` (one line)

- [ ] **Step 1: Bump version in `app/__init__.py`**

Change:
```python
__version__ = "2.2.3"
```
to:
```python
__version__ = "2.2.4"
```

- [ ] **Step 2: Run the full test suite**

```
pytest tests/ -v
```

Expected: All 98 tests pass (96 pre-existing + 2 footer tests). Zero failures.

- [ ] **Step 3: Build**

```
cmd /c build.bat
```

Expected: `dist/DATOToolkit_v2.2.4.exe` appears. Build log ends with success.

- [ ] **Step 4: Commit, tag, push, and release**

```bash
git add app/__init__.py
git commit -m "Add footer attribution and wiki link, publish documentation wiki (v2.2.4)"
git tag v2.2.4
git push origin main --tags
gh release create v2.2.4 "dist/DATOToolkit_v2.2.4.exe" \
  --title "v2.2.4 - Footer and Documentation" \
  --notes "## What's New

- Added footer on every page with developer attribution and documentation link
- Published full documentation wiki on GitHub"
```
