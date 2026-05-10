# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-10

### Fixed
- `store.connect()` is now a context manager that actually closes the SQLite
  connection on exit. Previously `with connect(...)` leaked the underlying
  file descriptor on every CLI invocation, TUI rescan, and menu-bar tick.
- `tama pet` now shell-tokenises `$EDITOR` via `shlex.split`, so values like
  `EDITOR="code --wait"` or `EDITOR="emacsclient -t"` work as expected
  instead of crashing with `FileNotFoundError`.
- The menu-bar "Open dashboard" action launches the TUI for real.
  `open -a Terminal tama` was treating "tama" as a file path; we now drive
  Terminal.app via `osascript` and invoke `sys.executable -m tama` so the
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
- Config file at `~/.config/tama/config.toml` via `platformdirs`
