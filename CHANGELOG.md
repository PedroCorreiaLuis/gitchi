# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
