"""ATS flag code to Standard Format code mapping."""
from __future__ import annotations

import difflib
from dataclasses import dataclass

DEFAULT_ATS_FLAG_MAP: dict[str, str] = {
    "NC": "<",   # Not clean
    "RF": "(",   # Refractory
    "RT": ")",   # Recessed tube
    "ST": "+",   # Stud
    "NS": "[",   # No scan
}

STANDARD_SYMBOL_DESCRIPTIONS: dict[str, str] = {
    ";": "SCAFFOLD INTERFERENCE",
    "(": "RF",
    ")": "RT",
    "+": "ST",
    "[": "NS",
    "/": "TC",
    "<": "NC",
}


@dataclass
class FlagMappingResult:
    known: dict[str, str]      # exact matches from DEFAULT_ATS_FLAG_MAP
    suggested: dict[str, str]  # smart-matched by description -- pre-filled but needs confirm
    unknown: dict[str, str]    # no match found at all, field is empty
    final: dict[str, str]      # complete mapping after user review (known only until confirmed)


def build_flag_mapping(ats_flags: dict[str, str]) -> FlagMappingResult:
    """Split ats_flags into known, suggested, and unknown tiers.

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
