"""Local-only Energy proxy.

The original Energy stat reflected open-issue rot via the GitHub API. When
GitHub enrichment is off (the default), Energy was hardcoded to a neutral 50
which made the dashboard feel placeholder-y. This module derives an Energy
score from purely local signals:

- uncommitted files (`git status --porcelain`) — work in progress hanging around
- stale local branches (any local branch >30d old that isn't the default branch)
- untracked top-level dirs — bigger drift than a single edited file

The score starts at 100 and is reduced by each signal. `score_for(path)`
returns `None` if git is unavailable or the path isn't a real repo — the
caller falls back to the neutral 50 in that case.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import LocalEnergySignals

STALE_BRANCH_AGE_DAYS = 30
UNCOMMITTED_PENALTY = 3
STALE_BRANCH_PENALTY = 5
UNTRACKED_DIR_PENALTY = 4


def score_for(path: Path) -> int | None:
    """Return a 0-100 Energy score for `path`, or None if git isn't usable."""
    sigs = signals(path)
    if sigs is None:
        return None
    return combine(sigs)


def combine(sigs: LocalEnergySignals) -> int:
    score = 100
    score -= sigs.uncommitted_files * UNCOMMITTED_PENALTY
    score -= sigs.stale_local_branches * STALE_BRANCH_PENALTY
    score -= sigs.untracked_dirs * UNTRACKED_DIR_PENALTY
    return max(0, min(100, score))


def signals(path: Path) -> LocalEnergySignals | None:
    try:
        uncommitted = _uncommitted_files(path)
        stale_branches = _stale_local_branches(path)
        untracked_dirs = _untracked_dirs(path)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return LocalEnergySignals(
        uncommitted_files=uncommitted,
        stale_local_branches=stale_branches,
        untracked_dirs=untracked_dirs,
    )


def _uncommitted_files(path: Path) -> int:
    out = _git(path, "status", "--porcelain")
    return sum(1 for line in out.splitlines() if line.strip())


def _untracked_dirs(path: Path) -> int:
    out = _git(path, "status", "--porcelain")
    untracked = [line for line in out.splitlines() if line.startswith("?? ")]
    # A trailing slash on the path tells git that this is a directory entry.
    return sum(1 for line in untracked if line.rstrip().endswith("/"))


def _stale_local_branches(path: Path) -> int:
    """Count local branches whose tip is >STALE_BRANCH_AGE_DAYS old, excluding default."""
    default_branch = _default_branch(path)
    out = _git(
        path,
        "for-each-ref",
        "--format=%(refname:short)|%(committerdate:unix)",
        "refs/heads/",
    )
    cutoff = (datetime.now(UTC) - timedelta(days=STALE_BRANCH_AGE_DAYS)).timestamp()
    stale = 0
    for line in out.splitlines():
        if "|" not in line:
            continue
        name, ts = line.split("|", 1)
        if name == default_branch:
            continue
        try:
            if int(ts) < cutoff:
                stale += 1
        except ValueError:
            continue
    return stale


def _default_branch(path: Path) -> str:
    """Best-effort detection of the repo's default branch (main / master / whatever)."""
    try:
        out = _git(path, "symbolic-ref", "refs/remotes/origin/HEAD")
        return out.removeprefix("refs/remotes/origin/").strip()
    except subprocess.CalledProcessError:
        pass
    # Fall back to checking which of main/master exists locally.
    for candidate in ("main", "master"):
        try:
            _git(path, "rev-parse", "--verify", candidate)
        except subprocess.CalledProcessError:
            continue
        return candidate
    # Final fallback: the currently checked-out branch — at least we won't double-count it.
    try:
        return _git(path, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except subprocess.CalledProcessError:
        return "main"


def _git(path: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    return res.stdout
