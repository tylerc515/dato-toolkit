"""ATS flag code to Standard Format code mapping."""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_ATS_FLAG_MAP: dict[str, str] = {
    "NC": "<",   # Not clean
    "RF": "(",   # Refractory
    "RT": ")",   # Recessed tube
    "SI": ";",   # Signal interrupt
    "ST": "+",   # Stud
    "NS": "[",   # No scan
}


@dataclass
class FlagMappingResult:
    known: dict[str, str]    # flags auto-mapped from DEFAULT_ATS_FLAG_MAP
    unknown: dict[str, str]  # {ats_code: ats_description} not in defaults
    final: dict[str, str]    # complete mapping after user review (known only until confirmed)


def build_flag_mapping(ats_flags: dict[str, str]) -> FlagMappingResult:
    """Split ats_flags into known (auto-mapped) and unknown (need user review).

    Args:
        ats_flags: {ats_code: description} from ATSParseResult.ats_flags

    Returns:
        FlagMappingResult where final contains only the auto-mapped codes
        until the user reviews unknowns and calls update on the result.
    """
    known: dict[str, str] = {}
    unknown: dict[str, str] = {}
    for code, description in ats_flags.items():
        if code in DEFAULT_ATS_FLAG_MAP:
            known[code] = DEFAULT_ATS_FLAG_MAP[code]
        else:
            unknown[code] = description
    return FlagMappingResult(known=known, unknown=unknown, final=dict(known))
