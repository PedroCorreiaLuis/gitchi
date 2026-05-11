# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.1] — 2026-05-11

### Fixed
- **Pet art centered inside the detail-panel frame.** Lines were
  left-justified, leaving the tamagotchi sprite hugging the left edge.
  Now uses `.center()` so eggs, blobs, dragons, ghosts, etc. sit in
  the middle of the `▓` frame.

## [0.6.0] — 2026-05-11

### Added
- **Retro CRT TUI theming.** Four built-in palettes — `gameboy-green`
  (default), `gameboy-pocket`, `virtual-boy`, `cozy` — selectable via the
  new `gitchi theme [name]` CLI verb or the `[tui] theme` config key.
- **Per-vital sparklines** in the detail pane. Each of hunger / health /
  energy / mood now shows its 7-day trend alongside the current value,
  sourced from the existing `vitals_history` table.
- **Status reason + badges line** in the detail pane. Below the status
  word, the panel surfaces the why ("hungry · 9d since commit",
  "thriving · daily commits") and a badge line with `todo N · ci ✓/✗ ·
  age Nd`. The CI badge reflects the most recent `gitchi play` result
  (persisted via the new `last_play_results` table).
- **2-frame idle pet animation.** Pets blink every ~0.5s. Toggle off
  with `a` (persists to config) or `[tui] animation = false`.
- **Search / sort / toggles in the TUI.**
  - `/` opens a live filter (case-insensitive substring match on repo name)
  - `s` cycles sort key (name → hunger → health → mood → age → rarity); `S` reverses
  - `g` hides/shows ghosts; `B` hides/shows buried
  - `n` collapses the news panel; `a` toggles animation
- **`gitchi theme` CLI verb.** Lists available themes when invoked
  without arguments; sets and persists when invoked with a name.

### Changed
- **`tui.py` refactored into a `tui/` package.** New `state`, `themes`,
  `animation`, `status_reason` modules plus a `widgets/` subpackage
  (`detail_panel`, `news_panel`, `pet_table`, `search_input`). Public
  imports (`from gitchi.tui import run`) remain stable.
- **`count_todos` bounded.** Caps file count (`max_files=500`), hit
  count (`cap=500`), and per-file lines (`max_lines_per_file=2000`) so
  large checked-in files don't stall the detail pane.
- **DetailPanel caches TODO counts.** Row-highlight navigation no longer
  re-scans the filesystem on every cursor move; the cache invalidates
  on rescan.

### Fixed
- **Hidden `Input` overlay stealing focus on TUI mount.** The new
  `SearchInput` is the first composed widget; Textual auto-focuses the
  first focusable widget regardless of `display: none`, so every
  keystroke was being consumed by the hidden input. Now `PetTable` is
  explicitly focused after mount.

### Internal
- Headless Textual `Pilot` smoke tests covering mount, sort cycle,
  ghost toggle, animation toggle, search filter, and quit.
- `pytest-asyncio` added to the `dev` extra with `asyncio_mode = "auto"`.
- New SQL migration `004_play_results.sql` adds `last_play_results
  (repo_path PK, returncode, ran_at)` for persisting `gitchi play`
  outcomes.

## [0.5.0] — 2026-05-10

### Added
- **Pet rarities.** Every pet rolls a tier — common (50%), uncommon (25%),
  rare (15%), epic (7%), mythic (2.5%), or legendary (0.5%) — that's
  deterministic per repo. The roll uses a stable hash of the repo path
  and first-commit timestamp, so the same repo always gets the same tier
  across scans; the distribution across a sufficiently large repo zoo
  matches the named percentages within sampling noise.
  - Surfaced in `gitchi list` (new column, colour-coded), `gitchi show`
    (rarity line + name-bar suffix), and the TUI (new column +
    detail-panel line).
  - Migration 003 adds a `rarity` column to `vitals_cache` and
    `vitals_history`; both default to `common` for pre-existing rows on
    upgrade (and get overwritten on the next refresh).
  - Distribution test (`test_rarity`) verifies the percentages match
    target tolerance over 20 000 synthetic repos.

## [0.4.0] — 2026-05-10

### Added
- **GitHub Action: `check-pet`.** A composite action at
  `.github/actions/check-pet/` that other repositories can call from
  their `pull_request` workflows. It installs gitchi from PyPI, computes
  the target repo's current pet vitals, and posts a sticky comment on
  the PR if hunger or health falls below configurable thresholds. The
  comment updates in place on subsequent pushes instead of stacking new
  ones (HTML-marker sticky-comment pattern). Inputs:
  `hunger-threshold` (default 30), `health-threshold` (default 50),
  `comment-marker`, `github-token`. The calling job needs
  `pull-requests: write`. See `.github/actions/check-pet/README.md` for
  the full usage walkthrough.

