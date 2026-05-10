# gitchi TUI improvements — design

Date: 2026-05-10
Status: approved, pending implementation plan

## Goal

Improve the gitchi TUI on two axes: **visual polish/feel** and **information density/layout**. The current TUI works but reads as a default Textual app — neutral chrome, plain DataTable, small static ASCII art, no theme identity. The redesign keeps the existing two-pane shape (it scans well and respects the terminal), but tightens the layout, adds a retro 4-color identity, surfaces more useful data per pet, and gives the pet art real estate to breathe and animate.

Scope is the TUI only. CLI verbs, refresh logic, scanner, store, and species/rarity systems are untouched except for additive surfaces (new `gitchi theme` verb, new config keys, optional cached fields).

## Decisions

| Axis | Decision |
|---|---|
| Layout | Refined two-pane (sortable headers, sparklines, color-coded vitals, collapsible news) |
| Aesthetic | Retro CRT / 4-color, gameboy-flavored, theme-pickable |
| Themes | 4 built-in: `gameboy-green` (default), `gameboy-pocket`, `virtual-boy`, `cozy` |
| Pet art | Bigger (~16×7 inside a frame) + 2-frame idle animation, state-aware variants (alert, ghost, celebrate) |
| Sparklines | 7-day per vital, Unicode `▁▂▃▄▅▆▇█`, sourced from existing `history` module |
| Badges | `todo N · ci ✓/✗/— · age 42d` in detail pane |
| Status reason | One-line "why" derived from same signals as `status_word` |
| Search | `/` opens live filter, Esc cancels |
| Sort | `s` cycles `name → hunger → health → mood → age → rarity`, Shift+S reverses |
| Toggles | `g` ghost visibility, `B` buried visibility, `n` news panel, `a` animation |
| Persistence | Theme + animation_enabled persist via `config.toml`; sort/filter/toggles per-session |

## File layout

The current `src/gitchi/tui.py` (249 lines) becomes a package. Splitting now because the additions push it past 600 lines, and several pieces are pure functions that deserve their own unit tests.

```
src/gitchi/tui/
  __init__.py          # exports run()
  app.py               # GitchiApp: composition, bindings, top-level state
  state.py             # AppState dataclass
  themes.py            # Theme dataclass, registry, CSS generator
  sparkline.py         # render_sparkline(samples, width) -> str   (pure)
  animation.py         # FrameClock, FrameSet, select_frames(pet)
  status_reason.py     # derive_reason(pet) -> str                 (pure)
  widgets/
    __init__.py
    pet_table.py       # DataTable subclass; applies sort + filter + toggles
    detail_panel.py    # Big art + animated frame + sparklines + badges
    news_panel.py      # (moved unchanged)
    search_input.py    # Overlay Input wired to AppState.filter_text
```

Pure modules (`sparkline`, `status_reason`, `themes` registry/CSS, sort/filter helpers in `state`) get unit tests. Widget classes stay thin.

## Layout

```
╭──── gitchi · 14 alive · 3 ghosts · 1 buried ─────────────╮
│  /search: rast_                                          │  ← only when / active
├──────────────────────────────────────────────────────────┤
│ NAME       SPECIES  STAGE  HUNGER▾  MOOD   STATUS       │ │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
│ ▸rasteira  🐍 snake adult  ███░░░   ████   hungry       │ │  ▓                ▓
│  gitchi    🟢 blob  baby   █████░   █████  thriving     │ │  ▓   ╱◕  ◡  ◕╲   ▓
│  coldpipe  🐍 snake teen   ████░░   ███░░  content      │ │  ▓  (   blob   )  ▓
│  flight    👻ghost  ghost  ░░░░░░   ░░░░░  buried       │ │  ▓   ╲  ───  ╱   ▓
│  uw-cop    🐉dragon teen   ██████   ██████ happy        │ │  ▓                ▓
│                                                         │ │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
├─ news ──────────────────────────────────────────────────┤ │  gitchi · 🟢 baby blob
│ • rasteira got hungry (2h)                              │ │  rarity ✦ uncommon
│ • gitchi leveled up baby→teen (1d)                      │ │
╰─────────────────────────────────────────────────────────╯ │  hunger ▁▂▃▅▇▆▅  ██████░░ 72
                                                            │  health ▆▆▅▅▄▃▂  █████░░░ 60
                                                            │  mood   ▃▄▅▆▇▇▇  ███████░ 88
                                                            │  energy ▅▅▆▆▆▆▆  ██████░░ 75
                                                            │
                                                            │  thriving · daily commits, tests pass
                                                            │  todo 14 · ci ✓ · age 42d
 q quit · r rescan · / search · s sort · g ghosts · ? help
```

