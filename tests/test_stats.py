"""Stat formula tests — pure functions, no I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from tama.models import Repo, Stage, StatsConfig
from tama.stats import compute, stage_for


def _repo(**overrides) -> Repo:
    base = {
        "path": Path("/tmp/x"),
        "name": "x",
        "primary_language": "Python",
        "first_commit": datetime(2025, 1, 1, tzinfo=UTC),
        "last_commit": datetime(2025, 1, 1, tzinfo=UTC),
        "commit_count": 1,
        "size_bytes": 0,
        "has_tests": False,
        "has_ci": False,
    }
    base.update(overrides)
    return Repo(**base)


def test_hunger_full_for_today_commit() -> None:
    now = datetime(2025, 1, 1, tzinfo=UTC)
    v = compute(_repo(last_commit=now), StatsConfig(), now=now)
    assert v.hunger == 100


def test_hunger_zero_after_30_days() -> None:
    now = datetime(2025, 2, 15, tzinfo=UTC)
    v = compute(_repo(last_commit=datetime(2025, 1, 1, tzinfo=UTC)), StatsConfig(), now=now)
    assert v.hunger == 0


def test_health_with_tests_and_ci() -> None:
    repo = _repo(has_tests=True, has_ci=True, commit_count=300)
    v = compute(repo, StatsConfig())
    # 50 base + 20 tests + 20 ci + 5 + 5
    assert v.health == 100


def test_stage_egg_for_new_repo() -> None:
    now = datetime.now(UTC)
    repo = _repo(first_commit=now - timedelta(days=2), last_commit=now)
    assert stage_for(repo, StatsConfig(), now=now) is Stage.EGG


def test_stage_ghost_for_silent_repo() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo = _repo(
        first_commit=datetime(2024, 1, 1, tzinfo=UTC),
        last_commit=datetime(2025, 1, 1, tzinfo=UTC),
    )
    assert stage_for(repo, StatsConfig(), now=now) is Stage.GHOST


def test_stage_progression() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    cases = [
        (5, Stage.EGG),
        (20, Stage.BABY),
        (60, Stage.TEEN),
        (200, Stage.ADULT),
        (400, Stage.ELDER),
    ]
    for age_days, expected in cases:
        repo = _repo(
            first_commit=now - timedelta(days=age_days),
            last_commit=now - timedelta(days=1),  # not a ghost
        )
        assert stage_for(repo, StatsConfig(), now=now) is expected, age_days


def test_overrides_applied() -> None:
    v = compute(_repo(), StatsConfig(), energy_override=10, mood_override=90)
    assert v.energy == 10
    assert v.mood == 90
