# gitchi — design spec

**Date:** 2026-05-10
**Status:** v0.5.0 — shipped through Wave 4

This is the historical design document that anchored the v0.1.0 build.
Subsequent waves (v0.2 dashboard depth, v0.3 PyPI publishing + rename
from `tama`, v0.4 check-pet action, v0.5 rarities) extended the design
but didn't invalidate it. For the current behavior, treat the README and
`CHANGELOG.md` as authoritative — they reflect what actually shipped.
For the historical reasoning behind the initial architecture, keep
reading.

## Concept

`gitchi` turns every git repo on a developer's machine into a virtual pet.
Pets have stats derived from real repo activity. The collection becomes a
glanceable dashboard for which projects are alive, which are dying, and
which deserve a quiet burial.

The core insight: developers accumulate dead repos but rarely confront
them. A static list won't trigger action. A pet that visibly suffers might.

## Goals

- **Honest signal:** stats must reflect repo reality, not synthetic gamification.
- **Glanceable:** state of the entire portfolio in one screen.
- **Open-source quality:** generic, configurable, no hardcoded user paths.
- **Optional enrichment:** GitHub and Claude integrations enhance the picture
  but the tool must work fully offline without them.

## Non-goals

- Replacing project-management tools (Linear, GitHub Projects).
- Tracking productivity metrics for performance review.
- Multi-user / shared-team views.

## Architecture

```
src/gitchi/
├── cli.py        # typer entrypoint, all top-level verbs
├── tui.py        # textual dashboard (read-only renderer)
├── menubar.py    # rumps menu-bar app (macOS optional extra)
├── scanner.py    # filesystem walk → list[Repo]
├── stats.py      # Repo → Vitals (hunger, health, energy, mood, age)
├── species.py    # Repo → Species
├── art.py        # (Species, Stage) → str  (ASCII art)
├── store.py      # SQLite persistence; append-only migrations
├── verbs.py      # feed / play / pet / bury / revive
├── config.py     # TOML config in platformdirs
├── github.py     # optional Energy enrichment via REST API
├── claude.py     # optional Mood enrichment via Anthropic SDK
└── cron.py       # launchd plist generator
```

### Data model

```python
@dataclass
class Repo:
    path: Path                      # absolute path
    name: str                       # path.name
    primary_language: str | None    # detected via git-attributes / file extensions
    first_commit: datetime | None
    last_commit: datetime | None
    commit_count: int
    size_bytes: int                 # repo working tree size
    has_tests: bool                 # heuristic: tests/ dir or pytest config
    has_ci: bool                    # .github/workflows/ exists

@dataclass
class Vitals:
    hunger: int   # 0–100, higher = healthier (recently fed)
    health: int   # 0–100
    energy: int   # 0–100
    mood: int     # 0–100
    age_days: int

@dataclass
class Pet:
    repo: Repo
    species: Species  # enum
    stage: Stage      # enum: egg|baby|teen|adult|elder|ghost
    vitals: Vitals
    buried: bool      # user-marked at-peace; ghosts can be buried
```

### Stat formulas

- **Hunger** = `max(0, 100 − days_since_last_commit × 100/30)` — drops linearly,
  zero by day 30, stays zero through ghost transition at day 90.
- **Health** = base 50; +20 if `has_tests`; +20 if `has_ci`; +10 if last commit
  message indicates a passing build / version bump. Capped 0–100.
- **Energy** = neutral 50 without GitHub enrichment. With token: 100 − (open
  issues older than 30 days × 5), clipped 0–100.
- **Mood** = neutral 50 without `ANTHROPIC_API_KEY`. With key: Claude reads
  last 30 commit messages, returns sentiment 0–100. Cached 7 days. Hard
  monthly token cap from config.
- **Age** = days since first commit.

### Stage rules

```
if days_since_last_commit > config.stats.ghost_after_days:
    stage = ghost
elif age_days <= 7:    stage = egg
elif age_days <= 30:   stage = baby
elif age_days <= 90:   stage = teen
elif age_days <= 365:  stage = adult
else:                  stage = elder
```

### Species detection

`primary_language` is derived from:
1. `.gitattributes` `linguist-*` overrides (if present)
2. file extension counts (excluding ignored dirs)
3. fall back to `generic_blob`

The mapping table lives in `species.py`.

## Configuration

`~/.config/gitchi/config.toml` (resolved via `platformdirs`):

```toml
[scan]
paths = ["~/"]
depth = 3
ignore = ["node_modules", ".venv", "venv", "vendor", "target", ".Trash"]

[stats]
ghost_after_days = 90
weights = { hunger = 1.0, health = 1.0, energy = 1.0, mood = 1.0 }

[claude]
enabled = false
model = "claude-haiku-4-5-20251001"
monthly_token_cap = 100_000

[github]
enabled = false
```

## Persistence

SQLite at `~/.local/share/gitchi/gitchi.db` (resolved via `platformdirs`).

Tables:
- `repos(path TEXT PK, name, primary_language, first_commit, last_commit, commit_count, size_bytes, has_tests, has_ci, last_scanned)`
- `vitals_cache(repo_path, hunger, health, energy, mood, age_days, computed_at)`
- `mood_cache(repo_path, score, sample_hash, computed_at)` — Claude responses
- `bury_state(repo_path, buried_at, reason)`
- `meta(key, value)` — schema version, monthly token usage, etc.

Migrations are SQL files in `src/gitchi/migrations/` named `NNN_<title>.sql`,
applied in order on startup.

## Verbs

| Verb     | Effect                                                         |
|----------|----------------------------------------------------------------|
| `feed`   | Open repo + print one stale TODO/FIXME found in tracked files. |
| `play`   | Detect test runner (pytest, cargo, npm, go), run it, animate.  |
| `pet`    | `$EDITOR <repo>` (defaults to `cursor`/`code`/`vim`).          |
| `bury`   | Set `buried_at`. Pet remains visible but greyed out.           |
| `revive` | Clear `buried_at`. Resets ghost state (re-evaluated next scan).|

## TUI

`textual` app with:
- Header: scan path, last scan time, total pets, ghost count
- Pet list (sortable: name | hunger | health | mood | age)
- Detail panel: full ASCII art, all vitals as bars, last-commit excerpt
- Footer: keybindings (q quit, r rescan, f feed, p play, b bury, /-search)

## Menu-bar (macOS)

`rumps`-based icon. Click reveals:
- Top 3 hungriest pets (one click → `gitchi feed <repo>`)
- Total pet count and ghost count
- "Open dashboard" → spawns `gitchi` in a new Terminal tab
- Refreshes every 15 minutes via background timer

## Cron

`gitchi cron install` writes `~/Library/LaunchAgents/com.gitchi.refresh.plist`
and `launchctl load`s it. Runs `gitchi refresh` nightly at 03:30. Logs to
`~/.local/share/gitchi/cron.log`.

## Tests

- `test_scanner.py` — fixture filesystem with nested repos and ignored dirs.
- `test_stats.py` — pure-function stat computations from `Repo` snapshots.
- `test_species.py` — language → species mapping, including precedence rules.
- `test_art.py` — every (species, stage) returns non-empty multi-line art.
- `test_store.py` — SQLite migrations idempotent, CRUD round-trip.
- `test_verbs.py` — bury/revive flow against an in-memory store.
- `test_config.py` — TOML round-trip, defaults applied.

## Out of scope

- Cross-machine sync.
- Web UI.
- Plugin system for new vital metrics.
- Linux menu-bar (contributors welcome).
