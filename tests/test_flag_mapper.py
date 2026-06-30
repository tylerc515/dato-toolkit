"""Tests for ATS flag code mapping logic."""
from __future__ import annotations


def test_default_map_has_five_entries():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert len(DEFAULT_ATS_FLAG_MAP) == 5


def test_default_map_contains_known_codes():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert DEFAULT_ATS_FLAG_MAP["NC"] == "<"
    assert DEFAULT_ATS_FLAG_MAP["RF"] == "("
    assert DEFAULT_ATS_FLAG_MAP["RT"] == ")"
    assert DEFAULT_ATS_FLAG_MAP["ST"] == "+"
    assert DEFAULT_ATS_FLAG_MAP["NS"] == "["


def test_build_mapping_all_known():
    from app.converters.flag_mapper import build_flag_mapping
    ats_flags = {"NC": "NOT CLEAN", "RF": "REFRACTORY"}
    result = build_flag_mapping(ats_flags)
    assert result.unknown == {}
    assert result.known == {"NC": "<", "RF": "("}
    assert result.final == {"NC": "<", "RF": "("}


def test_build_mapping_with_unknown():
    from app.converters.flag_mapper import build_flag_mapping
    ats_flags = {"NC": "NOT CLEAN", "XX": "SOME NEW FLAG"}
    result = build_flag_mapping(ats_flags)
    assert "XX" in result.unknown
    assert "NC" in result.known
    assert "XX" not in result.known
    assert result.final == {"NC": "<"}


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
    """Known, suggested, and unknown are all populated correctly."""
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({
        "NC": "NOT CLEAN",          # known (exact code match)
        "SI": "SCAFFOLD INTERFERENCE",  # suggested (description match)
        "XX": "MYSTERY FLAG",       # unknown (no match)
    })
    assert "NC" in result.known
    assert "SI" in result.suggested
    assert "XX" in result.unknown
    assert result.final == {"NC": "<"}  # only known in final until confirmed


def test_unknown_when_no_description_match():
    """ATS codes with non-matching descriptions go to unknown."""
    from app.converters.flag_mapper import build_flag_mapping
    result = build_flag_mapping({"ZZ": "COMPLETELY UNKNOWN THING"})
    assert result.known == {}
    assert result.suggested == {}
    assert "ZZ" in result.unknown
