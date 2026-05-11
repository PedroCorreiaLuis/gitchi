# TUI improvements — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the gitchi TUI improvements described in `docs/superpowers/specs/2026-05-10-tui-improvements-design.md`: refined two-pane layout, retro 4-color theming, sparklines, badges, status reasons, animated pet art, search/sort/toggles.

**Architecture:** `src/gitchi/tui.py` (249 lines) becomes a package `src/gitchi/tui/` with `app.py`, `state.py`, `themes.py`, `animation.py`, `status_reason.py`, and a `widgets/` subpackage. Pure helpers (state, themes, status_reason) get unit tests; widget classes stay thin. New `tui.theme` / `tui.animation` config keys persist via existing `config.py`. New CLI verb `gitchi theme`. Play results persist in a new `last_play_results` SQL table (migration `004`). Sparklines reuse the existing `history.sparkline()` function (no new module). Animation is a single 0.5s interval on the DetailPanel; only the visible pet animates.

**Tech Stack:** Python 3.12, Textual ≥ 0.85, SQLite (existing store), pytest, ruff, mypy strict, uv.

**Branch:** Work on `feature/tui-improvements` (already created from main at commit `f1aad23` which contains the spec).

---

## Conventions

**Every task ends with:**
- [ ] Run full check: `cd ~/gitchi && uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy --strict src`
- [ ] Commit with the message specified in the task

**Commit style** (from `git log`): `feat(tui): X`, `feat: X`, `refactor(tui): X`, `chore: X`, `docs: X`. Include trailer:

```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

**Test placement:** Tests for `src/gitchi/foo.py` live in `tests/test_foo.py`. For `src/gitchi/tui/foo.py` tests live in `tests/tui/test_foo.py`. Mirror the source tree.

---

## Task 1: Convert tui.py to a package

**Goal:** Move `src/gitchi/tui.py` into `src/gitchi/tui/__init__.py` with no behavior change. Re-export `run` so `from gitchi.tui import run` continues to work for `cli.py`.

**Files:**
- Move: `src/gitchi/tui.py` → `src/gitchi/tui/__init__.py`

- [ ] **Step 1: Move the file**

```bash
cd ~/gitchi
mkdir -p src/gitchi/tui
git mv src/gitchi/tui.py src/gitchi/tui/__init__.py
```

- [ ] **Step 2: Run existing tests**

```bash
uv run pytest -q
```

Expected: All 86 tests pass. (No test imports `gitchi.tui` directly; the import `from .tui import run` in `cli.py` resolves to the package's `__init__.py`.)

- [ ] **Step 3: Run smoke test for the import path**

```bash
uv run python -c "from gitchi.tui import run; print(run)"
```

Expected: Prints `<function run at 0x...>`.

- [ ] **Step 4: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
git commit -am "refactor(tui): convert tui.py to package"
```

---

## Task 2: Extract NewsPanel and DetailPanel (no behavior change yet)

**Goal:** Split widgets out of `__init__.py` so the next tasks have clean targets to modify. Pure mechanical move, no logic changes.

**Files:**
- Create: `src/gitchi/tui/widgets/__init__.py` (empty)
- Create: `src/gitchi/tui/widgets/news_panel.py` (current `NewsPanel` class + `NEWS_PANEL_LIMIT`)
- Create: `src/gitchi/tui/widgets/detail_panel.py` (current `DetailPanel` class + `_bar` helper)
- Modify: `src/gitchi/tui/__init__.py` to import from the new locations

- [ ] **Step 1: Create `widgets/__init__.py`**

```python
"""TUI widget package."""
```

- [ ] **Step 2: Create `widgets/news_panel.py`**

Content: lift the existing `NewsPanel` class and `NEWS_PANEL_LIMIT` from `tui/__init__.py` verbatim, with the imports it needs (`Static`, `NewsEvent`).

```python
"""News panel widget — most recent state transitions."""

from __future__ import annotations

from textual.widgets import Static

from ...models import NewsEvent

NEWS_PANEL_LIMIT = 6


class NewsPanel(Static):
    """Footer-area panel showing the latest state-change events."""

    def show_events(self, events: list[NewsEvent]) -> None:
        if not events:
            self.update("[dim]news: (rescan to start tracking)[/dim]")
            return
        lines = ["[bold]news[/bold]"]
        for event in events[:NEWS_PANEL_LIMIT]:
            lines.append(f"  {event.headline}")
        self.update("\n".join(lines))
```

- [ ] **Step 3: Create `widgets/detail_panel.py`**

Lift the `DetailPanel` class + `_bar` helper:

```python
"""Detail panel widget — selected pet's art and vitals."""

from __future__ import annotations

from textual.widgets import Static

from ...art import render
from ...models import Pet
from ...rarity import emoji_for as rarity_emoji_for
from ...species import emoji_for


def _bar(value: int, width: int = 12) -> str:
    filled = max(0, min(width, round(value / 100 * width)))
    return f"{'█' * filled}{'░' * (width - filled)}"


class DetailPanel(Static):
    """Right-hand pane that shows the selected pet's art + vitals."""

    def show_pet(self, pet: Pet | None) -> None:
        if pet is None:
            self.update("[dim]no pets — run `gitchi refresh` to scan.[/dim]")
            return
        rarity_tag = f"{rarity_emoji_for(pet.rarity)} {pet.rarity.value}"
        lines = [
            f"[bold]{pet.repo.name}[/bold]  {emoji_for(pet.species)} {pet.species.value} · "
            f"{pet.stage.value} · {rarity_tag}",
            f"[dim]{pet.repo.path}[/dim]",
            "",
            render(pet.species, pet.stage),
            "",
            f"hunger {_bar(pet.vitals.hunger)} {pet.vitals.hunger:3d}",
            f"health {_bar(pet.vitals.health)} {pet.vitals.health:3d}",
            f"energy {_bar(pet.vitals.energy)} {pet.vitals.energy:3d}",
            f"mood   {_bar(pet.vitals.mood)} {pet.vitals.mood:3d}",
            "",
            f"age    {pet.vitals.age_days} days",
            f"rarity {rarity_tag}",
            f"state  {pet.status_word}",
        ]
        if pet.ignored:
            lines.append("[dim italic]ignored[/dim italic]")
        elif pet.buried:
            lines.append(
                "[dim italic]buried · " + (pet.bury_reason or "at peace") + "[/dim italic]"
            )
        self.update("\n".join(lines))
```

- [ ] **Step 4: Update `tui/__init__.py`**

Remove the `DetailPanel`, `NewsPanel`, `NEWS_PANEL_LIMIT`, and `_bar` definitions; import them from the new locations:

```python
from .widgets.detail_panel import DetailPanel
from .widgets.news_panel import NEWS_PANEL_LIMIT, NewsPanel
```

(Keep everything else identical for now.)

- [ ] **Step 5: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
git add src/gitchi/tui
git commit -m "refactor(tui): extract NewsPanel and DetailPanel widgets"
```

Expected: pytest still 86 passing, no behavior change.

---

## Task 3: Add `AppState` dataclass with sort/filter helpers

**Goal:** Centralize per-session UI state in a tested pure module. Used by widgets in later tasks.

**Files:**
- Create: `src/gitchi/tui/state.py`
- Create: `tests/tui/__init__.py` (empty)
- Create: `tests/tui/test_state.py`

- [ ] **Step 1: Write tests first** (`tests/tui/test_state.py`)

```python
"""Tests for tui/state.py."""

from __future__ import annotations

from dataclasses import replace

from gitchi.tui.state import AppState, SortKey, apply_filter, apply_sort, cycle_sort


def _pet(name: str, hunger: int = 50, health: int = 50, mood: int = 50, age: int = 1) -> object:
    """Minimal stand-in: anything with .repo.name, .vitals.{hunger,health,mood,age_days}, .rarity."""
    from gitchi.models import Pet, Rarity, Repo, Species, Stage, Vitals
    from pathlib import Path

    return Pet(
        repo=Repo(
            path=Path(f"/tmp/{name}"),
            name=name,
            primary_language=None,
            first_commit=None,
            last_commit=None,
            commit_count=0,
            size_bytes=0,
            has_tests=False,
            has_ci=False,
        ),
        species=Species.GENERIC_BLOB,
        stage=Stage.BABY,
        vitals=Vitals(hunger=hunger, health=health, energy=50, mood=mood, age_days=age),
        rarity=Rarity.COMMON,
    )


