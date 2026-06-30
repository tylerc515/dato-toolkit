"""Tests for ATS flag code mapping logic."""
from __future__ import annotations


def test_default_map_has_six_entries():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert len(DEFAULT_ATS_FLAG_MAP) == 6


def test_default_map_contains_known_codes():
    from app.converters.flag_mapper import DEFAULT_ATS_FLAG_MAP
    assert DEFAULT_ATS_FLAG_MAP["NC"] == "<"
    assert DEFAULT_ATS_FLAG_MAP["RF"] == "("
    assert DEFAULT_ATS_FLAG_MAP["RT"] == ")"
    assert DEFAULT_ATS_FLAG_MAP["SI"] == ";"
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
