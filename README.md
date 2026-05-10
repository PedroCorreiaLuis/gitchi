# gitchi

> A virtual pet for every git repo. Your codebase as a tamagotchi.

`gitchi` scans your filesystem, finds every git repository, and spawns a virtual
pet for each one. The pet's health, mood, and species are derived from the
repo itself — language, commit cadence, open issues, age. Pets get hungry when
you don't commit, sick when CI breaks, and turn into ghosts when abandoned.

It's a glanceable, slightly absurd, and surprisingly honest dashboard for the
state of every project you've ever started.

```
╭───────────────────────── gitchi ─────────────────────────╮
│                                                        │
│   ◉ rasteira       🐍 baby snake     hungry  ░░░░░░░  │
│   ◉ gitchi           🟢 baby blob      thriving █████░  │
│   ◉ coldpipe       🐍 adult snake    content  ████░░  │
│   ◉ flight-project 👻 ghost          buried   ░░░░░░  │
│   ◉ uw-copilot     🐉 teen dragon    happy    ██████  │
│                                                        │
│  press ↑↓ to select · enter for details · q to quit   │
╰────────────────────────────────────────────────────────╯
```

## Why

Most developers have a graveyard of half-started repos. You don't know which
ones are alive, which are dying, and which deserve a funeral. A static list
won't tell you. A linter won't tell you. Your inbox certainly won't tell you.

A pet that visibly suffers when you ignore it might.

## Install

```bash
# recommended: isolated install via pipx
pipx install gitchi

# or with uv's pipx-equivalent
uv tool install gitchi

# or classic pip
pip install gitchi

# from source (for development)
git clone https://github.com/PedroCorreiaLuis/gitchi
cd gitchi
uv sync --extra menubar --extra dev   # `menubar` is macOS-only; drop it on Linux
```

## Quick start

```bash
# the typical flow
gitchi refresh                 # scan all configured paths, recompute every pet
gitchi                         # opens the TUI dashboard (also the default action)
gitchi list                    # text table of all pets
gitchi list --sort age         # sort by hunger | health | mood | age | name
gitchi list --all              # include pets you've `gitchi ignore`d
gitchi show <repo>             # full detail view with ASCII art + sparklines
gitchi news                    # what changed since last refresh (evolutions, ghosts, …)

# interactions
gitchi feed <repo>             # find a stale TODO/FIXME and jump $EDITOR to it
gitchi feed <repo> --no-open   # …or just print it without opening the editor
gitchi play <repo>             # detect the test runner (pytest/cargo/npm/…) and run it
gitchi pet <repo>              # open the repo in $EDITOR
gitchi bury <repo>             # mark an abandoned repo at peace (greyed out)
gitchi revive <repo>           # un-bury a ghost
gitchi ignore <repo>           # hide a repo entirely (vendored fork, inherited clone…)
gitchi unignore <repo>         # bring it back

# config
gitchi config show
gitchi config set scan.paths ~/code,~/projects
gitchi config set scan.depth 4
gitchi config set github.enabled true       # opt in to GitHub-API Energy enrichment
gitchi config set claude.enabled true       # opt in to Claude-scored Mood (needs token cap)

# bring optional services online
export GITHUB_TOKEN=ghp_...           # enriches Energy with real issue/PR data
export ANTHROPIC_API_KEY=sk-ant-...   # enriches Mood from commit-message tone

# automation (macOS)
gitchi cron install             # writes a launchd plist that refreshes nightly
gitchi cron uninstall           # remove the launchd job
gitchi menubar run              # run the rumps menu-bar app in the foreground
```

## Stats

Every pet has five vital signs. Each is a 0–100 score; higher is healthier.