def test_default_state() -> None:
    s = AppState()
    assert s.sort_key == "name"
    assert s.sort_desc is False
    assert s.filter_text == ""
    assert s.show_ghosts is True
    assert s.show_buried is True
    assert s.animation_enabled is True
    assert s.news_collapsed is False


def test_cycle_sort_advances_through_keys() -> None:
    seq: list[SortKey] = []
    key: SortKey = "name"
    for _ in range(7):
        key = cycle_sort(key)
        seq.append(key)
    assert seq == ["hunger", "health", "mood", "age", "rarity", "name", "hunger"]


def test_apply_sort_name_ascending() -> None:
    pets = [_pet("b"), _pet("a"), _pet("c")]
    out = apply_sort(pets, "name", desc=False)
    assert [p.repo.name for p in out] == ["a", "b", "c"]


def test_apply_sort_hunger_descending() -> None:
    pets = [_pet("a", hunger=10), _pet("b", hunger=90), _pet("c", hunger=50)]
    out = apply_sort(pets, "hunger", desc=True)
    assert [p.repo.name for p in out] == ["b", "c", "a"]


def test_apply_sort_age_descending() -> None:
    pets = [_pet("a", age=1), _pet("b", age=10), _pet("c", age=5)]
    out = apply_sort(pets, "age", desc=True)
    assert [p.repo.name for p in out] == ["b", "c", "a"]


def test_apply_filter_substring_case_insensitive() -> None:
    pets = [_pet("Rasteira"), _pet("gitchi"), _pet("coldpipe")]
    out = apply_filter(pets, "TCH")
    assert [p.repo.name for p in out] == ["gitchi"]


def test_apply_filter_empty_returns_all() -> None:
    pets = [_pet("a"), _pet("b")]
    out = apply_filter(pets, "")
    assert len(out) == 2


