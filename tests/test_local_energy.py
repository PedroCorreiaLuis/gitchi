"""Tests for the local Energy proxy."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tama.local_energy import (
    UNCOMMITTED_PENALTY,
    UNTRACKED_DIR_PENALTY,
    combine,
    score_for,
    signals,
)
from tama.models import LocalEnergySignals


def test_combine_returns_100_when_clean() -> None:
    sigs = LocalEnergySignals(uncommitted_files=0, stale_local_branches=0, untracked_dirs=0)
    assert combine(sigs) == 100


def test_combine_applies_penalties() -> None:
    sigs = LocalEnergySignals(uncommitted_files=5, stale_local_branches=0, untracked_dirs=0)
    expected = 100 - 5 * UNCOMMITTED_PENALTY
    assert combine(sigs) == expected


def test_combine_clamps_to_zero() -> None:
    sigs = LocalEnergySignals(uncommitted_files=1000, stale_local_branches=0, untracked_dirs=0)
    assert combine(sigs) == 0


def test_combine_clamps_to_hundred_for_negative_inputs() -> None:
    """We never construct negative signals, but be defensive."""
    sigs = LocalEnergySignals(uncommitted_files=0, stale_local_branches=0, untracked_dirs=0)
    assert combine(sigs) == 100


def test_score_for_returns_none_on_non_repo(tmp_path: Path) -> None:
    """A directory that isn't a git repo should yield None, not crash."""
    assert score_for(tmp_path) is None


def test_signals_detect_uncommitted_files(tmp_path: Path) -> None:
    """A real repo with one uncommitted file produces uncommitted_files=1."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "README.md").write_text("hi")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"],
        check=True,
    )
    # Now introduce drift: edit the file + add an untracked one.
    (tmp_path / "README.md").write_text("hi again")
    (tmp_path / "scratch.py").write_text("# wip")
    sigs = signals(tmp_path)
    assert sigs is not None
    assert sigs.uncommitted_files >= 2


def test_signals_detect_untracked_directory(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "README.md").write_text("hi")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    (tmp_path / "experiments").mkdir()
    (tmp_path / "experiments" / "draft.py").write_text("x = 1")
    sigs = signals(tmp_path)
    assert sigs is not None
    # The untracked dir penalty should apply at least once.
    assert sigs.untracked_dirs >= 1


def test_untracked_dir_penalty_is_applied(tmp_path: Path) -> None:
    sigs = LocalEnergySignals(uncommitted_files=0, stale_local_branches=0, untracked_dirs=2)
    assert combine(sigs) == 100 - 2 * UNTRACKED_DIR_PENALTY