Behaviors:
- **Header**: dynamic counts; reflects current filter (e.g., "8 of 14 alive · 1 hidden")
- **Search bar**: hidden until `/`; live-filters table; Esc closes and clears
- **Column headers**: `▾`/`▴` arrow on active sort key; `s` cycles
- **Detail pane**: bigger art inside a 4-shade frame; sparkline + bar + numeric value per vital; status reason line; badge line
- **News panel**: collapsible with `n`; shows newest 3 by default (currently 6, but the detail pane needs the vertical space)
- **Footer**: tightened keymap, key letters highlighted in accent color

## Theming

`themes.py` defines a `Theme` dataclass and a registry of 4 built-in themes.

```python
@dataclass(frozen=True)
class Theme:
    name: str
    bg: str         # darkest
    fg: str         # lightest
    dim: str        # mid-low
    accent: str     # highlight / selected
    alert: str      # alert state (hungry, dying, ghost)
    ok: str         # thriving state

THEMES: dict[str, Theme] = {
    "gameboy-green":  Theme("gameboy-green",  "#0f380f", "#8bac0f", "#306230", "#9bbc0f", "#9bbc0f", "#8bac0f"),
    "gameboy-pocket": Theme("gameboy-pocket", "#0f0f0f", "#c0c0c0", "#606060", "#ffffff", "#ff8080", "#80ff80"),
    "virtual-boy":    Theme("virtual-boy",    "#1a0000", "#ff2a2a", "#660000", "#ff6666", "#ff9999", "#ff4444"),
    "cozy":           Theme("cozy",           "#2a1f1a", "#d4b896", "#6b4f3a", "#e7a3a3", "#e7a3a3", "#7fb8a8"),
}

def render_css(theme: Theme) -> str: ...
```

`render_css` substitutes palette tokens into a Textual CSS template. Applied at app startup; theme switching mid-session is out of scope (config edit + restart is fine).

**Bar rendering**: 4-shade ramp `█▓▒░` mapped onto `(fg, fg-dim, dim, bg)`. Sparklines use 8-shade Unicode but quantize color to 4 theme shades. Selected row inverts to accent. Ghost rows render at 50% opacity via Textual `text-style: dim`. Alert states (hunger < 25, health < 25) tint the status word and bar in `alert`.

**Config**:

```toml
[tui]
theme = "gameboy-green"
animation = true
```

**CLI verb**: `gitchi theme <name>` validates against `THEMES`, writes config, prints confirmation. `gitchi theme` with no argument prints current theme and lists available themes.

## Animation

`animation.py` runs a single `set_interval(0.5)` tick on the app. Only the visible pet (in `DetailPanel`) animates; the table never animates.

```python
@dataclass
class FrameSet:
    idle: list[str]              # 2 frames, cycled every 1s
    alert: list[str] | None      # used when hungry < 25 or health < 25
    ghost: list[str] | None      # flicker frames for ghost stage
    celebrate: list[str] | None  # sparkle frames for thriving + recent commit (<24h)

def select_frames(pet: Pet) -> FrameSet:
    # priority: ghost > alert > celebrate > idle
```

Frames live in `art.py` alongside existing renders. Each `(species, stage)` already has one art string; we extend the table to a tuple per state. Missing frames fall back to the existing static art (backwards-compatible).

**Cost control**:
- Tick fires only when the app has focus (Textual default)
- Frame strings are pre-rendered; tick only assigns + repaints one widget
- Toggle off via `a` keybind or `[tui] animation = false` for slow terminals / Mosh

Frames are 2-state, not full loops. Multi-frame loops are explicitly out of scope.

## Sparklines

`sparkline.py` (pure):

```python
def render_sparkline(samples: list[int], width: int = 7) -> str:
    """
    Render 0-100 samples as a Unicode sparkline using ▁▂▃▄▅▆▇█.
    Samples are oldest-first; short series left-pads with " ";
    empty series returns " " * width.
    """
```

Source: existing `history` module, which already tracks per-vital daily snapshots. `DetailPanel` calls `history.last_n(pet.repo.path, vital, n=7)` for each vital. No DB schema change.

## Badges

`todo N · ci ✓ · age 42d` rendered in `DetailPanel` below the status reason line.