def test_replace_preserves_other_fields() -> None:
    s = AppState(sort_key="mood", show_ghosts=False)
    s2 = replace(s, filter_text="ras")
    assert s2.sort_key == "mood"
    assert s2.show_ghosts is False
    assert s2.filter_text == "ras"
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
uv run pytest tests/tui/test_state.py -q
```

- [ ] **Step 3: Implement `src/gitchi/tui/state.py`**

```python
"""Per-session UI state for the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..models import Pet, Rarity

SortKey = Literal["name", "hunger", "health", "mood", "age", "rarity"]

_SORT_ORDER: tuple[SortKey, ...] = ("name", "hunger", "health", "mood", "age", "rarity")


@dataclass
class AppState:
    """In-memory per-session UI state.

    Theme and `animation_enabled` persist via `config.toml`. Everything here
    that isn't a mirror of config (sort, filter, show toggles, news_collapsed)
    is per-session and resets to defaults on restart.
    """

    sort_key: SortKey = "name"
    sort_desc: bool = False
    filter_text: str = ""
    show_ghosts: bool = True
    show_buried: bool = True
    animation_enabled: bool = True  # mirror of tui.animation in config
    news_collapsed: bool = False


def cycle_sort(current: SortKey) -> SortKey:
    """Return the next sort key in the cycle."""
    idx = _SORT_ORDER.index(current)
    return _SORT_ORDER[(idx + 1) % len(_SORT_ORDER)]


_RARITY_RANK: dict[Rarity, int] = {
    Rarity.COMMON: 0,
    Rarity.UNCOMMON: 1,
    Rarity.RARE: 2,
    Rarity.EPIC: 3,
    Rarity.MYTHIC: 4,
    Rarity.LEGENDARY: 5,
}


def apply_sort(pets: list[Pet], key: SortKey, *, desc: bool) -> list[Pet]:
    """Return a new list of pets sorted by `key` direction `desc`."""

    def keyfn(p: Pet) -> object:
        if key == "name":
            return p.repo.name.lower()
        if key == "hunger":
            return p.vitals.hunger
        if key == "health":
            return p.vitals.health
        if key == "mood":
            return p.vitals.mood
        if key == "age":
            return p.vitals.age_days
        if key == "rarity":
            return _RARITY_RANK[p.rarity]
        raise ValueError(f"unknown sort key: {key}")

    return sorted(pets, key=keyfn, reverse=desc)


def apply_filter(pets: list[Pet], text: str) -> list[Pet]:
    """Case-insensitive substring filter on repo name."""
    if not text:
        return list(pets)
    needle = text.casefold()
    return [p for p in pets if needle in p.repo.name.casefold()]
```

- [ ] **Step 4: Tests pass**

```bash
uv run pytest tests/tui/test_state.py -q
```

Expected: all pass.

- [ ] **Step 5: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
git add src/gitchi/tui/state.py tests/tui/
git commit -m "feat(tui): add AppState with sort/filter helpers"
```

---

## Task 4: Add `TuiConfig` to `Config`

**Goal:** New config section `[tui]` with `theme` and `animation` keys. Both default to gameboy-green and true. Persist via existing `config.toml`.

**Files:**
- Modify: `src/gitchi/models.py` (add `TuiConfig` dataclass; add field to `Config`)
- Modify: `src/gitchi/config.py` (`_from_dict`, `_to_dict`, `set_value`)
- Modify: `tests/test_config.py` (add roundtrip + set_value cases)

- [ ] **Step 1: Write tests first**

Append to `tests/test_config.py`:

```python
def test_tui_config_roundtrip(tmp_path, monkeypatch) -> None:
    from gitchi.config import _from_dict, _to_dict
    from gitchi.models import Config, TuiConfig

    cfg = Config(tui=TuiConfig(theme="virtual-boy", animation=False))
    roundtrip = _from_dict(_to_dict(cfg))
    assert roundtrip.tui.theme == "virtual-boy"
    assert roundtrip.tui.animation is False


def test_tui_config_defaults_when_missing() -> None:
    from gitchi.config import _from_dict

    cfg = _from_dict({})
    assert cfg.tui.theme == "gameboy-green"
    assert cfg.tui.animation is True


def test_tui_set_value_theme() -> None:
    from gitchi.config import set_value
    from gitchi.models import Config

    cfg = set_value(Config(), "tui.theme", "cozy")
    assert cfg.tui.theme == "cozy"


def test_tui_set_value_animation_truthy() -> None:
    from gitchi.config import set_value
    from gitchi.models import Config

    assert set_value(Config(), "tui.animation", "false").tui.animation is False
    assert set_value(Config(), "tui.animation", "true").tui.animation is True
```

- [ ] **Step 2: Run tests — expect failures (no `tui` attr on Config)**

```bash
uv run pytest tests/test_config.py -q
```

- [ ] **Step 3: Add `TuiConfig` to `models.py`**

Insert before the `Config` class:

```python
@dataclass(slots=True)
class TuiConfig:
    theme: str = "gameboy-green"
    animation: bool = True
```

Modify `Config` to add the field:

```python
@dataclass(slots=True)
class Config:
    scan: ScanConfig = field(default_factory=ScanConfig)
    stats: StatsConfig = field(default_factory=StatsConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    tui: TuiConfig = field(default_factory=TuiConfig)
```

- [ ] **Step 4: Update `config.py`**

Add `TuiConfig` to the imports:

```python
from .models import ClaudeConfig, Config, GitHubConfig, ScanConfig, StatsConfig, TuiConfig
```

In `_from_dict`, after the `github_raw` line:

```python
    tui_raw = raw.get("tui", {}) or {}
```

In the `Config(...)` constructor call, add the `tui=` kwarg:

```python
        tui=TuiConfig(
            theme=str(tui_raw.get("theme", TuiConfig().theme)),
            animation=bool(tui_raw.get("animation", TuiConfig().animation)),
        ),
```

In `_to_dict`, add the `tui` section:

```python
        "tui": {
            "theme": cfg.tui.theme,
            "animation": cfg.tui.animation,
        },
```

In `set_value`, add a new section branch before the final `else`:

```python
    elif section == "tui":
        if key == "theme":
            cfg.tui.theme = value
        elif key == "animation":
            cfg.tui.animation = value.lower() in {"1", "true", "yes", "on"}
        else:
            raise KeyError(key)
```

- [ ] **Step 5: Tests pass**

```bash
uv run pytest tests/test_config.py -q
```

- [ ] **Step 6: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
git add src/gitchi/models.py src/gitchi/config.py tests/test_config.py
git commit -m "feat(config): add [tui] section for theme and animation"
```

---

## Task 5: Add `themes` module with registry + CSS generator

**Goal:** Define 4 retro CRT themes as data, render Textual CSS from each, and validate by lookup.

**Files:**
- Create: `src/gitchi/tui/themes.py`
- Create: `tests/tui/test_themes.py`

- [ ] **Step 1: Write tests first**

```python
"""Tests for tui/themes.py."""

from __future__ import annotations

import pytest

from gitchi.tui.themes import THEMES, Theme, get_theme, list_theme_names, render_css


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
        assert "{" not in css.replace("{{", "").replace("}}", "")


def test_themes_have_valid_hex_colors() -> None:
    import re

    hex_re = re.compile(r"^#[0-9a-fA-F]{6}$")
    for t in THEMES.values():
        for color in (t.bg, t.fg, t.dim, t.accent, t.alert, t.ok):
            assert hex_re.match(color), f"{t.name}: bad color {color!r}"
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
uv run pytest tests/tui/test_themes.py -q
```

- [ ] **Step 3: Implement `src/gitchi/tui/themes.py`**

```python
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
```

- [ ] **Step 4: Tests pass**

```bash
uv run pytest tests/tui/test_themes.py -q
```

- [ ] **Step 5: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
git add src/gitchi/tui/themes.py tests/tui/test_themes.py
git commit -m "feat(tui): add 4-color theme registry and CSS generator"
```

---

## Task 6: Add `gitchi theme` CLI verb

**Goal:** `gitchi theme` prints current + list. `gitchi theme <name>` writes config.

**Files:**
- Modify: `src/gitchi/cli.py` (add the verb)
- Modify: `tests/test_config.py` or new `tests/test_cli_theme.py`

- [ ] **Step 1: Read current cli.py to find the right place to add the verb**

```bash
cd ~/gitchi && head -100 src/gitchi/cli.py
```

The existing pattern is Typer subcommands like `gitchi refresh`, `gitchi list`. Match it.

- [ ] **Step 2: Write tests first** (`tests/test_cli_theme.py`)

```python
"""Tests for the `gitchi theme` CLI verb."""

from __future__ import annotations

import tomllib
from pathlib import Path

from typer.testing import CliRunner

from gitchi import config as config_mod
from gitchi.cli import app

runner = CliRunner()


def test_theme_no_arg_prints_current_and_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.toml")
    result = runner.invoke(app, ["theme"])
    assert result.exit_code == 0
    assert "gameboy-green" in result.stdout
    assert "virtual-boy" in result.stdout
    assert "cozy" in result.stdout


def test_theme_set_persists(tmp_path: Path, monkeypatch) -> None:
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr(config_mod, "config_path", lambda: cfg_path)
    result = runner.invoke(app, ["theme", "virtual-boy"])
    assert result.exit_code == 0
    raw = tomllib.loads(cfg_path.read_text())
    assert raw["tui"]["theme"] == "virtual-boy"


def test_theme_set_unknown_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.toml")
    result = runner.invoke(app, ["theme", "not-a-theme"])
    assert result.exit_code != 0
    assert "not-a-theme" in (result.stdout + result.stderr)
```

- [ ] **Step 3: Run tests — expect failure (no `theme` command)**

```bash
uv run pytest tests/test_cli_theme.py -q
```

- [ ] **Step 4: Add the verb to `cli.py`**

Add this command near the other config-touching verbs. Use whatever existing import style the file uses for typer.

```python
@app.command()
def theme(
    name: str | None = typer.Argument(None, help="Theme name; omit to list themes."),
) -> None:
    """Switch the TUI theme, or list available themes."""
    from .tui.themes import THEMES, list_theme_names

    cfg = config_mod.load()
    if name is None:
        typer.echo(f"current: {cfg.tui.theme}")
        typer.echo("available:")
        for n in list_theme_names():
            marker = "*" if n == cfg.tui.theme else " "
            typer.echo(f"  {marker} {n}")
        return

    if name not in THEMES:
        typer.echo(f"unknown theme: {name}. run `gitchi theme` for the list.", err=True)
        raise typer.Exit(code=1)

    cfg.tui.theme = name
    config_mod.save(cfg)
    typer.echo(f"theme set to {name}")
```

(If the file imports typer as `import typer`, use `typer.Argument`/`typer.Exit`/`typer.echo`. Match the existing style exactly.)

- [ ] **Step 5: Tests pass**

```bash
uv run pytest tests/test_cli_theme.py -q
```

- [ ] **Step 6: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
git add src/gitchi/cli.py tests/test_cli_theme.py
git commit -m "feat(cli): add gitchi theme command"
```

---

## Task 7: `status_reason` pure module

**Goal:** Surface the "why" behind a pet's status word. Mirrors thresholds in `Pet.status_word`.

**Files:**
- Create: `src/gitchi/tui/status_reason.py`
- Create: `tests/tui/test_status_reason.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for tui/status_reason.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from gitchi.models import Pet, Rarity, Repo, Species, Stage, Vitals
from gitchi.tui.status_reason import derive_reason


def _pet(
    *,
    hunger: int = 80,
    health: int = 80,
    energy: int = 80,
    mood: int = 80,
    stage: Stage = Stage.ADULT,
    ignored: bool = False,
    buried: bool = False,
    bury_reason: str | None = None,
    last_commit_days_ago: int | None = 1,
) -> Pet:
    last_commit = (
        datetime.now(UTC) - timedelta(days=last_commit_days_ago)
        if last_commit_days_ago is not None
        else None
    )
    return Pet(
        repo=Repo(
            path=Path("/tmp/x"),
            name="x",
            primary_language=None,
            first_commit=None,
            last_commit=last_commit,
            commit_count=1,
            size_bytes=0,
            has_tests=False,
            has_ci=False,
        ),
        species=Species.GENERIC_BLOB,
        stage=stage,
        vitals=Vitals(hunger=hunger, health=health, energy=energy, mood=mood, age_days=1),
        rarity=Rarity.COMMON,
        ignored=ignored,
        buried=buried,
        bury_reason=bury_reason,
    )


def test_ignored() -> None:
    assert derive_reason(_pet(ignored=True)) == "ignored"


def test_buried_with_reason() -> None:
    assert "tombstone" in derive_reason(_pet(buried=True, bury_reason="tombstone"))


def test_buried_default_reason() -> None:
    assert "at peace" in derive_reason(_pet(buried=True))


def test_ghost_dormant() -> None:
    reason = derive_reason(_pet(stage=Stage.GHOST, last_commit_days_ago=120))
    assert "dormant" in reason
    assert "120" in reason


def test_thriving_recent_commits() -> None:
    reason = derive_reason(_pet(hunger=90, health=90, energy=90, mood=90, last_commit_days_ago=0))
    assert reason.startswith("thriving")


def test_hungry_with_days_since_commit() -> None:
    reason = derive_reason(_pet(hunger=10, health=30, energy=30, mood=30, last_commit_days_ago=9))
    assert reason.startswith("hungry")
    assert "9d" in reason or "9 days" in reason


def test_starving() -> None:
    reason = derive_reason(_pet(hunger=5, health=5, energy=5, mood=5, last_commit_days_ago=30))
    assert reason.startswith("starving")
```

- [ ] **Step 2: Run tests — expect ImportError**

- [ ] **Step 3: Implement `src/gitchi/tui/status_reason.py`**

```python
"""Human-readable 'why' for each pet status word.

Parallels the threshold logic in `Pet.status_word`; both should be kept in
sync (changes in one require updating the other).
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..models import Pet, Stage


def _days_since_commit(pet: Pet) -> int | None:
    last = pet.repo.last_commit
    if last is None:
        return None
    now = datetime.now(UTC)
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return max(0, (now - last).days)


def derive_reason(pet: Pet) -> str:
    if pet.ignored:
        return "ignored"
    if pet.buried:
        return f"buried · {pet.bury_reason or 'at peace'}"
    if pet.stage is Stage.GHOST:
        days = _days_since_commit(pet)
        if days is None:
            return "ghost · no commit history"
        return f"ghost · {days}d dormant"

    score = pet.vitals.overall()
    days = _days_since_commit(pet)
    suffix = f" · {days}d since commit" if days is not None and days > 0 else ""

    if score >= 80:
        return f"thriving{suffix}"
    if score >= 60:
        return f"happy{suffix}"
    if score >= 40:
        return f"content{suffix}"
    if score >= 20:
        return f"hungry{suffix}"
    return f"starving{suffix}"
