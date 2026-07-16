"""ATS flag code to Standard Format code mapping."""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

DEFAULT_ATS_FLAG_MAP: dict[str, str] = {}


def _build_symbol_descriptions() -> dict[str, str]:
    """Parse legend block rows from the reference file to build {symbol: description}."""
    from app.converters.standard_format_writer import load_standard_legend_block

    result: dict[str, str] = {}
    primary = re.compile(r"\s*(\S+)\s+means\s+(.+?)\.?\s*$")
    fallback = re.compile(r"\s*(\S+)\s+(.+?)\.?\s*$")

    for row in load_standard_legend_block():
        # Check col index 1 (left column) and col index 6 (right column)
        for col_idx in (1, 6):
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip()
            if not cell:
                continue
            m = primary.match(cell)
            if m:
                result[m.group(1)] = m.group(2).rstrip(".")
                continue
            # Fallback only when "means" is absent from the cell
            if "means" not in cell:
                m2 = fallback.match(cell)
                if m2:
                    result[m2.group(1)] = m2.group(2).rstrip(".")

    for sym in ("R", "V", "N"):
        result.pop(sym, None)
    return result


STANDARD_SYMBOL_DESCRIPTIONS: dict[str, str] = _build_symbol_descriptions()

# Session memory: (ats_code, description_upper) -> std_symbol
_session_confirmed: dict[tuple[str, str], str] = {}


@dataclass
class FlagMappingResult:
    known: dict[str, str]      # exact matches from DEFAULT_ATS_FLAG_MAP
    suggested: dict[str, str]  # session memory or description-matched -- pre-filled but needs confirm
    unknown: dict[str, str]    # no match found at all, field is empty
    final: dict[str, str]      # complete mapping after user review (known only until confirmed)


def confirm_mapping(ats_code: str, description: str, std_symbol: str) -> None:
    """Record a user-confirmed mapping for this session."""
    _session_confirmed[(ats_code, description.upper())] = std_symbol


def confirm_session_mappings(
    confirmed: dict[str, str],
    ats_flags: dict[str, str],
) -> None:
    """Record all confirmed mappings for this session.

    Args:
        confirmed: {ats_code: std_symbol} from FlagReviewWidget.mappings_confirmed
        ats_flags: {ats_code: description} from ATSParseResult.ats_flags
    """
    for ats_code, std_symbol in confirmed.items():
        description = ats_flags.get(ats_code, "")
        confirm_mapping(ats_code, description, std_symbol)


def clear_session_mappings() -> None:
    """Reset session memory (call between tests or on app restart)."""
    _session_confirmed.clear()


def build_flag_mapping(ats_flags: dict[str, str]) -> FlagMappingResult:
    """Split ats_flags into known, suggested, and unknown tiers.

    Tier 0: session memory (previously confirmed by user this session) -> suggested
    Tier 1: exact code match in DEFAULT_ATS_FLAG_MAP -> known
    Tier 2: description fuzzy match against STANDARD_SYMBOL_DESCRIPTIONS -> suggested
    Tier 3: no match found -> unknown

    Args:
        ats_flags: {ats_code: description} from ATSParseResult.ats_flags

    Returns:
        FlagMappingResult where final contains only the auto-mapped codes
        until the user reviews suggested/unknowns and confirms.
    """
    known: dict[str, str] = {}
    suggested: dict[str, str] = {}
    unknown: dict[str, str] = {}

    for code, description in ats_flags.items():
        # Tier 0: session memory
        session_key = (code, description.upper())
        if session_key in _session_confirmed:
            suggested[code] = _session_confirmed[session_key]
            continue

        # Tier 1: exact code match
        if code in DEFAULT_ATS_FLAG_MAP:
            known[code] = DEFAULT_ATS_FLAG_MAP[code]
            continue

        # Tier 2: description fuzzy match against STANDARD_SYMBOL_DESCRIPTIONS
        best_symbol = None
        best_ratio = 0.0
        for symbol, std_desc in STANDARD_SYMBOL_DESCRIPTIONS.items():
            ratio = difflib.SequenceMatcher(
                None, description.upper(), std_desc.upper()
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_symbol = symbol
        if best_ratio > 0.8 and best_symbol is not None:
            suggested[code] = best_symbol
            continue

        # Tier 3: unknown
        unknown[code] = description

    return FlagMappingResult(
        known=known,
        suggested=suggested,
        unknown=unknown,
        final=dict(known),
    )


def check_known_symbols(flags_found: set[str]) -> FlagMappingResult:
    """Split TEAM flag symbols into known/unknown tiers.

    TEAM inspection files already carry Standard Format symbols, so no
    code-to-symbol translation is needed (unlike ATS). There is no
    per-flag description text to fuzzy-match against, so there is no
    Tier-2 smart-match tier for TEAM: suggested stays empty and nothing
    is pre-filled for an unknown symbol.

    Args:
        flags_found: set of flag symbols encountered in the TEAM file.

    Returns:
        FlagMappingResult where known maps each recognized symbol to
        itself, unknown maps each unrecognized symbol to "" (empty,
        pending manual review via FlagReviewWidget), suggested is
        always empty, and final mirrors known.
    """
    known = {s: s for s in flags_found if s in STANDARD_SYMBOL_DESCRIPTIONS}
    suggested: dict[str, str] = {}
    unknown = {s: "" for s in flags_found if s not in STANDARD_SYMBOL_DESCRIPTIONS}

    return FlagMappingResult(
        known=known,
        suggested=suggested,
        unknown=unknown,
        final=dict(known),
    )
