"""Tests for tui/themes.py."""

from __future__ import annotations

import pytest

from gitchi.tui.themes import THEMES, get_theme, list_theme_names, render_css


def test_four_builtin_themes() -> None:
    names = list_theme_names()
    assert set(names) == {"gameboy-green", "gameboy-pocket", "virtual-boy", "cozy"}


def test_default_lookup_returns_gameboy_green() -> None:
    t = get_theme("gameboy-green")
    assert t.name == "gameboy-green"


def test_unknown_theme_raises() -> None:
    with pytest.raises(KeyError):
        get_theme("not-a-theme")


def test_render_css_contains_palette_tokens() -> None:
    t = get_theme("gameboy-green")
    css = render_css(t)
    # Every palette color should appear at least once in the rendered CSS.
    for color in (t.bg, t.fg, t.dim, t.accent, t.alert, t.ok):
        assert color in css


def test_render_css_has_no_unresolved_placeholders() -> None:
    for t in THEMES.values():
        css = render_css(t)
        # A "{" that survives means a placeholder didn't get substituted.
        # Account for Textual's CSS curly braces by stripping them via the
        # template's literal {{ }} doubling (which becomes single { } after
        # .format). If any single brace remains it's a placeholder.
        # Easiest robust check: ensure no Python-format-style {token} survives.
        import re
        leftover = re.findall(r"\{[a-zA-Z_]+\}", css)
        assert leftover == [], f"leftover placeholders in {t.name}: {leftover}"


def test_themes_have_valid_hex_colors() -> None:
    import re

    hex_re = re.compile(r"^#[0-9a-fA-F]{6}$")
    for t in THEMES.values():
        for color in (t.bg, t.fg, t.dim, t.accent, t.alert, t.ok):
            assert hex_re.match(color), f"{t.name}: bad color {color!r}"