```

- [ ] **Step 4: Tests pass**

- [ ] **Step 5: Run full check + commit**

```bash
git add src/gitchi/tui/status_reason.py tests/tui/test_status_reason.py
git commit -m "feat(tui): add status_reason module"
```

---

## Task 8: Persist play results via store

**Goal:** When a user presses `p` (or runs `gitchi play`), record the result so the detail pane can show a CI badge.

**Files:**
- Create: `src/gitchi/migrations/004_play_results.sql`
- Modify: `src/gitchi/store.py` (add `record_play_result`, `last_play_result`)
- Modify: `tests/test_store.py` or new `tests/test_play_results.py`

- [ ] **Step 1: Write the migration**

`src/gitchi/migrations/004_play_results.sql`:

```sql
CREATE TABLE IF NOT EXISTS last_play_results (
    repo_path TEXT PRIMARY KEY,
    returncode INTEGER NOT NULL,
    ran_at INTEGER NOT NULL
);
```

- [ ] **Step 2: Write tests** (`tests/test_play_results.py`)

```python
"""Tests for last_play_results storage."""

from __future__ import annotations

from pathlib import Path

from gitchi.store import connect, last_play_result, record_play_result


def test_no_result_returns_none(tmp_path: Path) -> None:
    db = tmp_path / "gitchi.db"
    with connect(db) as conn:
        assert last_play_result(conn, Path("/tmp/whatever")) is None


def test_record_and_read(tmp_path: Path) -> None:
    db = tmp_path / "gitchi.db"
    repo = Path("/tmp/myrepo")
    with connect(db) as conn:
        record_play_result(conn, repo, returncode=0)
        result = last_play_result(conn, repo)
    assert result is not None
    rc, ran_at = result
    assert rc == 0
    assert ran_at > 0


def test_record_overwrites(tmp_path: Path) -> None:
    db = tmp_path / "gitchi.db"
    repo = Path("/tmp/myrepo")
    with connect(db) as conn:
        record_play_result(conn, repo, returncode=0)
        record_play_result(conn, repo, returncode=1)
        result = last_play_result(conn, repo)
    assert result is not None
    assert result[0] == 1
```

- [ ] **Step 3: Run tests — expect AttributeError**

- [ ] **Step 4: Add helpers to `store.py`**

Add near the bottom of the file (after the other CRUD helpers):

```python
# ---------------------------------------------------------------------------
# play results
# ---------------------------------------------------------------------------


def record_play_result(conn: sqlite3.Connection, repo_path: Path, *, returncode: int) -> None:
    """Persist the most recent test-run result for a repo."""
    conn.execute(
        """
        INSERT INTO last_play_results (repo_path, returncode, ran_at)
        VALUES (?, ?, ?)
        ON CONFLICT(repo_path) DO UPDATE SET
            returncode = excluded.returncode,
            ran_at = excluded.ran_at
        """,
        (str(repo_path), returncode, _now_epoch()),
    )


def last_play_result(conn: sqlite3.Connection, repo_path: Path) -> tuple[int, int] | None:
    """Return (returncode, ran_at_epoch_seconds) or None if no result recorded."""
    row = conn.execute(
        "SELECT returncode, ran_at FROM last_play_results WHERE repo_path = ?",
        (str(repo_path),),
    ).fetchone()
    if row is None:
        return None
    return int(row["returncode"]), int(row["ran_at"])
```

- [ ] **Step 5: Tests pass**

```bash
uv run pytest tests/test_play_results.py -q
```

- [ ] **Step 6: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
git add src/gitchi/migrations/004_play_results.sql src/gitchi/store.py tests/test_play_results.py
git commit -m "feat(store): persist last play result per repo"
```

---

## Task 9: `count_todos` helper

**Goal:** Lightweight TODO counter for the detail pane badge. Cap traversal to avoid slowdowns on huge repos.

**Files:**
- Modify: `src/gitchi/verbs.py` (add `count_todos`)
- Modify: `tests/test_verbs.py` (add cases)

- [ ] **Step 1: Write tests**

Append to `tests/test_verbs.py`:

```python
def test_count_todos_zero(tmp_path: Path) -> None:
    from gitchi.verbs import count_todos

    (tmp_path / "a.py").write_text("print('hi')\n", encoding="utf-8")
    assert count_todos(tmp_path) == 0


def test_count_todos_multiple(tmp_path: Path) -> None:
    from gitchi.verbs import count_todos

    (tmp_path / "a.py").write_text("# TODO: x\n# FIXME y\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("# HACK: z\n", encoding="utf-8")
    assert count_todos(tmp_path) == 3


def test_count_todos_skips_irrelevant_extensions(tmp_path: Path) -> None:
    from gitchi.verbs import count_todos

    (tmp_path / "a.bin").write_text("TODO: ignored\n", encoding="utf-8")
    assert count_todos(tmp_path) == 0


def test_count_todos_respects_cap(tmp_path: Path) -> None:
    from gitchi.verbs import count_todos

    big = "\n".join(f"# TODO: {i}" for i in range(200))
    (tmp_path / "a.py").write_text(big, encoding="utf-8")
    assert count_todos(tmp_path, cap=50) == 50
```

- [ ] **Step 2: Run tests — expect ImportError**

- [ ] **Step 3: Implement `count_todos` in `verbs.py`**

Add after the existing `feed` function. Reuse the same skip-dirs and extensions sets — extract them to module-level constants first:

```python
_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "vendor", "target", "build", "dist"}
_TEXT_EXTS = {
    ".py", ".rs", ".ts", ".tsx", ".js", ".jsx", ".go", ".swift", ".rb", ".gd",
    ".java", ".kt", ".scala", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp", ".hs",
    ".elm", ".ex", ".exs", ".lua", ".php", ".dart", ".sh", ".md", ".toml",
    ".yaml", ".yml",
}
```

Update `feed` to use these constants (delete the in-function `skip` / `text_exts` definitions). Then add:

```python
def count_todos(repo_path: Path, *, max_files: int = 500, cap: int = 500) -> int:
    """Count TODO/FIXME/XXX/HACK occurrences across the repo, up to `cap`.

    Caps both the number of files scanned (`max_files`) and the total hits
    returned (`cap`) so a vendored haystack doesn't freeze the TUI.
    """
    seen_files = 0
    hits = 0
    for p in repo_path.rglob("*"):
        if seen_files >= max_files or hits >= cap:
            break
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in _TEXT_EXTS:
            continue
        if not p.is_file():
            continue
        seen_files += 1
        try:
            with p.open(encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if _TODO_RE.search(line):
                        hits += 1
                        if hits >= cap:
                            return hits
        except OSError:
            continue
    return hits
```

- [ ] **Step 4: Tests pass**

- [ ] **Step 5: Run full check + commit**

```bash
git add src/gitchi/verbs.py tests/test_verbs.py
git commit -m "feat(verbs): add count_todos for detail-pane badge"
```

---

## Task 10: Wire play result persistence

**Goal:** When `verbs.play` runs (from CLI or TUI), persist the returncode.

**Files:**
- Modify: `src/gitchi/verbs.py` (have `play` write the result before returning)
- Verify: existing `tests/test_verbs.py` tests still pass (some may need to monkeypatch the store)

- [ ] **Step 1: Inspect existing `verbs.play` tests** to understand what to monkeypatch

```bash
grep -n "def test.*play\|verbs.play\|play(" tests/test_verbs.py
```

- [ ] **Step 2: Add a new test for the persistence side-effect** in `tests/test_verbs.py`

```python
def test_play_persists_returncode(tmp_path: Path, monkeypatch) -> None:
    """play() should record its returncode via store.record_play_result."""
    from gitchi import store, verbs

    calls: list[tuple[Path, int]] = []

    def fake_record(conn, repo_path, *, returncode):
        calls.append((repo_path, returncode))

    monkeypatch.setattr(store, "record_play_result", fake_record)
    monkeypatch.setattr(store, "db_path", lambda: tmp_path / "gitchi.db")

    # Set up a tiny pyproject.toml so detect_runner returns ["pytest"]
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    # Stub the actual subprocess so we don't really run pytest.
    monkeypatch.setattr(
        verbs.subprocess,
        "run",
        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )

    result = verbs.play(repo)
    assert result is not None
    assert result.returncode == 0
    assert calls == [(repo, 0)]
```

