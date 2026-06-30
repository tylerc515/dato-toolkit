"""Tests for ATS flag code mapping logic."""
from __future__ import annotations


def test_default_map_is_empty():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert DEFAULT_ATS_FLAG_MAP == {}


def test_default_map_contains_no_codes():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert len(DEFAULT_ATS_FLAG_MAP) == 0
    for code in ("NC", "RF", "RT", "NS", "ST"):
        assert code not in DEFAULT_ATS_FLAG_MAP


def test_standard_symbol_descriptions_has_scaffold():
    from app.converters.flag_mapper import STANDARD_SYMBOL_DESCRIPTIONS
    assert STANDARD_SYMBOL_DESCRIPTIONS[";"] == "SCAFFOLD INTERFERENCE"


def test_build_mapping_scaffold_interference_suggested():
    """Codes whose description matches SCAFFOLD INTERFERENCE go to Tier 2 (suggested)."""
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({"SI": "SCAFFOLD INTERFERENCE"})
    assert result.known == {}
    assert result.suggested == {"SI": ";"}
    assert result.final == {}


def test_build_mapping_with_unknown():
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({"SI": "SCAFFOLD INTERFERENCE", "XX": "SOME NEW FLAG"})
    assert "XX" in result.unknown
    assert "SI" in result.suggested
    assert "XX" not in result.known
    assert result.final == {}


def test_build_mapping_empty():
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({})
    assert result.known == {}
    assert result.unknown == {}
    assert result.final == {}


def test_build_mapping_only_unknown():
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({"ZZ": "MYSTERY"})
    assert result.known == {}
    assert "ZZ" in result.unknown
    assert result.final == {}


def test_flag_maps_are_consistent():
    """Every symbol in DEFAULT_ATS_FLAG_MAP must appear in STANDARD_SYMBOL_DESCRIPTIONS."""
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP, STANDARD_SYMBOL_DESCRIPTIONS
    for ats_code, std_symbol in DEFAULT_ATS_FLAG_MAP.items():
        assert std_symbol in STANDARD_SYMBOL_DESCRIPTIONS, (
            f"DEFAULT_ATS_FLAG_MAP maps {ats_code!r} to {std_symbol!r}, "
            f"but {std_symbol!r} is not in STANDARD_SYMBOL_DESCRIPTIONS"
        )


def test_smart_flag_matching_by_description():
    """ATS codes not in DEFAULT_ATS_FLAG_MAP but matching by description go to suggested."""
    from app.converters.flag_mapper import build_flag_mapping
    # "SI - SCAFFOLD INTERFERENCE" should match ";" via description
    result = build_flag_mapping({"SI": "SCAFFOLD INTERFERENCE"})
    assert "SI" in result.suggested
    assert result.suggested["SI"] == ";"
    assert "SI" not in result.known
    assert "SI" not in result.unknown


def test_three_tier_mixed():
    """Suggested and unknown are populated correctly; known is empty (no Tier 1 entries)."""
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({
        "SI": "SCAFFOLD INTERFERENCE",  # suggested (description match)
        "XX": "MYSTERY FLAG",           # unknown (no match)
    })
    assert result.known == {}
    assert "SI" in result.suggested
    assert "XX" in result.unknown
    assert result.final == {}


def test_unknown_when_no_description_match():
    """ATS codes with non-matching descriptions go to unknown."""
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({"ZZ": "COMPLETELY UNKNOWN THING"})
    assert result.known == {}
    assert result.suggested == {}
    assert "ZZ" in result.unknown


def test_smart_flag_matching_stud_description():
    """ST with STUD INTERFERENCE falls to unknown.
    Best fuzzy ratio is 0.79 (vs SCAFFOLD INTERFERENCE) - just below the 0.8 threshold.
    Both stud and structural interference require human review because ST is ambiguous."""
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({"ST": "STUD INTERFERENCE"})
    assert "ST" not in result.known
    assert "ST" not in result.suggested
    assert "ST" in result.unknown


def test_session_memory_pre_fills_suggested():
    """A previously confirmed mapping re-appears in suggested on next call."""
    from app.converters.flag_mapper import (
        build_flag_mapping,
        clear_session_mappings,
        confirm_mapping,
    )
    clear_session_mappings()
    confirm_mapping("XX", "MYSTERY FLAG", "+")
    result = build_flag_mapping({"XX": "MYSTERY FLAG"})
    assert "XX" in result.suggested
    assert result.suggested["XX"] == "+"
    assert "XX" not in result.known
    assert "XX" not in result.unknown
    clear_session_mappings()


def test_session_memory_is_description_scoped():
    """Same code with a different description does NOT use session memory."""
    from app.converters.flag_mapper import (
        build_flag_mapping,
        clear_session_mappings,
        confirm_mapping,
    )
    clear_session_mappings()
    confirm_mapping("XX", "MYSTERY FLAG", "+")
    # Different description for the same code - should not hit session cache
    result = build_flag_mapping({"XX": "DIFFERENT DESCRIPTION"})
    assert "XX" not in result.suggested
    assert "XX" in result.unknown
    clear_session_mappings()


def test_confirm_session_mappings_helper():
    """confirm_session_mappings() records all pairs from confirmed + ats_flags dicts."""
    from app.converters.flag_mapper import (
        build_flag_mapping,
        clear_session_mappings,
        confirm_session_mappings,
    )
    clear_session_mappings()
    confirmed = {"AA": "(", "BB": ")"}
    ats_flags = {"AA": "SOME FLAG A", "BB": "SOME FLAG B", "CC": "SOME FLAG C"}
    confirm_session_mappings(confirmed, ats_flags)
    result = build_flag_mapping({"AA": "SOME FLAG A", "BB": "SOME FLAG B", "CC": "SOME FLAG C"})
    assert result.suggested.get("AA") == "("
    assert result.suggested.get("BB") == ")"
    assert "CC" in result.unknown
    clear_session_mappings()
