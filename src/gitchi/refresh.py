"""Top-level orchestration: scan → enrich → persist → diff → emit news.

The refresh pipeline does four things in order:

1.  Scan the configured roots for git repos and build a fresh `Repo` snapshot
    of each one.
2.  Optionally enrich Energy via the GitHub API and Mood via Claude. If
    GitHub enrichment isn't on we fall back to a local-only Energy proxy
    so the stat reflects real signal (uncommitted drift, stale branches)
    rather than a hardcoded 50.
3.  Persist the current Vitals into both `vitals_cache` (the always-latest
    cache the TUI reads) and `vitals_history` (an append-only time series
    that powers sparklines).
4.  Diff the post-scan state against the pre-scan snapshot and append the
    resulting `NewsEvent`s — these are what `gitchi news` and the dashboard's
    side panel surface to the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import claude as claude_mod
from . import config as config_mod
from . import github as github_mod
from . import local_energy as local_energy_mod
from . import news as news_mod
from . import rarity as rarity_mod
from . import species as species_mod
from . import stats as stats_mod
from .models import Config, NewsEvent, Pet, Stage, VitalsSnapshot
from .scanner import find_repos
from .store import (
    all_pets,
    append_news_events,
    append_vitals_history,
    connect,
    currently_ignored_paths,
    recent_news,
    repo_name_map,
    snapshot_current_vitals,
    upsert_repo,
    upsert_vitals,
)


@dataclass(frozen=True, slots=True)
class RefreshSummary:
    scanned: int
    persisted: int
    ghosts: int
    enriched_with_github: int
    enriched_with_claude: int
    enriched_with_local_energy: int
    news_events: list[NewsEvent]


def refresh(cfg: Config | None = None) -> RefreshSummary:
    cfg = cfg or config_mod.load()
    roots = [Path(p).expanduser() for p in cfg.scan.paths]
    repos = find_repos(roots, cfg.scan)

    gh_count = 0
    cl_count = 0
    local_energy_count = 0
    ghosts = 0
    after: dict[str, VitalsSnapshot] = {}

    with connect() as conn:
        before = snapshot_current_vitals(conn)

        for repo in repos:
            upsert_repo(conn, repo)

            energy: int | None = None
            if cfg.github.enabled:
                energy = github_mod.energy_score(repo.path)
                if energy is not None:
                    gh_count += 1

            if energy is None:
                energy = local_energy_mod.score_for(repo.path)
                if energy is not None:
                    local_energy_count += 1

            mood = claude_mod.mood_score(repo.path, cfg.claude) if cfg.claude.enabled else None
            if mood is not None:
                cl_count += 1

            vitals = stats_mod.compute(
                repo,
                cfg.stats,
                energy_override=energy,
                mood_override=mood,
            )
            stage = stats_mod.stage_for(repo, cfg.stats)
            species = species_mod.species_for(repo)

            if stage is Stage.GHOST:
                ghosts += 1

            rarity = rarity_mod.rarity_for(repo)

            upsert_vitals(conn, repo.path, vitals, stage, species, rarity)
            append_vitals_history(conn, repo.path, vitals, stage, species, rarity)

            after[str(repo.path)] = VitalsSnapshot(
                repo_path=repo.path,
                stage=stage,
                hunger=vitals.hunger,
                health=vitals.health,
                energy=vitals.energy,
                mood=vitals.mood,
            )

        ignored = currently_ignored_paths(conn)
        raw_events = news_mod.diff_snapshots(before, after, name_for=repo_name_map(conn))
        # The `gitchi ignore` docstring promises ignored repos stay out of the
        # news feed too — not just `gitchi list`. Filter them out here so the
        # promise is implementation-true.
        events = [e for e in raw_events if str(e.repo_path) not in ignored]
        append_news_events(conn, events)

    return RefreshSummary(
        scanned=len(repos),
        persisted=len(repos),
        ghosts=ghosts,
        enriched_with_github=gh_count,
        enriched_with_claude=cl_count,
        enriched_with_local_energy=local_energy_count,
        news_events=events,
    )


def list_pets(*, include_ignored: bool = False) -> list[Pet]:
    with connect() as conn:
        return all_pets(conn, include_ignored=include_ignored)


def list_recent_news(*, limit: int = 20) -> list[NewsEvent]:
    with connect() as conn:
        return recent_news(conn, limit=limit)
