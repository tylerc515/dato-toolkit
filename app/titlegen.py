"""Auto-generation of tracker titles from TRACE export metadata."""

from __future__ import annotations

import re

# Words ignored when abbreviating a boiler name (e.g. "Recovery Boiler #2" -> "RB2")
GENERIC_BOILER_WORDS = {"the", "a", "an", "of", "no", "no.", "number", "unit"}

YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
DIGITS_PATTERN = re.compile(r"\d+")


def company_initials(company_name: str) -> str:
    """'Example Paper' -> 'EP'."""
    return "".join(word[0].upper() for word in company_name.split() if word)


def location_city(mill_location: str) -> str:
    """'Anytown, LA' -> 'ANYTOWN'."""
    city = mill_location.split(",")[0].strip()
    return city.upper()


def boiler_abbreviation(boiler_name: str) -> str:
    """'Recovery Boiler #2' -> 'RB2'. Falls back to the full name if unparseable."""
    digits_match = DIGITS_PATTERN.search(boiler_name)
    words = [w for w in re.split(r"[\s#]+", boiler_name) if w]

    letters = ""
    for word in words:
        if word.isdigit() or word.lower().strip(".") in GENERIC_BOILER_WORDS:
            continue
        letters += word[0].upper()
        if len(letters) >= 2:
            break

    if digits_match and letters:
        return f"{letters}{digits_match.group()}"
    return boiler_name.strip()


def inspection_year(inspection_date: str) -> str:
    """'June 2026' -> '2026'. Falls back to the full date string if no year is found."""
    match = YEAR_PATTERN.search(inspection_date)
    return match.group(0) if match else inspection_date.strip()


def generate_title(company_name: str, mill_location: str, boiler_name: str, inspection_date: str) -> str:
    """Build the default tracker title, e.g. 'EP ANYTOWN RB2 — 2026 OUTAGE NDE TRACKSHEET'."""
    return (
        f"{company_initials(company_name)} {location_city(mill_location)} "
        f"{boiler_abbreviation(boiler_name)} — {inspection_year(inspection_date)} OUTAGE NDE TRACKSHEET"
    )
