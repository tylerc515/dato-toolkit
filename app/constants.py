"""Shared constants for TRACE CSV parsing and tracker generation."""

# Column indices (0-indexed) within a TRACE export CSV
METADATA_LABEL_COL = 5
METADATA_VALUE_COL = 7
ELEVATION_LABEL_COL = 2
ROLE_COL = 4
MEASUREMENT_START_COL = 5

# Metadata row labels as they appear in TRACE exports
LABEL_COMPANY_NAME = "Company Name:---->"
LABEL_MILL_LOCATION = "Mill Location:---->"
LABEL_BOILER_NAME = "Boiler Name:---->"
LABEL_INSPECTION_DATE = "Inspection Date:---->"
LABEL_BOILER_SECTION = "Boiler Section:---->"
LABEL_NUMBER_OF_TUBES = "Number of Tubes:---->"
LABEL_NUMBERING_DIRECTION = "Numbering Direction:---->"
LABEL_NDE_LABORATORY = "NDE Laboratory:---->"

UT_TECH_NAME_MARKER = "UT Tech Name:"
ROLE_LEFT = "LEFT"
ROLE_CNTR = "CNTR"
ROLE_RGHT = "RGHT"

# Tracker output column headers (Step 8 onward of the generated sheet)
TRACKER_COLUMNS = [
    "Elevation",
    "Received",
    "Verifications Run",
    "Verifications Received",
    "Final Printed",
    "Wear Printed",
    "Forecasting Printed",
    "Trending Printed",
    "Exec Updated",
    "Notes",
]

TRACKER_SHEET_NAME = "Tracker"
