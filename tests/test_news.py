"""Tests for news.diff_snapshots."""

from __future__ import annotations

from pathlib import Path

from tama.models import Stage, VitalsSnapshot
from tama.news import diff_snapshots


def _snap(path: str, stage: Stage, hunger: int = 100) -> VitalsSnapshot:
    return VitalsSnapshot(
        repo_path=Path(path),
        stage=stage,
        hunger=hunger,
        health=80,
        energy=50,
        mood=50,
    )


def test_hatched_event_when_repo_is_new() -> None:
    after = {"/repos/alpha": _snap("/repos/alpha", Stage.EGG)}
    events = diff_snapshots({}, after, name_for={"/repos/alpha": "alpha"})
    assert len(events) == 1
    assert events[0].event_type == "hatched"
    assert events[0].repo_name == "alpha"


def test_evolved_event_when_stage_advances() -> None:
    before = {"/r/a": _snap("/r/a", Stage.BABY)}
    after = {"/r/a": _snap("/r/a", Stage.TEEN)}
    events = diff_snapshots(before, after, name_for={"/r/a": "a"})
    assert len(events) == 1
    assert events[0].event_type == "evolved"
    assert events[0].from_value == "baby"
    assert events[0].to_value == "teen"


def test_became_ghost_event() -> None:
    before = {"/r/a": _snap("/r/a", Stage.ADULT)}
    after = {"/r/a": _snap("/r/a", Stage.GHOST)}
    events = diff_snapshots(before, after, name_for={"/r/a": "a"})
    assert len(events) == 1
    assert events[0].event_type == "became_ghost"


def test_revived_event_when_stage_leaves_ghost() -> None:
    before = {"/r/a": _snap("/r/a", Stage.GHOST)}
    after = {"/r/a": _snap("/r/a", Stage.TEEN)}
    events = diff_snapshots(before, after, name_for={"/r/a": "a"})
    assert len(events) == 1
    assert events[0].event_type == "revived"


def test_became_hungry_event_when_hunger_crosses_threshold() -> None:
    before = {"/r/a": _snap("/r/a", Stage.BABY, hunger=60)}
    after = {"/r/a": _snap("/r/a", Stage.BABY, hunger=10)}
    events = diff_snapshots(before, after, name_for={"/r/a": "a"})
    assert any(e.event_type == "became_hungry" for e in events)


def test_recovered_event_when_hunger_climbs_above_recovery() -> None:
    before = {"/r/a": _snap("/r/a", Stage.BABY, hunger=20)}
    after = {"/r/a": _snap("/r/a", Stage.BABY, hunger=95)}
    events = diff_snapshots(before, after, name_for={"/r/a": "a"})
    assert any(e.event_type == "recovered_from_hunger" for e in events)


def test_no_event_when_state_unchanged() -> None:
    before = {"/r/a": _snap("/r/a", Stage.BABY, hunger=80)}
    after = {"/r/a": _snap("/r/a", Stage.BABY, hunger=80)}
    events = diff_snapshots(before, after, name_for={"/r/a": "a"})
    assert events == []


def test_stage_regression_does_not_emit_evolved() -> None:
    """Going backwards (teen → baby) shouldn't generate an 'evolved' event."""
    before = {"/r/a": _snap("/r/a", Stage.TEEN)}
    after = {"/r/a": _snap("/r/a", Stage.BABY)}
    events = diff_snapshots(before, after, name_for={"/r/a": "a"})
    assert not any(e.event_type == "evolved" for e in events)


def test_headline_has_icon_and_name() -> None:
    after = {"/r/a": _snap("/r/a", Stage.EGG)}
    events = diff_snapshots({}, after, name_for={"/r/a": "a"})
    headline = events[0].headline
    assert "a" in headline
    assert "🥚" in headline  # hatched icon