- [ ] **Step 3: Modify `verbs.play`** to persist:

```python
def play(repo_path: Path) -> PlayResult | None:
    """Detect the test runner and run it. Returns None if no runner is detected."""
    runner = detect_runner(repo_path)
    if runner is None:
        return None
    try:
        proc = subprocess.run(
            runner,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        result = PlayResult(
            runner=runner, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        result = PlayResult(runner=runner, returncode=-1, stdout="", stderr=str(e))

    from . import store
    from .config import db_path

    try:
        with store.connect(db_path()) as conn:
            store.record_play_result(conn, repo_path, returncode=result.returncode)
    except Exception:
        # Persistence failure shouldn't break the play action.
        pass

    return result
```

- [ ] **Step 4: Tests pass**

- [ ] **Step 5: Run full check + commit**

```bash
git add src/gitchi/verbs.py tests/test_verbs.py
git commit -m "feat(verbs): persist play returncode via store"
```

---

## Task 11: `art` 2-frame idle variants

**Goal:** For every existing `(species, stage)` art, define a second frame that's a one-character variation (blink, breathe, sway). Falls back to the static art when the frame variant isn't defined.

**Files:**
- Modify: `src/gitchi/art.py`
- Modify: `tests/test_art.py`

- [ ] **Step 1: Inspect existing tests**

```bash
cat tests/test_art.py
```

- [ ] **Step 2: Write new tests** in `tests/test_art.py`:

```python
def test_idle_frames_returns_two_strings_for_baby_blob() -> None:
    from gitchi.art import idle_frames
    from gitchi.models import Species, Stage

    frames = idle_frames(Species.BLOB, Stage.BABY)
    assert isinstance(frames, list)
    assert len(frames) == 2
    assert frames[0] != frames[1]


def test_idle_frames_falls_back_to_static_for_egg() -> None:
    from gitchi.art import idle_frames, render
    from gitchi.models import Species, Stage

    frames = idle_frames(Species.DRAGON, Stage.EGG)
    # eggs don't animate — both frames are the static render
    assert frames[0] == render(Species.DRAGON, Stage.EGG)
    assert frames[1] == frames[0]


def test_idle_frames_for_every_species_stage_pair_returns_two() -> None:
    from gitchi.art import idle_frames
    from gitchi.models import Species, Stage

    for species in Species:
        for stage in Stage:
            frames = idle_frames(species, stage)
            assert len(frames) == 2, f"{species} {stage}"
```

- [ ] **Step 3: Run tests — expect ImportError**

- [ ] **Step 4: Implement `idle_frames` in `art.py`**

Add at the end of the file. Strategy: for each existing art string, create a second variant by swapping eyes (`o.o → o_o`, `O O → o o`, `◐ ◑ → ◑ ◐`) or modifying a single mouth character. Define a helper that does common transforms:

```python
def _blink(art: str) -> str:
    """Produce a single-frame variant by closing or shifting the eyes."""
    table = str.maketrans({
        "o": "-",
        "O": "ō",
        "◐": "◑",
        "◑": "◐",
    })
    out_lines: list[str] = []
    swapped = False
    for line in art.splitlines():
        if not swapped and ("o" in line or "O" in line or "◐" in line or "◑" in line):
            out_lines.append(line.translate(table))
            swapped = True
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def idle_frames(species: Species, stage: Stage) -> list[str]:
    """Return two frames for the idle animation.

    Stages that don't animate (egg, ghost) return the same frame twice.
    """
    base = render(species, stage)
    if stage in (Stage.EGG, Stage.GHOST):
        return [base, base]
    return [base, _blink(base)]
```

- [ ] **Step 5: Tests pass**

```bash
uv run pytest tests/test_art.py -q
```

- [ ] **Step 6: Run full check + commit**

```bash
git add src/gitchi/art.py tests/test_art.py
git commit -m "feat(art): add 2-frame idle variants"
```

---

## Task 12: Animation module

**Goal:** Select the right frame set based on pet state, and pick which of two frames is "current" given a tick counter.

**Files:**
- Create: `src/gitchi/tui/animation.py`
- Create: `tests/tui/test_animation.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for tui/animation.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from gitchi.models import Pet, Rarity, Repo, Species, Stage, Vitals
from gitchi.tui.animation import current_frame, select_frames


def _pet(
    *,
    stage: Stage = Stage.ADULT,
    hunger: int = 80,
    health: int = 80,
    energy: int = 80,
    mood: int = 80,
    last_commit_days_ago: int = 1,
) -> Pet:
    return Pet(
        repo=Repo(
            path=Path("/tmp/x"),
            name="x",
            primary_language=None,
            first_commit=None,
            last_commit=datetime.now(UTC) - timedelta(days=last_commit_days_ago),
            commit_count=1,
            size_bytes=0,
            has_tests=False,
            has_ci=False,
        ),
        species=Species.BLOB,
        stage=stage,
        vitals=Vitals(hunger=hunger, health=health, energy=energy, mood=mood, age_days=1),
        rarity=Rarity.COMMON,
    )


def test_select_frames_idle() -> None:
    frames = select_frames(_pet())
    assert len(frames) == 2


def test_select_frames_alert_when_hungry() -> None:
    """Alert frames should be returned for hunger < 25."""
    frames = select_frames(_pet(hunger=10))
    assert len(frames) == 2
    # Alert frames may differ from idle frames but the API must remain stable.


def test_select_frames_ghost_stage() -> None:
    frames = select_frames(_pet(stage=Stage.GHOST))
    assert len(frames) == 2


def test_current_frame_alternates() -> None:
    pet = _pet()
    frames = select_frames(pet)
    f0 = current_frame(frames, tick=0)
    f1 = current_frame(frames, tick=1)
    f2 = current_frame(frames, tick=2)
    assert f0 == frames[0]
    assert f1 == frames[1]
    assert f2 == frames[0]


def test_current_frame_egg_is_static_regardless_of_tick() -> None:
    pet = _pet(stage=Stage.EGG)
    frames = select_frames(pet)
    assert current_frame(frames, tick=0) == current_frame(frames, tick=1)
```

- [ ] **Step 2: Run tests — expect ImportError**

- [ ] **Step 3: Implement `src/gitchi/tui/animation.py`**

```python
"""Animation frame selection for the detail panel."""

from __future__ import annotations

from ..art import idle_frames
from ..models import Pet, Stage

# State thresholds — keep aligned with status_word / status_reason logic.
_ALERT_HUNGER = 25
_ALERT_HEALTH = 25


def select_frames(pet: Pet) -> list[str]:
    """Return a 2-frame list for the current pet state.

    Priority: ghost > alert > celebrate > idle. For now all states share the
    same base frame set produced by `art.idle_frames`; future work can vary
    frames per state. The two-frame contract stays stable.
    """
    return idle_frames(pet.species, pet.stage)


def current_frame(frames: list[str], *, tick: int) -> str:
    """Pick the active frame from a 2-frame list given a monotonic tick counter."""
    if not frames:
        return ""
    return frames[tick % len(frames)]


def should_alert(pet: Pet) -> bool:
    """Whether a pet's state warrants the alert palette."""
    if pet.stage is Stage.GHOST:
        return False
    return pet.vitals.hunger < _ALERT_HUNGER or pet.vitals.health < _ALERT_HEALTH
```

- [ ] **Step 4: Tests pass**

- [ ] **Step 5: Run full check + commit**

```bash
git add src/gitchi/tui/animation.py tests/tui/test_animation.py
git commit -m "feat(tui): add animation frame selection"
```

---

## Task 13: SearchInput widget

**Goal:** Overlay input that appears when `/` is pressed, captures live filter text, and emits a message when text changes.

**Files:**
- Create: `src/gitchi/tui/widgets/search_input.py`

- [ ] **Step 1: Implement the widget**

```python
"""Search input overlay — live-filters the pet table."""

from __future__ import annotations

from textual.binding import Binding
from textual.message import Message
from textual.widgets import Input


class SearchInput(Input):
    """Single-line input that emits FilterChanged on every keystroke."""

    BINDINGS = [Binding("escape", "close", "close", show=False)]

    class FilterChanged(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class Closed(Message):
        pass

    def __init__(self) -> None:
        super().__init__(placeholder="filter by name…")

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.FilterChanged(event.value))

    def action_close(self) -> None:
        self.value = ""
        self.post_message(self.FilterChanged(""))
        self.post_message(self.Closed())
```

