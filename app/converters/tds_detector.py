import csv
from pathlib import Path
from typing import Literal

_SCAN_ROWS = 15
_SIGNAL = "Company Name:"


def detect_tds_format(filepath: str | Path) -> Literal["old", "new"]:
    """Scan the first ~15 rows for the substring "Company Name:".

    Present -> "new" (TDS 5.3+); absent -> "old" (pre-5.3).
    """
    with open(filepath, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= _SCAN_ROWS:
                break
            for cell in row:
                if _SIGNAL in cell:
                    return "new"
    return "old"
