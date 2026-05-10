"""Optional GitHub enrichment for the Energy stat.

Energy reflects open-issue/PR rot: 100 = clean, drains by 5 for every issue
older than 30 days, capped at 0. Disabled when no GITHUB_TOKEN is set or
when `github.enabled = false` in the config.

Repo→GitHub mapping is best-effort: we parse `git remote get-url origin`,
match `github.com[:/]<owner>/<repo>(.git)?`, and skip silently otherwise.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

_REMOTE_RE = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$")


def repo_slug(path: Path) -> tuple[str, str] | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None

    m = _REMOTE_RE.search(out)
    if not m:
        return None
    return m.group("owner"), m.group("repo")


def energy_score(
    path: Path, *, token: str | None = None, client: httpx.Client | None = None
) -> int | None:
    """Return Energy 0–100 for a repo, or None if not enrichable.

    A return of None tells the caller to fall back to the neutral default.
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    slug = repo_slug(path)
    if slug is None:
        return None
    owner, repo = slug

    own_client = client is None
    client = client or httpx.Client(
        base_url="https://api.github.com",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=10.0,
    )
    try:
        url = f"/repos/{owner}/{repo}/issues"
        params = {"state": "open", "per_page": "100", "sort": "updated", "direction": "asc"}
        response = client.get(url, params=params)
        if response.status_code != 200:
            return None
        issues = response.json()
    finally:
        if own_client:
            client.close()

    cutoff = datetime.now(UTC) - timedelta(days=30)
    stale = sum(1 for issue in issues if _updated_at(issue) < cutoff)
    score = 100 - stale * 5
    return max(0, min(100, score))


def _updated_at(issue: dict[str, object]) -> datetime:
    raw = issue.get("updated_at") or issue.get("created_at")
    if not isinstance(raw, str):
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)
