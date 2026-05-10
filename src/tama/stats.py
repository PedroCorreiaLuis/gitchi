"""Compute Vitals and Stage from a Repo snapshot.

Pure functions: no I/O, no state. Optional enrichments (energy from GitHub,
mood from Claude) are passed in by the caller.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .models import Repo, Stage, StatsConfig, Vitals


def compute(
    repo: Repo,
    cfg: StatsConfig,
    *,
    energy_override: int | None = None,
    mood_override: int | None = None,
    now: datetime | None = None,
) -> Vitals:
    now = now or datetime.now(UTC)
    age_days = _age_days(repo, now)
    return Vitals(
        hunger=_hunger(repo, now),
        health=_health(repo),
        energy=energy_override if energy_override is not None else 50,
        mood=mood_override if mood_override is not None else 50,
        age_days=age_days,
    )


def stage_for(repo: Repo, cfg: StatsConfig, now: datetime | None = None) -> Stage:
    now = now or datetime.now(UTC)
    if repo.last_commit is None:
        # never committed → still an egg
        return Stage.EGG

    days_silent = (now - repo.last_commit).days
    if days_silent > cfg.ghost_after_days:
        return Stage.GHOST

    age = _age_days(repo, now)
    if age <= 7:
        return Stage.EGG
    if age <= 30:
        return Stage.BABY
    if age <= 90:
        return Stage.TEEN
    if age <= 365:
        return Stage.ADULT
    return Stage.ELDER


def _age_days(repo: Repo, now: datetime) -> int:
    if repo.first_commit is None:
        return 0
    return max(0, (now - repo.first_commit).days)


def _hunger(repo: Repo, now: datetime) -> int:
    if repo.last_commit is None:
        return 0
    days = (now - repo.last_commit).days
    if days <= 0:
        return 100
    # linear decay: full at 0 days, zero at 30 days
    score = 100 - int(days * 100 / 30)
    return max(0, min(100, score))


def _health(repo: Repo) -> int:
    score = 50
    if repo.has_tests:
        score += 20
    if repo.has_ci:
        score += 20
    if repo.commit_count >= 50:
        score += 5
    if repo.commit_count >= 200:
        score += 5
    return max(0, min(100, score))