- `todo N` — from `verbs_mod.scan_todos(repo.path)`. Hidden when N = 0. Cached per refresh (not per render) — add `todo_count: int` field to `Pet` populated during `refresh`.
- `ci ✓ / ✗ / —` — from last `verbs_mod.play` result if available; `—` when no runner detected or no run recorded. Add `last_play_result: int | None` field to `Pet`, persisted via store.
- `age 42d` — moved from the vitals block to the badges line.

Both new `Pet` fields are additive; existing migrations handle the schema bump.

## Status reason

`status_reason.py` (pure):

```python
def derive_reason(pet: Pet) -> str:
    """
    Surface the signal that drove `pet.status_word`. Mirrors the same
    threshold logic. Examples:
      "hungry: 9d since commit"
      "thriving: daily commits, tests pass"
      "buried: at peace"
      "ghost: 60+ days dormant"
    """
```

This parallels (and stays in sync with) the logic that computes `status_word`. Co-located in its own pure module so it's testable in isolation. If `status_word` lives in `models.py` today, the two functions can share a private helper for threshold lookups.

## State, keybindings, interactions

**AppState** (in `state.py`):

```python
@dataclass
class AppState:
    sort_key: Literal["name","hunger","health","mood","age","rarity"] = "name"
    sort_desc: bool = False
    filter_text: str = ""
    show_ghosts: bool = True
    show_buried: bool = True
    animation_enabled: bool = True   # mirror of config
    news_collapsed: bool = False
```

Persistence rules:
- **`theme`** — persists via `config.toml` (not in `AppState`; loaded at startup, set via `gitchi theme <name>` verb).
- **`animation_enabled`** — persists via `config.toml`. The `a` keybind toggles the in-session `AppState.animation_enabled` AND writes the new value back to `config.toml` so it survives restart.
- **Everything else in `AppState`** (sort, filter, toggles) — per-session only. A restart returns to defaults.

Filter semantics: case-insensitive substring match on `pet.repo.name` only. Empty filter shows all rows (subject to ghost/buried toggles).

**Final keybindings**:

| key | action |
|---|---|
| `q` | quit |
| `r` | rescan |
| `f` | feed |
| `p` | play |
| `e` | edit |
| `b` | bury |
| `v` | revive |
| `i` | ignore |
| `u` | unignore |
| `/` | search (live filter; Esc cancels) |
| `s` | sort cycle (Shift+S reverses direction) |
| `g` | toggle ghosts visibility |
| `B` | toggle buried visibility |
| `n` | toggle news panel |
| `a` | toggle animation (also persists to config) |
| `?` | show built-in Textual help (lists all bindings) |

## Testing

New pure-function tests:
- `test_sparkline.py` — empty, partial, full, all-zero, all-max, monotone increasing/decreasing
- `test_status_reason.py` — each status word maps to a reasonable reason; thresholds match `status_word`
- `test_themes.py` — `render_css` produces output for every registered theme; no missing tokens; registry lookup; CLI verb roundtrip (write → read → assert)
- `test_state.py` — sort cycle order, sort direction toggle, filter substring matching, ghost/buried toggle semantics

Existing 86 tests stay green. Don't add Textual widget tests — fragile, low value.

## Out of scope

- Multi-frame animation loops (asked, not chosen)
- Last-commit recency column (asked, not chosen — kept as `age` badge)
- Custom `?` help modal — use Textual's built-in help binding for the same result
- Theme switching mid-session — config + restart is enough
- New scanner/refresh logic — additive `Pet` fields only

## Risks & mitigations

- **Risk**: Animation tick adds CPU on slow terminals / Mosh sessions.
  **Mitigation**: `a` toggle + `[tui] animation = false` config. 0.5s tick × one widget repaint is negligible on local terms.
- **Risk**: `Pet` schema additions (`todo_count`, `last_play_result`) require store migration.
  **Mitigation**: gitchi already uses numbered migrations under `src/gitchi/migrations/`. Add the next migration with default values; existing rows get sensible defaults.
- **Risk**: Splitting `tui.py` into a package breaks any external import of `gitchi.tui.run`.
  **Mitigation**: `tui/__init__.py` re-exports `run`, so `from gitchi.tui import run` continues to work. Verified `__main__.py` and `menubar.py` import paths.
- **Risk**: 4-color themes look broken on terminals without 24-bit color.
  **Mitigation**: Textual already degrades to 256-color. Pick palettes that quantize sanely (verified by eye on the gameboy-green choice).
