"""Tests for the token-driven stylesheet and the transitional color() shim."""
from __future__ import annotations

import re


def test_legacy_color_keys_still_resolve():
    from app.styles import color
    from app.design.tokens import Color as T
    assert color("surface") == T.CARD_BG
    assert color("border") == T.BORDER
    assert color("highlight") == T.ACCENT
    assert color("accent") == T.CARD_BG
    assert color("text") == T.TEXT_PRIMARY
    assert color("muted_text") == T.TEXT_MUTED
    assert color("success") == T.SUCCESS
    assert color("warning") == T.WARNING
    assert color("error") == T.DANGER
    assert color("background") == T.PAGE_BG
    assert color("chrome_hover") == T.BORDER_STRONG


def test_build_stylesheet_contains_no_old_palette_hex():
    from app.styles import build_stylesheet
    qss = build_stylesheet("dark")
    for old_hex in ("#1a1a2e", "#16213e", "#e94560", "#0f3460"):
        assert old_hex not in qss, f"Old palette color {old_hex} leaked into new stylesheet"


def test_build_stylesheet_contains_no_stray_hex_outside_tokens():
    """Every hex literal in the generated QSS must trace back to a Color token value."""
    from app.styles import build_stylesheet
    from app.design.tokens import Color as T
    qss = build_stylesheet("dark")
    token_hexes = {v for k, v in vars(T).items() if not k.startswith("_")}
    found_hexes = set(re.findall(r"#[0-9a-fA-F]{6}", qss))
    stray = found_hexes - token_hexes
    assert not stray, f"QSS contains hex values not defined in Color tokens: {stray}"


def test_build_stylesheet_same_regardless_of_theme_arg():
    """This pass ships one theme; build_stylesheet ignores the theme argument's palette."""
    from app.styles import build_stylesheet
    assert build_stylesheet("dark") == build_stylesheet("light")


def test_set_and_get_active_theme_still_work():
    from app.styles import set_active_theme, get_active_theme, DEFAULT_THEME
    set_active_theme("light")
    assert get_active_theme() == "light"
    set_active_theme(DEFAULT_THEME)


def test_build_stylesheet_contains_no_stray_pixel_literals():
    """Every `<number>px` value in the generated QSS must trace back to a
    Spacing/Radius/FontSize token value, with one narrow exception: a bare
    `1px` border width. `1px solid ...` is a CSS/QSS border-width convention
    (the universal "hairline" border), not a design-system spacing or radius
    value - there is no Spacing/Radius token for it and it isn't meant to
    scale with the rest of the design system, so it's excluded from this
    check rather than forced onto an unrelated token.
    """
    from app.styles import build_stylesheet
    from app.design.tokens import FontSize, Radius, Spacing

    qss = build_stylesheet("dark")

    token_values = set()
    for token_class in (Spacing, Radius, FontSize):
        for key, value in vars(token_class).items():
            if not key.startswith("_") and isinstance(value, int):
                token_values.add(value)

    found_pixels = {int(n) for n in re.findall(r"(\d+)px", qss)}
    stray = {n for n in found_pixels if n != 1 and n not in token_values}
    assert not stray, (
        f"QSS contains pixel literals not sourced from app.design.tokens: {stray}"
    )
