# Contributing to gitchi

Thanks for considering a contribution. gitchi is small, so the bar for getting
something merged is low: it should be tested, it should pass `ruff` and
`mypy`, and it should not break the TUI.

## Setup

```bash
git clone https://github.com/PedroCorreiaLuis/gitchi
cd gitchi
uv sync --extra menubar --extra dev   # creates .venv and installs locked deps
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

1. `src/gitchi/species.py` — add a `(language, Species)` mapping.
2. `src/gitchi/art.py` — add ASCII art for each evolution stage:
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

Releases are automated. Pushing a tag of the form `v<X>.<Y>.<Z>` triggers
`.github/workflows/release.yml` which:

1. Verifies the tag matches the version in `pyproject.toml`.
2. Builds the wheel + sdist with `uv build`.
3. Publishes to PyPI via [trusted publishing][trusted-pub] — no API token
   needed; PyPI verifies the workflow's OIDC token instead.

To cut a release:

```bash
# bump the version in pyproject.toml + src/gitchi/__init__.py + CHANGELOG.md
# (we keep them in sync as a deliberate three-place edit so each can be
# audited independently in PR review)

git checkout -b chore/v<X>.<Y>.<Z>
# ...edit, run tests...
git push -u origin chore/v<X>.<Y>.<Z>
gh pr create --fill
gh pr merge --squash --delete-branch
git pull
git tag -a v<X>.<Y>.<Z> -m "v<X>.<Y>.<Z>"
git push origin v<X>.<Y>.<Z>
gh release create v<X>.<Y>.<Z> --generate-notes  # or write notes manually
```

The PyPI workflow runs automatically once the tag is pushed; the release
URL appears in the workflow's deployment summary when it completes.

### One-time PyPI setup (only needed before the first publish)

Trusted publishing requires a one-time configuration on pypi.org:

1. Log in to pypi.org → "Your projects" → "Manage" or "Publishing".
2. Add a **pending publisher** (works even before the project exists):
   - Project: `gitchi`
   - Owner: `PedroCorreiaLuis`
   - Repo: `gitchi`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. First tag push runs the workflow, claims the project name, and uploads
   the artifact in one shot.

[trusted-pub]: https://docs.pypi.org/trusted-publishers/
