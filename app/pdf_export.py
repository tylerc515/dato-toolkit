"""PDF export for generated tracker workbooks.

Tries LibreOffice headless conversion first (produces a PDF that matches the
Excel layout exactly). If LibreOffice isn't installed or conversion fails,
falls back to a simple reportlab-generated table with the same content.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.builder import TrackerData
from app.constants import TRACKER_COLUMNS

LIBREOFFICE_EXECUTABLE_NAMES = ["soffice", "libreoffice"]
LIBREOFFICE_TIMEOUT_SECONDS = 60

logger = logging.getLogger(__name__)


def _find_libreoffice() -> Optional[str]:
    """Return the path to a LibreOffice executable, if one is on PATH."""
    for name in LIBREOFFICE_EXECUTABLE_NAMES:
        path = shutil.which(name)
        if path:
            return path
    return None


def _export_with_libreoffice(xlsx_path: Path, pdf_path: Path, executable: str) -> bool:
    """Convert xlsx_path to a PDF at pdf_path using LibreOffice headless. Returns success."""
    try:
        result = subprocess.run(
            [executable, "--headless", "--convert-to", "pdf", "--outdir", str(pdf_path.parent), str(xlsx_path)],
            capture_output=True,
            timeout=LIBREOFFICE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("LibreOffice PDF conversion failed: %s", exc)
        return False

    if result.returncode != 0:
        logger.warning("LibreOffice PDF conversion exited with %s: %s", result.returncode, result.stderr)
        return False

    converted = pdf_path.parent / (xlsx_path.stem + ".pdf")
    if converted.exists() and converted != pdf_path:
        converted.replace(pdf_path)
    return pdf_path.exists()


def _export_with_reportlab(data: TrackerData, pdf_path: Path) -> None:
    """Render a simple table-based PDF from tracker data as a fallback."""
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(data.title, styles["Title"]),
        Paragraph(f"Customer: {data.customer}", styles["Normal"]),
        Paragraph(f"Location: {data.location}", styles["Normal"]),
        Paragraph(f"Equipment: {data.equipment}", styles["Normal"]),
        Paragraph(f"Project Date: {data.date}", styles["Normal"]),
        Spacer(1, 12),
    ]

    table_data = [TRACKER_COLUMNS]
    style_commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
    blank_row = [""] * (len(TRACKER_COLUMNS) - 1)
    row_index = 1
    for section in data.sections:
        table_data.append([section.name] + blank_row)
        style_commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.whitesmoke))
        style_commands.append(("FONTNAME", (0, row_index), (0, row_index), "Helvetica-Bold"))
        row_index += 1
        for elevation in section.elevations:
            table_data.append([elevation] + blank_row)
            row_index += 1

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle(style_commands))
    elements.append(table)

    doc = SimpleDocTemplate(str(pdf_path), pagesize=landscape(letter))
    doc.build(elements)


def export_tracker_pdf(xlsx_path: str | Path, pdf_path: str | Path, data: TrackerData) -> Path:
    """Export a PDF version of the tracker, trying LibreOffice before reportlab."""
    xlsx_path = Path(xlsx_path)
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    executable = _find_libreoffice()
    if executable and _export_with_libreoffice(xlsx_path, pdf_path, executable):
        return pdf_path

    logger.info("Using reportlab fallback for PDF export of %s", pdf_path)
    _export_with_reportlab(data, pdf_path)
    return pdf_path
