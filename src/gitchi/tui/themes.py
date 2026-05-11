"""4-color retro CRT themes for the TUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """A 6-token palette. Bars and frames use the first four; ok/alert tint state."""

    name: str
    bg: str       # darkest — backgrounds, empty bar cells
    fg: str       # lightest — text, full bar cells
    dim: str      # mid — borders, low-fill cells
    accent: str   # highlight — selected row, sort arrow
    alert: str    # alert state — hungry/dying bars + status word
    ok: str       # thriving state — sparkles, healthy bars


THEMES: dict[str, Theme] = {
    "gameboy-green": Theme(
        name="gameboy-green",
        bg="#0f380f",
        fg="#8bac0f",
        dim="#306230",
        accent="#9bbc0f",
        alert="#9bbc0f",
        ok="#8bac0f",
    ),
    "gameboy-pocket": Theme(
        name="gameboy-pocket",
        bg="#0f0f0f",
        fg="#c0c0c0",
        dim="#606060",
        accent="#ffffff",
        alert="#ff8080",
        ok="#80ff80",
    ),
    "virtual-boy": Theme(
        name="virtual-boy",
        bg="#1a0000",
        fg="#ff2a2a",
        dim="#660000",
        accent="#ff6666",
        alert="#ff9999",
        ok="#ff4444",
    ),
    "cozy": Theme(
        name="cozy",
        bg="#2a1f1a",
        fg="#d4b896",
        dim="#6b4f3a",
        accent="#e7a3a3",
        alert="#e7a3a3",
        ok="#7fb8a8",
    ),
}


def list_theme_names() -> list[str]:
    return list(THEMES.keys())


def get_theme(name: str) -> Theme:
    if name not in THEMES:
        raise KeyError(name)
    return THEMES[name]


_CSS_TEMPLATE = """\
Screen {{
    background: {bg};
    color: {fg};
}}
#body {{ height: 1fr; }}
DataTable {{
    width: 50%;
    background: {bg};
    color: {fg};
}}
DataTable > .datatable--header {{
    background: {dim};
    color: {accent};
}}
DataTable > .datatable--cursor {{
    background: {accent};
    color: {bg};
}}
DetailPanel {{
    width: 50%;
    padding: 1 2;
    border: round {dim};
    background: {bg};
    color: {fg};
}}
NewsPanel {{
    height: auto;
    max-height: 10;
    padding: 0 2;
    border-top: solid {dim};
    color: {fg};
    background: {bg};
}}
NewsPanel.collapsed {{
    display: none;
}}
SearchInput {{
    dock: top;
    height: 3;
    border: round {accent};
    background: {bg};
    color: {fg};
}}
SearchInput.hidden {{
    display: none;
}}
.alert {{
    color: {alert};
    text-style: bold;
}}
.ok {{
    color: {ok};
}}
.dim {{
    color: {dim};
}}
.ghost-row {{
    color: {dim};
    text-style: italic;
}}
"""


def render_css(theme: Theme) -> str:
    """Render Textual CSS for the given theme."""
    return _CSS_TEMPLATE.format(
        bg=theme.bg,
        fg=theme.fg,
        dim=theme.dim,
        accent=theme.accent,
        alert=theme.alert,
        ok=theme.ok,
    )
