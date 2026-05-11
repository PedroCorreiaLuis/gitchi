"""Tests for tui/status_reason.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from gitchi.models import Pet, Rarity, Repo, Species, Stage, Vitals
from gitchi.tui.status_reason import derive_reason


def _pet(
    *,
    hunger: int = 80,
    health: int = 80,
    energy: int = 80,
    mood: int = 80,
    stage: Stage = Stage.ADULT,
    ignored: bool = False,
    buried: bool = False,
    bury_reason: str | None = None,
    last_commit_days_ago: int | None = 1,
) -> Pet:
    last_commit = (
        datetime.now(UTC) - timedelta(days=last_commit_days_ago)
        if last_commit_days_ago is not None
        else None
    )
    return Pet(
        repo=Repo(
            path=Path("/tmp/x"),
            name="x",
            primary_language=None,
            first_commit=None,
            last_commit=last_commit,
            commit_count=1,
            size_bytes=0,
            has_tests=False,
            has_ci=False,
        ),
        species=Species.GENERIC_BLOB,
        stage=stage,
        vitals=Vitals(hunger=hunger, health=health, energy=energy, mood=mood, age_days=1),
        rarity=Rarity.COMMON,
        ignored=ignored,
        buried=buried,
        bury_reason=bury_reason,
    )


def test_ignored() -> None:
    assert derive_reason(_pet(ignored=True)) == "ignored"


def test_buried_with_reason() -> None:
    assert "tombstone" in derive_reason(_pet(buried=True, bury_reason="tombstone"))


def test_buried_default_reason() -> None:
    assert "at peace" in derive_reason(_pet(buried=True))


def test_ghost_dormant() -> None:
    reason = derive_reason(_pet(stage=Stage.GHOST, last_commit_days_ago=120))
    assert "dormant" in reason
    assert "120" in reason


def test_thriving_recent_commits() -> None:
    reason = derive_reason(_pet(hunger=90, health=90, energy=90, mood=90, last_commit_days_ago=0))
    assert reason.startswith("thriving")


def test_hungry_with_days_since_commit() -> None:
    reason = derive_reason(_pet(hunger=10, health=30, energy=30, mood=30, last_commit_days_ago=9))
    assert reason.startswith("hungry")
    assert "9d" in reason or "9 days" in reason


def test_starving() -> None:
    reason = derive_reason(_pet(hunger=5, health=5, energy=5, mood=5, last_commit_days_ago=30))
    assert reason.startswith("starving")


def test_no_last_commit_ghost() -> None:
    reason = derive_reason(_pet(stage=Stage.GHOST, last_commit_days_ago=None))
    assert "ghost" in reason