## [0.3.0] — 2026-05-10

### Changed
- **Renamed from `tama` to `gitchi`.** The PyPI name `tama` was already
  claimed, so the entire project — package, import, CLI binary, config
  directory, launchd plist label, all docs and references — moves to
  `gitchi`. Existing users on `tama` will need to re-run `gitchi refresh`
  to rebuild their dashboard (the old `tama` config / data directories
  are not migrated automatically).
- **Release workflow now publishes the `gitchi` package on PyPI** via
  trusted publishing — first publish goes out with v0.3.0.

## [0.2.0] — 2026-05-10

### Added
- **News log.** Each `gitchi refresh` diffs the post-scan state against a
  snapshot taken before the scan and emits typed events: `hatched`,
  `evolved`, `became_ghost`, `revived`, `became_hungry`, and
  `recovered_from_hunger`. Surfaced in the refresh output, via a new
  `gitchi news` command, and in a side panel in the TUI.
- **Local Energy proxy.** Energy used to be a hardcoded 50 when GitHub
  enrichment was off. Now derived from local signals: uncommitted files,
  stale local branches, untracked top-level directories. GitHub
  enrichment still takes priority when enabled.
- **`gitchi ignore` / `gitchi unignore`.** Hide pets that shouldn't be
  tracked (vendored forks, inherited clones). Distinct from `bury`.
  Ignored pets are also filtered out of the news feed. `gitchi list --all`
  re-includes them.
- **Smarter `gitchi feed`.** Opens `$EDITOR` directly at the TODO line.
  Recognises VS Code / Cursor / Sublime / Vim / Emacs goto conventions.
  `--no-open` keeps the print-only behavior for scripted callers.
- **Time-series history + sparklines.** New `vitals_history` table; each
  refresh appends one row per pet. `gitchi show <repo>` renders a Unicode
  sparkline per vital across the last 20 scans.
- **Stage transitions in the news log** with a ✨ icon and clear
  before-→-after message.

### Fixed
- TUI `f` keybind no longer silently auto-opens `$EDITOR` (which would
  also silently swallow rc=127 when no editor was configured). Press
  `f` to surface the TODO; press `e` to jump there.
- News events now read back in their documented priority order within a
  single refresh batch (stage transitions before hunger crossings).
  The previous query tiebroke on `id DESC`, inverting the insertion
  order.

## [0.1.1] — 2026-05-10

### Fixed
- Pet evolution stages were stuck at `egg` for nearly every repo because
  `_git_first_commit_time` invoked `git log --reverse --max-count=1`,
  which is a footgun: git applies `--max-count` *before* reversing the
  output, so it returned the most recent commit instead of the first.
  Replaced with `git log --max-parents=0 --format=%ct HEAD` to find the
  root commit directly. Includes a 60-day backdated regression test.

## [0.1.0] — 2026-05-10

### Fixed
- `store.connect()` is now a context manager that actually closes the SQLite
  connection on exit. Previously `with connect(...)` leaked the underlying
  file descriptor on every CLI invocation, TUI rescan, and menu-bar tick.
- `gitchi pet` now shell-tokenises `$EDITOR` via `shlex.split`, so values like
  `EDITOR="code --wait"` or `EDITOR="emacsclient -t"` work as expected
  instead of crashing with `FileNotFoundError`.
- The menu-bar "Open dashboard" action launches the TUI for real.
  `open -a Terminal gitchi` was treating "gitchi" as a file path; we now drive
  Terminal.app via `osascript` and invoke `sys.executable -m gitchi` so the
  new shell uses the same Python as the menu-bar process.

### Added
- Repo scanner (`scanner.py`) with configurable depth and ignore globs
- Five vital stats: Hunger, Health, Energy, Mood, Age
- Species mapping for Rust, Python, TypeScript/JavaScript, Go, Swift, Ruby,
  GDScript, Markdown-only repos, and a generic fallback
- Evolution stages: egg → baby → teen → adult → elder, with ghost as an
  override for abandoned repos
- ASCII pixel-art renderer per species × stage
- SQLite persistence with append-only migrations
- TUI dashboard built on `textual`
- macOS menu-bar app via `rumps` (optional extra)
- launchd plist generator for nightly auto-refresh
- Optional GitHub enrichment for Energy
- Optional Claude-powered Mood sentiment with prompt caching and a hard
  monthly token cap
- Verbs: `feed`, `play`, `pet`, `bury`, `revive`
- Config file at `~/.config/gitchi/config.toml` via `platformdirs`
