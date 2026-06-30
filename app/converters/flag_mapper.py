"""ATS flag code to Standard Format code mapping."""
from __future__ import annotations

import difflib
from dataclasses import dataclass

DEFAULT_ATS_FLAG_MAP: dict[str, str] = {}

STANDARD_SYMBOL_DESCRIPTIONS: dict[str, str] = {
    ";": "SCAFFOLD INTERFERENCE",
}

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
