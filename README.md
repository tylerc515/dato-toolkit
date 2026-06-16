# DATO Toolkit

DATO Toolkit is a suite of field operations tools for NDE inspection teams.
Generate tracksheets, update emails, and manage outage scope from TRACE export data.

## Features

- **Drag-and-drop import** of TRACE export `.csv` files, with per-file
  error cards so a bad file never crashes the app
- **Arrange sections** with a drag-to-reorder list, inline renaming, and a
  live preview of the generated tracker
- **Auto-generated tracker title** based on the customer, location, boiler,
  and inspection date (editable before generating)
- **One-click generation** of an Excel tracker that matches the standard
  tracksheet layout exactly (column headers, section rows, borders, and
  formatting)
- Optional **PDF export** alongside the Excel file
- **Project autosave** — pick up where you left off if you reopen the same
  inspection's files later
- Built-in **update checks** against GitHub Releases
- Dark theme UI with onboarding and contextual help panels

## Getting Started

### Requirements

- Python 3.11+
- Windows (for the packaged `.exe`); the source also runs on macOS/Linux

### Run from source

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Build a standalone executable

```bash
pip install -r requirements.txt
build.bat
```

The packaged executable will be created at `dist/DATOToolkit_v2.0.0.exe`.

## Usage

1. **Import Files** — drag your TRACE export `.csv` files onto the drop
   zone, or click it to browse. Each file becomes one section of the
   tracker.
2. **Arrange Sections** — drag sections into the order you want, rename them
   if needed, and review the tracker title.
3. **Generate Tracker** — pick an output folder and filename, optionally
   enable PDF export, and click **Generate Tracker**.

When generation finishes, you can open the file, open its folder, or start a
new project directly from the app.

## Running Tests

```bash
pip install -r requirements.txt
pytest
```

## License

Released under the [MIT License](LICENSE).