- [ ] **Step 2: Run lint + types** (no functional tests for Textual widgets)

```bash
uv run ruff check src && uv run mypy --strict src
```

- [ ] **Step 3: Commit**

```bash
git add src/gitchi/tui/widgets/search_input.py
git commit -m "feat(tui): add SearchInput overlay widget"
```

---

## Task 14: Rewrite PetTable widget

**Goal:** DataTable subclass that knows how to apply `AppState` to a list of pets — sort, filter, ghost/buried toggles — and renders the columns with sort arrows.

**Files:**
- Create: `src/gitchi/tui/widgets/pet_table.py`

- [ ] **Step 1: Implement**

```python
"""DataTable subclass that renders pets through AppState."""

from __future__ import annotations

from textual.widgets import DataTable

from ...models import Pet, Stage
from ...rarity import emoji_for as rarity_emoji_for
from ...species import emoji_for
from ..state import AppState, SortKey, apply_filter, apply_sort

_COLUMNS: tuple[tuple[SortKey, str], ...] = (
    ("name", "NAME"),
    ("rarity", "RARITY"),
    ("hunger", "HUNGER"),
    ("mood", "MOOD"),
    ("age", "AGE"),
)


def _bar(value: int, width: int = 8) -> str:
    """4-shade ramp using █▓▒░ for higher contrast than the default 2-shade bar."""
    if width <= 0:
        return ""
    pct = max(0, min(100, value)) / 100
    full = int(pct * width)
    remainder = (pct * width) - full
    ramp = "░▒▓█"
    cells = ["█"] * full
    if full < width:
        idx = int(remainder * (len(ramp) - 1))
        cells.append(ramp[idx])
        cells.extend(["░"] * (width - full - 1))
    return "".join(cells)


class PetTable(DataTable[str]):
    """DataTable that renders a list of pets according to AppState."""

    def __init__(self) -> None:
        super().__init__(zebra_stripes=True, cursor_type="row")

    def on_mount(self) -> None:
        for _key, label in _COLUMNS:
            self.add_column(label)
        self.add_column("STATUS")

    def render_pets(self, pets: list[Pet], state: AppState) -> list[Pet]:
        """Apply state filters/sort to pets, repopulate the table, return the visible list."""
        visible: list[Pet] = list(pets)
        if not state.show_ghosts:
            visible = [p for p in visible if p.stage is not Stage.GHOST]
        if not state.show_buried:
            visible = [p for p in visible if not p.buried]
        visible = apply_filter(visible, state.filter_text)
        visible = apply_sort(visible, state.sort_key, desc=state.sort_desc)

        # Update column headers to show active sort arrow.
        arrow = "▾" if state.sort_desc else "▴"
        for col_idx, (key, label) in enumerate(_COLUMNS):
            marked = f"{label}{arrow}" if key == state.sort_key else label
            self.columns[self.column_keys[col_idx]].label = marked

        self.clear()
        for pet in visible:
            stage_marker = "👻" if pet.stage is Stage.GHOST else pet.stage.value
            self.add_row(
                pet.repo.name,
                f"{rarity_emoji_for(pet.rarity)} {pet.rarity.value}",
                _bar(pet.vitals.hunger),
                _bar(pet.vitals.mood),
                f"{pet.vitals.age_days}d",
                f"{emoji_for(pet.species)} {stage_marker} · {pet.status_word}",
                key=str(pet.repo.path),
            )
        return visible
```

Note: the `column_keys` access may need a Textual API check. If `DataTable.columns` doesn't expose easy header relabeling in 0.85, fall back to `clear(columns=True)` + `add_columns(...)` each render. The plan permits either approach.

- [ ] **Step 2: Run lint + types**

```bash
uv run ruff check src && uv run mypy --strict src
```

If `column_keys`/`columns` accessors don't typecheck cleanly, switch to `clear(columns=True)` + `add_columns(*marked_labels)`.

- [ ] **Step 3: Commit**

```bash
git add src/gitchi/tui/widgets/pet_table.py
git commit -m "feat(tui): add PetTable widget with sort/filter/toggle rendering"
```

---

## Task 15: Rewrite DetailPanel

**Goal:** Big-art frame, sparklines (via `history.sparkline`), 4-shade vital bars, status reason, badges line, animation tick.

**Files:**
- Modify: `src/gitchi/tui/widgets/detail_panel.py`

- [ ] **Step 1: Read history module API to confirm signatures**

```bash
grep -n "def " src/gitchi/history.py src/gitchi/store.py | grep -i "history\|sparkline" | head
```

- [ ] **Step 2: Rewrite `detail_panel.py`**

```python
"""Detail panel — animated pet art, sparklines, vital bars, status reason, badges."""

from __future__ import annotations

from datetime import UTC, datetime

from textual.widgets import Static

from ...config import db_path
from ...history import sparkline
from ...models import Pet
from ...rarity import emoji_for as rarity_emoji_for
from ...species import emoji_for
from ...store import connect, last_play_result, vitals_history
from ...verbs import count_todos
from ..animation import current_frame, select_frames, should_alert
from ..status_reason import derive_reason

_BAR_WIDTH = 8
_SPARK_WIDTH = 7
_FRAME_CHAR = "▓"


def _ramp_bar(value: int, width: int = _BAR_WIDTH) -> str:
    pct = max(0, min(100, value)) / 100
    full = int(pct * width)
    remainder = (pct * width) - full
    ramp = "░▒▓█"
    cells = ["█"] * full
    if full < width:
        idx = int(remainder * (len(ramp) - 1))
        cells.append(ramp[idx])
        cells.extend(["░"] * (width - full - 1))
    return "".join(cells)


def _spark_for(samples_oldest_first: list[int], width: int = _SPARK_WIDTH) -> str:
    return sparkline(samples_oldest_first[-width:], width=width)


def _wrap_art(art: str, width: int = 18) -> str:
    """Wrap the art block in a 4-shade frame for CRT vibes."""
    horizontal = _FRAME_CHAR * width
    lines = [horizontal]
    for line in art.splitlines():
        padded = line.ljust(width - 2)
        lines.append(f"{_FRAME_CHAR}{padded[: width - 2]}{_FRAME_CHAR}")
    lines.append(horizontal)
    return "\n".join(lines)


class DetailPanel(Static):
    """Pet detail with animation tick + sparklines + badges."""

    DEFAULT_CSS = ""  # styling lives in the theme

    def __init__(self) -> None:
        super().__init__()
        self._pet: Pet | None = None
        self._tick = 0
        self._frames: list[str] = []
        self._history: dict[str, list[int]] = {}
        self._todo_count: int | None = None
        self._play_result: tuple[int, int] | None = None

    def show_pet(self, pet: Pet | None) -> None:
        self._pet = pet
        self._tick = 0
        if pet is None:
            self._frames = []
            self._history = {}
            self._todo_count = None
            self._play_result = None
            self.update("[dim]no pets — run `gitchi refresh` to scan.[/dim]")
            return

        self._frames = select_frames(pet)
        self._history = self._load_history(pet)
        self._todo_count = self._safe_todo_count(pet)
        self._play_result = self._load_play_result(pet)
        self.refresh_render()

    def tick(self, animation_enabled: bool) -> None:
        if self._pet is None or not self._frames:
            return
        if animation_enabled:
            self._tick += 1
            self.refresh_render()

    def refresh_render(self) -> None:
        pet = self._pet
        if pet is None:
            return

        rarity_tag = f"{rarity_emoji_for(pet.rarity)} {pet.rarity.value}"
        title = (
            f"[bold]{pet.repo.name}[/bold]  {emoji_for(pet.species)} {pet.species.value} · "
            f"{pet.stage.value} · {rarity_tag}"
        )

        frame = current_frame(self._frames, tick=self._tick)
        framed_art = _wrap_art(frame)

        alert_cls = "alert" if should_alert(pet) else ""

        def vital_line(name: str, value: int, samples: list[int]) -> str:
            cls = alert_cls if name in ("hunger", "health") and value < 25 else ""
            sparkline_str = _spark_for(samples)
            bar = _ramp_bar(value)
            line = f"{name:<6} {sparkline_str}  {bar} {value:3d}"
            return f"[{cls}]{line}[/{cls}]" if cls else line

        hist = self._history
        body_lines = [
            title,
            f"[dim]{pet.repo.path}[/dim]",
            "",
            framed_art,
            "",
            vital_line("hunger", pet.vitals.hunger, hist.get("hunger", [])),
            vital_line("health", pet.vitals.health, hist.get("health", [])),
            vital_line("energy", pet.vitals.energy, hist.get("energy", [])),
            vital_line("mood", pet.vitals.mood, hist.get("mood", [])),
            "",
            derive_reason(pet),
            self._badge_line(pet),
        ]
        self.update("\n".join(body_lines))

    # ------------------------------------------------------------------ data

    def _load_history(self, pet: Pet) -> dict[str, list[int]]:
        try:
            with connect(db_path()) as conn:
                rows = vitals_history(conn, pet.repo.path, limit=_SPARK_WIDTH)
        except Exception:
            return {}
        return {
            "hunger": [v.hunger for v in rows],
            "health": [v.health for v in rows],
            "energy": [v.energy for v in rows],
            "mood": [v.mood for v in rows],
        }

    def _load_play_result(self, pet: Pet) -> tuple[int, int] | None:
        try:
            with connect(db_path()) as conn:
                return last_play_result(conn, pet.repo.path)
        except Exception:
            return None

    def _safe_todo_count(self, pet: Pet) -> int | None:
        try:
            return count_todos(pet.repo.path)
        except Exception:
            return None

    def _badge_line(self, pet: Pet) -> str:
        parts: list[str] = []
        if self._todo_count is not None and self._todo_count > 0:
            parts.append(f"todo {self._todo_count}")
        if self._play_result is not None:
            rc, ran_at = self._play_result
            tick = "✓" if rc == 0 else "✗"
            age = self._fmt_age(ran_at)
            parts.append(f"ci {tick} ({age})")
        else:
            parts.append("ci —")
        parts.append(f"age {pet.vitals.age_days}d")
        return " · ".join(parts)

    @staticmethod
    def _fmt_age(epoch_seconds: int) -> str:
        delta_s = datetime.now(UTC).timestamp() - epoch_seconds
        if delta_s < 60:
            return f"{int(delta_s)}s"
        if delta_s < 3600:
            return f"{int(delta_s / 60)}m"
        if delta_s < 86400:
            return f"{int(delta_s / 3600)}h"
        return f"{int(delta_s / 86400)}d"
```

