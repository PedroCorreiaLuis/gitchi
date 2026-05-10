# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-10

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
