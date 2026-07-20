"""Tests for ATS comment code mapping logic."""
from __future__ import annotations


def test_default_map_is_empty():
    from app.converters.comment_code_mapper import DEFAULT_ATS_COMMENT_CODE_MAP
    assert DEFAULT_ATS_COMMENT_CODE_MAP == {}


def test_default_ats_flag_map_is_empty():
    from app.converters.comment_code_mapper import DEFAULT_ATS_COMMENT_CODE_MAP
    assert DEFAULT_ATS_COMMENT_CODE_MAP == {}


def test_default_map_contains_no_codes():
    from app.converters.comment_code_mapper import DEFAULT_ATS_COMMENT_CODE_MAP
    assert len(DEFAULT_ATS_COMMENT_CODE_MAP) == 0
    for code in ("NC", "RF", "RT", "NS", "ST"):
        assert code not in DEFAULT_ATS_COMMENT_CODE_MAP


def test_standard_symbol_descriptions_excludes_rvn():
    """R, V, N must not appear in STANDARD_SYMBOL_DESCRIPTIONS (picker/matching exclusion)."""
    from app.converters.comment_code_mapper import STANDARD_SYMBOL_DESCRIPTIONS
    assert "R" not in STANDARD_SYMBOL_DESCRIPTIONS, "R should be excluded from picker/matching"
    assert "V" not in STANDARD_SYMBOL_DESCRIPTIONS, "V should be excluded from picker/matching"
    assert "N" not in STANDARD_SYMBOL_DESCRIPTIONS, "N should be excluded from picker/matching"


def test_standard_symbol_descriptions_has_scaffold():
    """';' maps to 'Structural interference' as parsed from the reference file."""
    from app.converters.comment_code_mapper import STANDARD_SYMBOL_DESCRIPTIONS
    assert STANDARD_SYMBOL_DESCRIPTIONS[";"] == "Structural interference"


def test_standard_symbol_descriptions_has_expected_entries():
    """Parsed table has at least 20 entries covering all main symbols."""
    from app.converters.comment_code_mapper import STANDARD_SYMBOL_DESCRIPTIONS
    assert len(STANDARD_SYMBOL_DESCRIPTIONS) >= 20
    # Spot-check key entries parsed from the reference file
    assert STANDARD_SYMBOL_DESCRIPTIONS[";"] == "Structural interference"
    assert STANDARD_SYMBOL_DESCRIPTIONS["*"] == "Scaffold was interfering"
    # '!' uses the fallback pattern (no 'means' keyword in the reference)
    assert "!" in STANDARD_SYMBOL_DESCRIPTIONS


def test_build_mapping_structural_interference_suggested():
    """Codes whose description matches STRUCTURAL INTERFERENCE go to Tier 2 (suggested)."""
    from app.converters.comment_code_mapper import build_comment_code_mapping
    result = build_comment_code_mapping({"SI": "STRUCTURAL INTERFERENCE"})
    assert result.known == {}
    assert result.suggested == {"SI": ";"}
    assert result.final == {}


def test_build_mapping_with_unknown():
    from app.converters.comment_code_mapper import build_comment_code_mapping
    result = build_comment_code_mapping({"SI": "STRUCTURAL INTERFERENCE", "XX": "SOME NEW FLAG"})
    assert "XX" in result.unknown
    assert "SI" in result.suggested
    assert "XX" not in result.known
    assert result.final == {}


def test_build_mapping_empty():
    from app.converters.comment_code_mapper import build_comment_code_mapping
    result = build_comment_code_mapping({})
    assert result.known == {}
    assert result.unknown == {}
    assert result.final == {}


def test_build_mapping_only_unknown():
    from app.converters.comment_code_mapper import build_comment_code_mapping
    result = build_comment_code_mapping({"ZZ": "MYSTERY"})
    assert result.known == {}
    assert "ZZ" in result.unknown
    assert result.final == {}


def test_flag_maps_are_consistent():
    """Every symbol in DEFAULT_ATS_COMMENT_CODE_MAP must appear in STANDARD_SYMBOL_DESCRIPTIONS."""
    from app.converters.comment_code_mapper import DEFAULT_ATS_COMMENT_CODE_MAP, STANDARD_SYMBOL_DESCRIPTIONS
    for ats_code, std_symbol in DEFAULT_ATS_COMMENT_CODE_MAP.items():
        assert std_symbol in STANDARD_SYMBOL_DESCRIPTIONS, (
            f"DEFAULT_ATS_COMMENT_CODE_MAP maps {ats_code!r} to {std_symbol!r}, "
            f"but {std_symbol!r} is not in STANDARD_SYMBOL_DESCRIPTIONS"
        )