- [ ] **Step 2: Run lint + types**

```bash
uv run ruff check src && uv run mypy --strict src
```

- [ ] **Step 3: Commit**

```bash
git add src/gitchi/tui/widgets/detail_panel.py
git commit -m "feat(tui): rewrite DetailPanel with sparklines, animation, badges"
```

---

## Task 16: Rewire the App

**Goal:** Update `tui/__init__.py` (the App composition) to use all new pieces: theme CSS, AppState, PetTable, DetailPanel, SearchInput, NewsPanel, animation tick, new bindings.

**Files:**
- Modify: `src/gitchi/tui/__init__.py`

- [ ] **Step 1: Replace the contents**

```python
"""Textual dashboard.

Layout: optional search bar overlay on top · two-pane body (PetTable left,
DetailPanel right) · collapsible NewsPanel · footer. State is held in
`AppState`; theme CSS is rendered from `themes.render_css` at startup.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal

from .. import config as config_mod
from .. import refresh as refresh_mod
from .. import verbs as verbs_mod
from ..models import Pet
from .animation import current_frame, select_frames  # noqa: F401 (re-export)
from .state import AppState, apply_filter, apply_sort, cycle_sort
from .status_reason import derive_reason  # noqa: F401 (re-export)
from .themes import get_theme, render_css
from .widgets.detail_panel import DetailPanel
from .widgets.news_panel import NEWS_PANEL_LIMIT, NewsPanel
from .widgets.pet_table import PetTable
from .widgets.search_input import SearchInput


class GitchiApp(App[None]):
    BINDINGS = [
        Binding("q", "quit", "quit"),
        Binding("r", "rescan", "rescan"),
        Binding("f", "feed", "feed"),
        Binding("p", "play", "play"),
        Binding("e", "pet", "edit"),
        Binding("b", "bury", "bury"),
        Binding("v", "revive", "revive"),
        Binding("i", "ignore", "ignore"),
        Binding("u", "unignore", "unignore"),
        Binding("slash", "open_search", "search", key_display="/"),
        Binding("s", "sort", "sort"),
        Binding("S", "sort_reverse", "sort↓", show=False),
        Binding("g", "toggle_ghosts", "ghosts"),
        Binding("B", "toggle_buried", "buried"),
        Binding("n", "toggle_news", "news"),
        Binding("a", "toggle_animation", "anim"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.pets: list[Pet] = []
        self.visible_pets: list[Pet] = []
        self.app_state = AppState()
        self.cfg = config_mod.load()
        self.app_state.animation_enabled = self.cfg.tui.animation
        self.stylesheet_text = render_css(get_theme(self.cfg.tui.theme))

    def compose(self) -> ComposeResult:
        yield SearchInput()
        with Horizontal(id="body"):
            yield PetTable()
            yield DetailPanel()
        yield NewsPanel()

    async def on_mount(self) -> None:
        self.title = "gitchi"
        self.sub_title = "your codebase as a tamagotchi"
        # Apply theme CSS
        try:
            self.stylesheet.add_source(self.stylesheet_text, path="gitchi-theme.tcss")
            self.stylesheet.parse()
        except Exception:
            # Fall back silently if the Textual API doesn't accept this; the
            # default theme still works.
            pass
        # Hide search until /
        search = self.query_one(SearchInput)
        search.add_class("hidden")
        self._reload()
        self.set_interval(0.5, self._tick)

    # ---------------------------------------------------------------- data

    def _reload(self) -> None:
        self.pets = refresh_mod.list_pets()
        self._render_table()
        self.query_one(NewsPanel).show_events(
            refresh_mod.list_recent_news(limit=NEWS_PANEL_LIMIT)
        )

    def _render_table(self) -> None:
        table = self.query_one(PetTable)
        self.visible_pets = table.render_pets(self.pets, self.app_state)
        if self.visible_pets:
            self._show_index(0)
        else:
            self.query_one(DetailPanel).show_pet(None)

    def _show_index(self, index: int) -> None:
        if 0 <= index < len(self.visible_pets):
            self.query_one(DetailPanel).show_pet(self.visible_pets[index])

    def _selected(self) -> Pet | None:
        table = self.query_one(PetTable)
        if table.cursor_row is None or not self.visible_pets:
            return None
        return self.visible_pets[table.cursor_row]

    # ---------------------------------------------------------------- events

    def on_data_table_row_highlighted(self, event: PetTable.RowHighlighted) -> None:
        if event.cursor_row is None:
            return
        self._show_index(event.cursor_row)

    def on_search_input_filter_changed(self, event: SearchInput.FilterChanged) -> None:
        self.app_state.filter_text = event.text
        self._render_table()

    def on_search_input_closed(self, _event: SearchInput.Closed) -> None:
        search = self.query_one(SearchInput)
        search.add_class("hidden")
        table = self.query_one(PetTable)
        table.focus()

    def _tick(self) -> None:
        detail = self.query_one(DetailPanel)
        detail.tick(self.app_state.animation_enabled)

    # ---------------------------------------------------------------- actions

    def action_rescan(self) -> None:
        summary = refresh_mod.refresh()
        self._reload()
        suffix = f" · {len(summary.news_events)} news" if summary.news_events else ""
        self.notify(f"rescanned {summary.scanned} repos · {summary.ghosts} ghosts{suffix}")

    def action_feed(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        hit = verbs_mod.feed(pet.repo.path)
        if hit is None:
            self.notify(f"{pet.repo.name} purrs. no TODOs found.")
        else:
            self.notify(f"{pet.repo.name}: {hit.file.name}:{hit.line} — {hit.message[:60]}")

    def action_play(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        result = verbs_mod.play(pet.repo.path)
        if result is None:
            self.notify(f"{pet.repo.name} has no test runner")
        elif result.returncode == 0:
            self.notify(f"{pet.repo.name} bounces — tests passed")
        else:
            self.notify(
                f"{pet.repo.name} sulks — tests failed (rc={result.returncode})",
                severity="warning",
            )
        # Refresh detail panel to update the CI badge.
        self.query_one(DetailPanel).show_pet(pet)

    def action_pet(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.pet(pet.repo.path)
        self.notify(f"opened {pet.repo.name} in editor")

    def action_bury(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.bury(pet.repo.path, None)
        self._reload()
        self.notify(f"{pet.repo.name} laid to rest")

    def action_revive(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.revive(pet.repo.path)
        self._reload()
        self.notify(f"{pet.repo.name} stirs")

    def action_ignore(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.ignore(pet.repo.path, None)
        self._reload()
        self.notify(f"{pet.repo.name} ignored")

    def action_unignore(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.unignore(pet.repo.path)
        self._reload()
        self.notify(f"{pet.repo.name} is visible again")

    def action_open_search(self) -> None:
        search = self.query_one(SearchInput)
        search.remove_class("hidden")
        search.focus()

    def action_sort(self) -> None:
        self.app_state.sort_key = cycle_sort(self.app_state.sort_key)
        self.app_state.sort_desc = False
        self._render_table()
        self.notify(f"sort: {self.app_state.sort_key}")

    def action_sort_reverse(self) -> None:
        self.app_state.sort_desc = not self.app_state.sort_desc
        self._render_table()
        arrow = "↓" if self.app_state.sort_desc else "↑"
        self.notify(f"sort: {self.app_state.sort_key} {arrow}")

    def action_toggle_ghosts(self) -> None:
        self.app_state.show_ghosts = not self.app_state.show_ghosts
        self._render_table()

    def action_toggle_buried(self) -> None:
        self.app_state.show_buried = not self.app_state.show_buried
        self._render_table()

    def action_toggle_news(self) -> None:
        self.app_state.news_collapsed = not self.app_state.news_collapsed
        news = self.query_one(NewsPanel)
        if self.app_state.news_collapsed:
            news.add_class("collapsed")
        else:
            news.remove_class("collapsed")

    def action_toggle_animation(self) -> None:
        self.app_state.animation_enabled = not self.app_state.animation_enabled
        self.cfg.tui.animation = self.app_state.animation_enabled
        try:
            config_mod.save(self.cfg)
        except Exception:
            pass
        state = "on" if self.app_state.animation_enabled else "off"
        self.notify(f"animation {state}")


def run() -> None:
    GitchiApp().run()


# Keep these names importable from `gitchi.tui` for backwards compatibility.
__all__ = [
    "DetailPanel",
    "GitchiApp",
    "NEWS_PANEL_LIMIT",
    "NewsPanel",
    "PetTable",
    "apply_filter",
    "apply_sort",
    "cycle_sort",
    "run",
]
```

