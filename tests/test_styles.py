"""Tests for the token-driven stylesheet."""
from __future__ import annotations

import re
from pathlib import Path


def test_no_color_shim_calls_remain():
    app_dir = Path(__file__).resolve().parent.parent / "app"
    offenders = []
    for py in app_dir.rglob("*.py"):
        if re.search(r"\bcolor\(['\"]", py.read_text(encoding="utf-8")):
            offenders.append(str(py.relative_to(app_dir)))
    assert offenders == [], f"color() shim still called in: {offenders}"


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


def test_build_stylesheet_has_success_variant_button():
    from app.styles import build_stylesheet
    qss = build_stylesheet("dark")
    assert 'QPushButton[variant="success"]' in qss


def test_set_and_get_active_theme_still_work():
    from app.styles import set_active_theme, get_active_theme, DEFAULT_THEME
    set_active_theme("light")
    assert get_active_theme() == "light"
    set_active_theme(DEFAULT_THEME)


def test_build_stylesheet_contains_no_stray_pixel_literals():
    """Every `<number>px` value written in `build_stylesheet`'s SOURCE CODE
    must come from a token interpolation like `{Spacing.SM}px`, with one
    narrow exception: a bare `1px` border width. `1px solid ...` is a
    CSS/QSS border-width convention (the universal "hairline" border), not
    a design-system spacing or radius value - there is no Spacing/Radius
    token for it and it isn't meant to scale with the rest of the design
    system, so it's excluded from this check rather than forced onto an
    unrelated token.

    This inspects the SOURCE TEXT of the function, not the rendered QSS
    output. Checking the rendered output is not sufficient: the token
    value space (Spacing/Radius/FontSize, roughly 4-32) is small and dense
    enough that a hardcoded literal can coincidentally equal some token's
    numeric value without ever having been interpolated from it, letting a
    regression silently pass. A real token interpolation always renders in
    source as `...}px` (the closing brace sits directly before `px`); a
    hardcoded literal has a digit directly before `px` with no brace in
    between. Matching `\\d+px` that is NOT immediately preceded by `}`
    catches exactly the hardcoded case.
    """
    import inspect

    from app.styles import build_stylesheet

    source = inspect.getsource(build_stylesheet)

    found_pixels = re.findall(r"(?<!\})\d+px", source)
    stray = {literal for literal in found_pixels if literal != "1px"}
    assert not stray, (
        f"build_stylesheet source contains pixel literals not sourced via "
        f"token interpolation (e.g. {{Spacing.SM}}px): {stray}"
    )


def test_build_stylesheet_has_disabled_state_rules():
    from app.styles import build_stylesheet
    qss = build_stylesheet("dark")
    assert "QComboBox:disabled" in qss
    assert "QCheckBox::indicator:disabled" in qss


def test_pyproject_version_matches_app_version():
    from pathlib import Path
    from app import __version__
    text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in text