| Stat       | Source                                                        |
|------------|---------------------------------------------------------------|
| **Hunger** | Days since last commit. >90 days = starving = ghost.                                            |
| **Health** | Test discovery + last test run result + dependency staleness.                                   |
| **Energy** | Local default: uncommitted files + stale local branches + untracked dirs. Optional: GitHub issue rot. |
| **Mood**   | Neutral 50 by default. Optional: Claude scores the last 30 commit messages.                     |
| **Age**    | Days since first commit. Drives evolution stage.                                                |

## Species

Pet species is derived from the repo's primary language. Body size scales
with repo size; accessories appear with milestones (releases, stars, big
commit counts).

| Language        | Species       |
|-----------------|---------------|
| Rust            | dragon 🐉     |
| Python          | snake 🐍      |
| TypeScript / JS | blob 🟢       |
| Go              | gopher 🦫     |
| Swift           | falcon 🦅     |
| Ruby            | gem 💎        |
| GDScript        | ghost-cat 👻🐈|
| Markdown-only   | scroll 📜     |
| _other / mixed_ | generic blob  |

## Evolution

| Stage  | Trigger                              |
|--------|--------------------------------------|
| egg    | repo age 0–7 days                    |
| baby   | 8–30 days                            |
| teen   | 31–90 days                           |
| adult  | 91–365 days                          |
| elder  | 365+ days                            |
| ghost  | 90+ days with no commits (overrides) |

A `git tag` or GitHub release accelerates the next evolution.

## Rarity

Every pet also rolls a rarity tier — common, uncommon, rare, epic, mythic,
or legendary. The roll is **deterministic per repo**: the same repository
always rolls the same tier across scans (the seed is a hash of the repo's
absolute path and first-commit timestamp). Across a large enough zoo the
distribution matches these percentages:

| Tier       |   %   | Color   |
|------------|-------|---------|
| common     | 50.0% | dim     |
| uncommon   | 25.0% | green   |
| rare       | 15.0% | blue    |
| epic       |  7.0% | magenta |
| mythic     |  2.5% | red     |
| legendary  |  0.5% | yellow  |

Rarity is just visual flair — it doesn't affect any other stat or
mechanic. If a repo is on a different path on a different machine it'll
roll a different tier (rarity is per-checkout, not per-repo-content).

## Architecture

```
src/gitchi/
├── cli.py          # typer entrypoint
├── tui.py          # textual dashboard
├── menubar.py      # rumps menu-bar (macOS)
├── scanner.py      # find .git repos
├── stats.py        # compute the five vitals
├── species.py      # repo → species mapping
├── rarity.py       # deterministic gacha-style rarity tier
├── art.py          # ASCII pixel-art per species × stage
├── store.py        # SQLite persistence (~/.local/share/gitchi/)
├── verbs.py        # feed / play / pet / bury / revive / ignore
├── refresh.py      # scan → enrich → diff → emit news
├── news.py         # stage / hunger transitions between scans
├── history.py      # vitals_history sparkline rendering
├── local_energy.py # default Energy proxy (no GitHub needed)
├── config.py       # ~/.config/gitchi/config.toml
├── github.py       # optional GitHub enrichment
├── claude.py       # optional commit-mood sentiment
└── cron.py         # launchd plist generator
```

## Configuration

Config lives at `~/.config/gitchi/config.toml` (`platformdirs` resolves the
right path on each OS).

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

## GitHub Action — warn on PRs against unhealthy pets

If you want gitchi to comment on PRs in your other repos whenever the
target repo's pet is starving or fragile, drop this into the target repo's
`.github/workflows/pet-check.yml`:

```yaml
name: pet check
on:
  pull_request:
    branches: [main]

jobs:
  pet-check:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - uses: PedroCorreiaLuis/gitchi/.github/actions/check-pet@v0.5.0
        with:
          hunger-threshold: 30
          health-threshold: 50
```

Full action docs: [`.github/actions/check-pet/README.md`](.github/actions/check-pet/README.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). New species are especially welcome —
they're a few lines of art plus a language mapping.

## License

[MIT](LICENSE)