def test_smart_flag_matching_by_description():
    """ATS codes not in DEFAULT_ATS_COMMENT_CODE_MAP but matching by description go to suggested."""
    from app.converters.comment_code_mapper import build_comment_code_mapping
    # "STRUCTURAL INTERFERENCE" is an exact-case-insensitive match for ";" in the parsed table
    result = build_comment_code_mapping({"SI": "STRUCTURAL INTERFERENCE"})
    assert "SI" in result.suggested
    assert result.suggested["SI"] == ";"
    assert "SI" not in result.known
    assert "SI" not in result.unknown


def test_three_tier_mixed():
    """Suggested and unknown are populated correctly; known is empty (no Tier 1 entries)."""
    from app.converters.comment_code_mapper import build_comment_code_mapping
    result = build_comment_code_mapping({
        "SI": "STRUCTURAL INTERFERENCE",  # suggested (description match)
        "XX": "MYSTERY FLAG",             # unknown (no match)
    })
    assert result.known == {}
    assert "SI" in result.suggested
    assert "XX" in result.unknown
    assert result.final == {}


def test_unknown_when_no_description_match():
    """ATS codes with non-matching descriptions go to unknown."""
    from app.converters.comment_code_mapper import build_comment_code_mapping
    result = build_comment_code_mapping({"ZZ": "COMPLETELY UNKNOWN THING"})
    assert result.known == {}
    assert result.suggested == {}
    assert "ZZ" in result.unknown


def test_smart_flag_matching_stud_description():
    """ST with STUD INTERFERENCE falls to unknown.

    Best fuzzy ratio is 0.80 (vs STRUCTURAL INTERFERENCE) - not strictly above
    the 0.8 threshold, so it requires human review since ST is ambiguous."""
    from app.converters.comment_code_mapper import build_comment_code_mapping
    result = build_comment_code_mapping({"ST": "STUD INTERFERENCE"})
    assert "ST" not in result.known
    assert "ST" not in result.suggested
    assert "ST" in result.unknown


def test_session_memory_pre_fills_suggested():
    """A previously confirmed mapping re-appears in suggested on next call."""
    from app.converters.comment_code_mapper import (
        build_comment_code_mapping,
        clear_session_mappings,
        confirm_mapping,
    )
    clear_session_mappings()
    confirm_mapping("XX", "MYSTERY FLAG", "+")
    result = build_comment_code_mapping({"XX": "MYSTERY FLAG"})
    assert "XX" in result.suggested
    assert result.suggested["XX"] == "+"
    assert "XX" not in result.known
    assert "XX" not in result.unknown
    clear_session_mappings()


def test_session_memory_is_description_scoped():
    """Same code with a different description does NOT use session memory."""
    from app.converters.comment_code_mapper import (
        build_comment_code_mapping,
        clear_session_mappings,
        confirm_mapping,
    )
    clear_session_mappings()
    confirm_mapping("XX", "MYSTERY FLAG", "+")
    # Different description for the same code - should not hit session cache
    result = build_comment_code_mapping({"XX": "DIFFERENT DESCRIPTION"})
    assert "XX" not in result.suggested
    assert "XX" in result.unknown
    clear_session_mappings()


def test_check_known_symbols_all_known():
    from app.converters.comment_code_mapper import check_known_symbols
    result = check_known_symbols({"*", "<", ";", "[", "&"})
    assert result.unknown == {}
    assert result.known == {"*": "*", "<": "<", ";": ";", "[": "[", "&": "&"}
    assert result.suggested == {}
    assert result.final == result.known


def test_check_known_symbols_unknown_symbol():
    from app.converters.comment_code_mapper import check_known_symbols
    result = check_known_symbols({"*", "Q"})
    assert "Q" in result.unknown
    assert result.unknown["Q"] == ""
    assert "*" in result.known
    assert result.suggested == {}   # no smart-match suggestion attached


def test_confirm_session_mappings_helper():
    """confirm_session_mappings() records all pairs from confirmed + ats_comment_codes dicts."""
    from app.converters.comment_code_mapper import (
        build_comment_code_mapping,
        clear_session_mappings,
        confirm_session_mappings,
    )
    clear_session_mappings()
    confirmed = {"AA": "(", "BB": ")"}
    ats_comment_codes = {"AA": "SOME FLAG A", "BB": "SOME FLAG B", "CC": "SOME FLAG C"}
    confirm_session_mappings(confirmed, ats_comment_codes)
    result = build_comment_code_mapping({"AA": "SOME FLAG A", "BB": "SOME FLAG B", "CC": "SOME FLAG C"})
    assert result.suggested.get("AA") == "("
    assert result.suggested.get("BB") == ")"
    assert "CC" in result.unknown
    clear_session_mappings()
