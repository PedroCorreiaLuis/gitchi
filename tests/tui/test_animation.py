"""Tests for tui/animation.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from gitchi.models import Pet, Rarity, Repo, Species, Stage, Vitals
from gitchi.tui.animation import current_frame, select_frames, should_alert


def _pet(
    *,
    stage: Stage = Stage.ADULT,
    hunger: int = 80,
    health: int = 80,
    energy: int = 80,
    mood: int = 80,
    last_commit_days_ago: int = 1,
) -> Pet:
    return Pet(
        repo=Repo(
            path=Path("/tmp/x"),
            name="x",
            primary_language=None,
            first_commit=None,
            last_commit=datetime.now(UTC) - timedelta(days=last_commit_days_ago),
            commit_count=1,
            size_bytes=0,
            has_tests=False,
            has_ci=False,
        ),
        species=Species.BLOB,
        stage=stage,
        vitals=Vitals(hunger=hunger, health=health, energy=energy, mood=mood, age_days=1),
        rarity=Rarity.COMMON,
    )


def test_select_frames_idle() -> None:
    frames = select_frames(_pet())
    assert len(frames) == 2


def test_select_frames_alert_when_hungry() -> None:
    frames = select_frames(_pet(hunger=10))
    assert len(frames) == 2


def test_select_frames_ghost_stage() -> None:
    frames = select_frames(_pet(stage=Stage.GHOST))
    assert len(frames) == 2


def test_current_frame_alternates() -> None:
    pet = _pet()
    frames = select_frames(pet)
    f0 = current_frame(frames, tick=0)
    f1 = current_frame(frames, tick=1)
    f2 = current_frame(frames, tick=2)
    assert f0 == frames[0]
    assert f1 == frames[1]
    assert f2 == frames[0]


def test_current_frame_egg_is_static_regardless_of_tick() -> None:
    pet = _pet(stage=Stage.EGG)
    frames = select_frames(pet)
    assert current_frame(frames, tick=0) == current_frame(frames, tick=1)


def test_current_frame_empty_list_returns_empty_string() -> None:
    assert current_frame([], tick=0) == ""
    assert current_frame([], tick=42) == ""


def test_should_alert_true_when_hungry() -> None:
    assert should_alert(_pet(hunger=10)) is True


def test_should_alert_true_when_low_health() -> None:
    assert should_alert(_pet(health=10)) is True


def test_should_alert_false_when_healthy() -> None:
    assert should_alert(_pet()) is False


def test_should_alert_false_for_ghost() -> None:
    assert should_alert(_pet(stage=Stage.GHOST, hunger=10)) is False
