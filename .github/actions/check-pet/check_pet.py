"""Runner-side script for the `check-pet` composite action.

Imports gitchi as a library, scans the action's checkout, decides whether the
repo's pet is unhealthy enough to warrant a PR comment, and writes its
findings to the step's $GITHUB_OUTPUT file.

The action.yml wrapper picks the output up and either creates a new sticky
comment or patches the existing one (identified by an HTML marker so we don't
stack comments on every push).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

# When this script runs on a GitHub Actions runner, gitchi has just been
# `pip install`ed by the action's previous step, so the imports below resolve
# from site-packages rather than the action's working tree.
from gitchi import species as species_mod
from gitchi import stats as stats_mod
from gitchi.models import Repo, ScanConfig, StatsConfig
from gitchi.scanner import find_repos
from gitchi.species import emoji_for


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--hunger-threshold", required=True, type=int)
    p.add_argument("--health-threshold", required=True, type=int)
    p.add_argument("--comment-marker", required=True)
    p.add_argument("--output", required=True, type=Path)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    repo = _resolve_repo(args.workspace)
    if repo is None:
        _write_output(args.output, {"needs_comment": "false"})
        print("No git repo detected at workspace root; skipping.", file=sys.stderr)
        return 0

    cfg = StatsConfig()
    vitals = stats_mod.compute(repo, cfg)
    stage = stats_mod.stage_for(repo, cfg)
    species = species_mod.species_for(repo)

    needs_comment = vitals.hunger < args.hunger_threshold or vitals.health < args.health_threshold
    if not needs_comment:
        _write_output(args.output, {"needs_comment": "false"})
        print(
            f"Pet is healthy enough — hunger {vitals.hunger}, health {vitals.health}.",
            file=sys.stderr,
        )
        return 0

    body = _format_comment(
        marker=args.comment_marker,
        repo=repo,
        species=species,
        stage=stage,
        vitals=vitals,
        hunger_threshold=args.hunger_threshold,
        health_threshold=args.health_threshold,
    )

    existing_id = _find_existing_comment_id(args.comment_marker)
    _write_output(
        args.output,
        {
            "needs_comment": "true",
            "comment_body": body,
            "existing_comment_id": existing_id or "",
        },
    )
    return 0


def _resolve_repo(workspace: Path) -> Repo | None:
    """Use the scanner's machinery to grab the workspace's repo snapshot.

    `find_repos` walks recursively, so we set depth=0 to keep it focused on the
    checkout root and rely on its existing handling of `.git` discovery, language
    detection, and the v0.1.1 root-commit fix.
    """
    repos = find_repos([workspace], ScanConfig(depth=0))
    return repos[0] if repos else None


def _format_comment(
    *,
    marker: str,
    repo: Repo,
    species: Any,
    stage: Any,
    vitals: Any,
    hunger_threshold: int,
    health_threshold: int,
) -> str:
    lines = [
        marker,
        f"## {emoji_for(species)} `{repo.name}` is looking a bit unwell",
        "",
        "| stat   | value | threshold |",
        "|--------|-------|-----------|",
        f"| hunger | {vitals.hunger} | {hunger_threshold} |",
        f"| health | {vitals.health} | {health_threshold} |",
        f"| stage  | {stage.value} | — |",
        "",
    ]
    reasons: list[str] = []
    if vitals.hunger < hunger_threshold:
        reasons.append(
            f"**Hunger is {vitals.hunger}/100** — the repo hasn't seen a commit "
            "in a while, so its [gitchi](https://github.com/PedroCorreiaLuis/gitchi) "
            "pet is starving."
        )
    if vitals.health < health_threshold:
        reasons.append(
            f"**Health is {vitals.health}/100** — no tests / no CI / few "
            "commits. The pet is fragile right now."
        )
    lines.extend(f"- {r}" for r in reasons)
    lines.extend(
        [
            "",
            "_Adjust thresholds in your workflow_, or merge this PR to give the "
            "pet a snack 🍽 — committing usually nudges the stats back up.",
        ]
    )
    return "\n".join(lines)


def _find_existing_comment_id(marker: str) -> str | None:
    """Scan the PR's existing comments for one carrying our HTML marker."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not token or not event_path:
        return None
    try:
        event = json.loads(Path(event_path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    pr_number = event.get("pull_request", {}).get("number")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not pr_number or not repo:
        return None

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments?per_page=100"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            comments = json.loads(resp.read())
    except (OSError, ValueError):
        return None

    for c in comments:
        if isinstance(c, dict) and isinstance(c.get("body"), str) and marker in c["body"]:
            return str(c.get("id"))
    return None


def _write_output(path: Path, values: dict[str, str]) -> None:
    """Append `key=value` (or `key<<HEREDOC` for multi-line) to $GITHUB_OUTPUT."""
    lines: list[str] = []
    for key, value in values.items():
        if "\n" in value:
            delim = "GITCHI_EOF"
            lines.append(f"{key}<<{delim}")
            lines.append(value)
            lines.append(delim)
        else:
            lines.append(f"{key}={value}")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
