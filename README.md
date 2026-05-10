# tama

> A virtual pet for every git repo. Your codebase as a tamagotchi.

`tama` scans your filesystem, finds every git repository, and spawns a virtual
pet for each one. The pet's health, mood, and species are derived from the
repo itself — language, commit cadence, open issues, age. Pets get hungry when
you don't commit, sick when CI breaks, and turn into ghosts when abandoned.

It's a glanceable, slightly absurd, and surprisingly honest dashboard for the
state of every project you've ever started.

```
╭───────────────────────── tama ─────────────────────────╮
│                                                        │
│   ◉ rasteira       🐍 baby snake     hungry  ░░░░░░░  │
│   ◉ tama           🟢 baby blob      thriving █████░  │
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
pipx install tama

# or with uv's pipx-equivalent
uv tool install tama

# or classic pip
pip install tama

# from source (for development)
git clone https://github.com/PedroCorreiaLuis/tama
cd tama
uv sync --extra menubar --extra dev   # `menubar` is macOS-only; drop it on Linux
```

## Quick start

```bash
# scan and view
tama                          # opens the TUI dashboard

# inspect a single pet
tama show <repo>

# interact
tama feed <repo>              # nudges you to commit (suggests a stale TODO)
tama play <repo>              # runs the test suite
tama pet <repo>               # opens the repo in $EDITOR
tama bury <repo>              # marks an abandoned repo at peace
tama revive <repo>            # un-buries a ghost

# config
tama config show
tama config set scan.paths ~/code,~/projects
tama config set scan.depth 4

# bring optional services online
export GITHUB_TOKEN=ghp_...           # enriches Energy with real issue/PR data
export ANTHROPIC_API_KEY=sk-ant-...   # enriches Mood from commit-message tone

# automation (macOS)
tama cron install             # writes a launchd plist that refreshes nightly
tama menubar install          # registers the menu-bar app at login
```

## Stats

Every pet has five vital signs. Each is a 0–100 score; higher is healthier.

| Stat       | Source                                                        |
|------------|---------------------------------------------------------------|
| **Hunger** | Days since last commit. >90 days = starving = ghost.          |
| **Health** | Test discovery + last test run result + dependency staleness. |
| **Energy** | Open issue/PR rot from GitHub (optional). Stale = drained.    |
| **Mood**   | Sentiment of last 30 commit messages via Claude (optional).   |
| **Age**    | Days since first commit. Drives evolution stage.              |

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

## Architecture

```
src/tama/
├── cli.py        # typer entrypoint
├── tui.py        # textual dashboard
├── menubar.py    # rumps menu-bar (macOS)
├── scanner.py    # find .git repos
├── stats.py      # compute the five vitals
├── species.py    # repo → species mapping
├── art.py        # ASCII pixel-art per species × stage
├── store.py      # SQLite persistence (~/.local/share/tama/)
├── verbs.py      # feed / play / pet / bury / revive
├── config.py     # ~/.config/tama/config.toml
├── github.py     # optional GitHub enrichment
├── claude.py     # optional commit-mood sentiment
└── cron.py       # launchd plist generator
```

## Configuration

Config lives at `~/.config/tama/config.toml` (`platformdirs` resolves the
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). New species are especially welcome —
they're a few lines of art plus a language mapping.

## License

[MIT](LICENSE)