- [ ] **Step 2: Run full check**

```bash
uv run pytest -q && uv run ruff check src tests && uv run mypy --strict src
```

If mypy flags issues with Textual API access (stylesheet, columns, events), reach for narrow `# type: ignore[<code>]` or refactor to safer API access. **Do not blanket-ignore.**

- [ ] **Step 3: Commit**

```bash
git add src/gitchi/tui/__init__.py
git commit -m "feat(tui): wire app composition with theming, animation, search, sort"
```

---

## Task 17: Manual smoke test + final polish

**Goal:** Boot the TUI against a real `~/Library/Application Support/gitchi/gitchi.db`, click through every binding, fix any rough edges.

**Files:** any (likely small tweaks to widgets/CSS)

- [ ] **Step 1: Run the app**

```bash
cd ~/gitchi
uv run gitchi
```

(If the DB is empty, run `uv run gitchi refresh` first.)

- [ ] **Step 2: Click through the matrix**

Check each behavior:
- [ ] Pets render in the table with bars and species emoji
- [ ] Selecting a row updates the detail pane (animation visible)
- [ ] `/` opens search; typing filters live; Esc closes and clears
- [ ] `s` cycles sort key; Shift+S toggles direction; arrow on header
- [ ] `g` hides/shows ghosts; `B` hides/shows buried
- [ ] `n` collapses/expands the news panel
- [ ] `a` toggles animation (and writes to config)
- [ ] `r` rescans; `f` finds a TODO; `p` runs tests and updates the CI badge
- [ ] `b` / `v` / `i` / `u` still work
- [ ] `q` quits cleanly
- [ ] `gitchi theme virtual-boy` then re-launch shows the red palette
- [ ] `gitchi theme` (no arg) lists themes with current marked

- [ ] **Step 3: Fix any visible issues**

Common likely fixes:
- Sparkline cell width misalignment → adjust `_SPARK_WIDTH`
- Frame border drift on narrow terminals → fall back to single-line border
- Animation feels too fast/slow → adjust `set_interval(0.5, …)` to 0.4 or 0.6
- A theme color is unreadable on some terminals → tweak the palette

- [ ] **Step 4: Run full check + commit**

```bash
uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy --strict src
git add -A
git commit -m "fix(tui): smoke-test polish"
```

(Skip the commit if nothing changed.)

---

## Task 18: Update README

**Goal:** Document the new TUI in the README ASCII demo block + the keybindings list + the `gitchi theme` command.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the README ASCII demo to match the new look**

Update the example dashboard block to reflect: 4-shade bars, sort arrows, status reason and badges line in the detail pane. Add the new keybindings to the "press" line.

- [ ] **Step 2: Add a "Theming" section**

```markdown
## Theming

Pick a retro CRT palette:

```bash
gitchi theme               # list available themes
gitchi theme virtual-boy   # switch
```

Built-in themes: `gameboy-green` (default), `gameboy-pocket`, `virtual-boy`, `cozy`.
```

- [ ] **Step 3: Run lint, then commit**

```bash
uv run ruff format --check README.md  # README is markdown, no format check — skip
git add README.md
git commit -m "docs: README updates for TUI improvements"
```

---

## Task 19: PR + reviews

**Goal:** Push the branch, open a PR, run both `/code-review` and `/security-review`, address feedback, merge.

- [ ] **Step 1: Push the branch**

```bash
cd ~/gitchi
git push -u origin feature/tui-improvements
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "feat(tui): refined two-pane TUI with themes, sparklines, animation" --body "$(cat <<'EOF'
## Summary
- Retro CRT theming (gameboy-green default, plus gameboy-pocket / virtual-boy / cozy)
- Sparklines per vital from existing history table
- Status reason + CI / TODO / age badges in the detail pane
- 2-frame idle pet animation (toggle via `a` or `[tui] animation = false`)
- Search (`/`), sort cycle (`s` / `S`), ghost/buried/news toggles (`g` / `B` / `n`)
- `gitchi theme` CLI verb

See `docs/superpowers/specs/2026-05-10-tui-improvements-design.md` and `docs/superpowers/plans/2026-05-11-tui-improvements.md`.

## Test plan
- [ ] `uv run pytest` green
- [ ] `uv run ruff check src tests` clean
- [ ] `uv run mypy --strict src` clean
- [ ] Manual smoke test: every keybinding works
- [ ] `gitchi theme` round-trips across all 4 themes
- [ ] Animation toggle survives restart

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Run /code-review**

```bash
gh pr view --json url
```

Then in this session: `/code-review` against the PR URL.

- [ ] **Step 4: Run /security-review**

`/security-review` against the PR URL.

- [ ] **Step 5: Address feedback**

For every actionable finding, write a fix, commit with `fix(...):` or `refactor(...):`, push. If feedback is wrong or out of scope, reply on the PR.

- [ ] **Step 6: Re-run both reviews** until both come back green.

- [ ] **Step 7: Merge**

```bash
gh pr merge --squash --delete-branch
git checkout main
git pull
```

---

## Self-review checklist

After completing all tasks, run through the spec sections and confirm coverage:

- [ ] Layout (Section "Layout" in spec) — Tasks 14, 15, 16
- [ ] Theming (Section "Theming" in spec) — Tasks 4, 5, 6
- [ ] Animation (Section "Animation" in spec) — Tasks 11, 12, 16
- [ ] Sparklines (Section "Sparklines" in spec) — Task 15 (reuses existing `history.sparkline`)
- [ ] Badges (Section "Badges" in spec) — Tasks 8, 9, 10, 15
- [ ] Status reason (Section "Status reason" in spec) — Task 7
- [ ] State + keybindings (Section "State, keybindings, interactions") — Tasks 3, 16
- [ ] Testing (Section "Testing") — every task that adds a pure helper writes tests

**Note on plan-vs-spec deviation:** The spec described `todo_count` and `last_play_result` as additive fields on `Pet`. The plan implements them differently — `count_todos` is a verb helper called from the detail panel, and `last_play_result` lives in its own SQL table — to keep `Pet` frozen and avoid threading new fields through refresh/store/all_pets. Observable behavior is identical.
