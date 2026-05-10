"""Top-level orchestration: scan → enrich → persist."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import claude as claude_mod
from . import config as config_mod
from . import github as github_mod
from . import species as species_mod
from . import stats as stats_mod
from .models import Config, Pet, Stage
from .scanner import find_repos
from .store import all_pets, connect, upsert_repo, upsert_vitals


@dataclass(frozen=True, slots=True)
class RefreshSummary:
    scanned: int
    persisted: int
    ghosts: int
    enriched_with_github: int
    enriched_with_claude: int


def refresh(cfg: Config | None = None) -> RefreshSummary:
    cfg = cfg or config_mod.load()
    roots = [Path(p).expanduser() for p in cfg.scan.paths]
    repos = find_repos(roots, cfg.scan)

    gh_count = 0
    cl_count = 0
    ghosts = 0

    with connect() as conn:
        for repo in repos:
            upsert_repo(conn, repo)

            energy = github_mod.energy_score(repo.path) if cfg.github.enabled else None
            if energy is not None:
                gh_count += 1

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

            upsert_vitals(conn, repo.path, vitals, stage, species)

    return RefreshSummary(
        scanned=len(repos),
        persisted=len(repos),
        ghosts=ghosts,
        enriched_with_github=gh_count,
        enriched_with_claude=cl_count,
    )


def list_pets() -> list[Pet]:
    with connect() as conn:
        return all_pets(conn)
