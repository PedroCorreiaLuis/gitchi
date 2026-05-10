# Contributing to tama

Thanks for considering a contribution. tama is small, so the bar for getting
something merged is low: it should be tested, it should pass `ruff` and
`mypy`, and it should not break the TUI.

## Setup

```bash
git clone https://github.com/PedroCorreiaLuis/tama
cd tama
uv venv
uv pip install -e ".[menubar,dev]"
```

## Run tests

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

## Add a species

Species are the easiest contribution path. Edit two files:

1. `src/tama/species.py` — add a `(language, Species)` mapping.
2. `src/tama/art.py` — add ASCII art for each evolution stage:
   `egg`, `baby`, `teen`, `adult`, `elder`, `ghost`.

Open a PR with one new test in `tests/test_species.py` proving the language
maps correctly.

## Architecture notes

- Stat computation is pure: given a `Repo` snapshot, produce numeric stats.
  No side effects. This keeps it testable.
- Persistence is in SQLite. Migrations are append-only.
- The TUI is a thin renderer over `store.py` reads. Don't put logic in `tui.py`.
- Optional services (GitHub, Claude) must degrade gracefully when env vars
  are absent — never raise, always return `None` and let downstream merge.

## Releases

We follow semver. The `v0.x` line may break TUI keybindings or stat formulas
without a major bump.
