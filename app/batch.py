"""Batch scanning and generation of trackers from a folder of TRACE export CSVs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.builder import TrackerData, TrackerSection, build_tracker
from app.history import HistoryEntry, add_history_entry
from app.parser import TraceFileData, TraceParseError, parse_trace_csv
from app.pdf_export import export_tracker_pdf
from app.project import ProjectConfig, ProjectSection, sanitize_filename
from app.titlegen import generate_title
from app.validation import validate_tracker_output

XLSX_SUFFIX = ".xlsx"
PDF_SUFFIX = ".pdf"


@dataclass
class BatchFileError:
    """A CSV file that could not be parsed during a folder scan."""

    path: str
    error: str


@dataclass
class BatchProjectGroup:
    """A set of TRACE export files sharing the same project metadata."""

    customer: str
    location: str
    equipment: str
    date: str
    title: str
    files: list[TraceFileData] = field(default_factory=list)


@dataclass
class BatchScanResult:
    """The outcome of scanning a folder for TRACE export CSVs."""

    groups: list[BatchProjectGroup] = field(default_factory=list)
    errors: list[BatchFileError] = field(default_factory=list)


@dataclass
class BatchGenerateResult:
    """The outcome of generating a tracker for one project group."""

    title: str
    xlsx_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None


def group_files(files: list[TraceFileData]) -> list[BatchProjectGroup]:
    """Group parsed TRACE files by project metadata, preserving first-seen order."""
    groups: list[BatchProjectGroup] = []
    index: dict[tuple[str, str, str, str], BatchProjectGroup] = {}
    for file in files:
        key = (file.company_name, file.mill_location, file.boiler_name, file.inspection_date)
        group = index.get(key)
        if group is None:
            group = BatchProjectGroup(
                customer=file.company_name,
                location=file.mill_location,
                equipment=file.boiler_name,
                date=file.inspection_date,
                title=generate_title(file.company_name, file.mill_location, file.boiler_name, file.inspection_date),
            )
            index[key] = group
            groups.append(group)
        group.files.append(file)
    return groups


def scan_folder(folder: str | Path) -> BatchScanResult:
    """Parse every CSV file directly inside `folder` and group them by project.

    Files are processed in name order, which also determines each project's
    section order (since batch mode has no manual reordering step).
    """
    files: list[TraceFileData] = []
    errors: list[BatchFileError] = []
    for path in sorted(Path(folder).glob("*.csv")):
        try:
            files.append(parse_trace_csv(path))
        except TraceParseError as exc:
            errors.append(BatchFileError(path=str(path), error=str(exc)))
    return BatchScanResult(groups=group_files(files), errors=errors)


def generate_group(group: BatchProjectGroup, output_dir: str | Path, export_pdf: bool) -> BatchGenerateResult:
    """Build the tracker (and optionally a PDF) for one project group.

    Also saves a project config and a history entry, matching the wizard's
    normal Step 3 behavior, so batch-generated trackers show up on the
    dashboard like any other.
    """
    sections = [
        TrackerSection(name=file.boiler_section, elevations=[e.label for e in file.elevations])
        for file in group.files
    ]
    data = TrackerData(
        title=group.title,
        customer=group.customer,
        location=group.location,
        equipment=group.equipment,
        date=group.date,
        sections=sections,
    )

    output_dir = Path(output_dir)
    filename = sanitize_filename(group.title) + XLSX_SUFFIX
    xlsx_path = output_dir / filename
    pdf_path = xlsx_path.with_suffix(PDF_SUFFIX) if export_pdf else None

    try:
        build_tracker(data, xlsx_path)
        pdf_result = export_tracker_pdf(xlsx_path, pdf_path, data) if pdf_path is not None else None
    except OSError as exc:
        return BatchGenerateResult(title=group.title, error=str(exc))

    warnings = validate_tracker_output(data, xlsx_path, pdf_result)

    project_sections = [
        ProjectSection(
            name=file.boiler_section,
            file_path=file.source_path,
            display_name=file.boiler_section,
            elevations=[e.label for e in file.elevations],
        )
        for file in group.files
    ]
    config = ProjectConfig(
        title=group.title,
        customer=group.customer,
        location=group.location,
        equipment=group.equipment,
        date=group.date,
        sections=project_sections,
        output_directory=str(output_dir),
        output_filename=filename,
        export_pdf=export_pdf,
    )
    config.save()

    elevation_count = sum(len(section.elevations) for section in sections)
    add_history_entry(
        HistoryEntry(
            title=group.title,
            customer=group.customer,
            location=group.location,
            equipment=group.equipment,
            date=group.date,
            elevation_count=elevation_count,
            output_path=str(xlsx_path),
            pdf_path=str(pdf_result) if pdf_result else "",
            generated_at=datetime.now().isoformat(),
        )
    )

    return BatchGenerateResult(title=group.title, xlsx_path=xlsx_path, pdf_path=pdf_result, warnings=warnings)
