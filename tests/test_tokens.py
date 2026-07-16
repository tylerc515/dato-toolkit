"""Tests for the design token source of truth."""
from __future__ import annotations


def test_color_tokens_have_expected_values():
    from app.design.tokens import Color
    assert Color.PAGE_BG == "#0c0c0e"
    assert Color.SIDEBAR_BG == "#131316"
    assert Color.CARD_BG == "#151517"
    assert Color.TABLE_HEADER_BG == "#1a1a1d"
    assert Color.INPUT_BG == "#0f0f11"
    assert Color.BORDER == "#232326"
    assert Color.BORDER_STRONG == "#2f2f34"
    assert Color.TEXT_PRIMARY == "#f4f4f5"
    assert Color.TEXT_SECONDARY == "#d4d4d8"
    assert Color.TEXT_MUTED == "#8b8b90"
    assert Color.TEXT_FAINT == "#6b6b70"
    assert Color.ACCENT == "#2563eb"
    assert Color.ACCENT_HOVER == "#1d4ed8"
    assert Color.ACCENT_TEXT == "#7fb0ff"
    assert Color.ACCENT_BG_TINT == "#1a2c50"
    assert Color.SUCCESS == "#00B050"
    assert Color.WARNING == "#f4b13b"
    assert Color.DANGER == "#ef4444"


def test_spacing_tokens_have_expected_values():
    from app.design.tokens import Spacing
    assert (Spacing.XS, Spacing.SM, Spacing.MD, Spacing.LG, Spacing.XL, Spacing.XXL, Spacing.XXXL) == (
        4, 8, 12, 18, 22, 28, 36,
    )


def test_radius_tokens_have_expected_values():
    from app.design.tokens import Radius
    assert (Radius.INPUT, Radius.BUTTON, Radius.CARD, Radius.SIDEBAR_ITEM, Radius.PILL) == (
        7, 8, 10, 8, 999,
    )


def test_font_size_tokens_have_expected_values():
    from app.design.tokens import FontSize
    assert (FontSize.LABEL, FontSize.SMALL, FontSize.BODY, FontSize.SECTION, FontSize.PAGE_TITLE, FontSize.STAT_NUMBER) == (
        15, 15, 16, 16, 22, 28,
    )


def test_font_family_token():
    from app.design.tokens import FONT_FAMILY
    assert FONT_FAMILY == "Segoe UI"
