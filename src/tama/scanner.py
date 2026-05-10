"""Filesystem walker that finds git repositories.

Heuristics:
- A directory containing a `.git` subdirectory (or `.git` file pointing to a
  worktree) is treated as a repo root.
- Directories matching the configured ignore globs are pruned.
- Submodules (`.git` is a file) are recognized but their children are not
  recursed into (the parent already covers them).
- We respect a max depth from the configured scan roots.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path

from .models import Repo, ScanConfig

_LANG_BY_EXT: dict[str, str] = {
    ".py": "Python",
    ".rs": "Rust",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".go": "Go",
    ".swift": "Swift",
    ".rb": "Ruby",
    ".gd": "GDScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sc": "Scala",
    ".cs": "C#",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C",
    ".hpp": "C++",
    ".hs": "Haskell",
    ".elm": "Elm",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".clj": "Clojure",
    ".lua": "Lua",
    ".php": "PHP",
    ".dart": "Dart",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".fish": "Shell",
    ".md": "Markdown",
}

_TEST_HINTS: tuple[str, ...] = (
    "tests",
    "test",
    "spec",
    "__tests__",
    "pytest.ini",
    "tox.ini",
    "conftest.py",
)


def find_repos(roots: list[Path], config: ScanConfig) -> list[Repo]:
    """Walk roots, return Repo snapshots for every git repository found."""
    repos: list[Repo] = []
    seen: set[Path] = set()

    for root in roots:
        root = root.expanduser().resolve()
        if not root.exists():
            continue

        for repo_path in _walk_for_repos(root, config, depth=0, max_depth=config.depth):
            if repo_path in seen:
                continue
            seen.add(repo_path)
            try:
                repos.append(_snapshot(repo_path))
            except OSError:
                continue

    return sorted(repos, key=lambda r: r.path)


def _walk_for_repos(current: Path, cfg: ScanConfig, depth: int, max_depth: int) -> list[Path]:
    """Yield repo roots beneath `current`, pruning ignored dirs and stopping at max depth."""
    out: list[Path] = []
    if not current.is_dir():
        return out

    git_marker = current / ".git"
    if git_marker.exists():
        out.append(current)
        return out  # don't recurse into a repo's children

    if depth >= max_depth:
        return out

    try:
        children = list(current.iterdir())
    except (PermissionError, OSError):
        return out

    for child in children:
        if not child.is_dir():
            continue
        if _ignored(child.name, cfg.ignore):
            continue
        if child.is_symlink():
            continue
        out.extend(_walk_for_repos(child, cfg, depth + 1, max_depth))

    return out


def _ignored(name: str, patterns: list[str]) -> bool:
    return any(fnmatch(name, pat) for pat in patterns)


def _snapshot(repo_path: Path) -> Repo:
    name = repo_path.name
    primary = _detect_primary_language(repo_path)
    first, last, count = _git_history(repo_path)
    size = _dir_size(repo_path)
    has_tests = _has_tests(repo_path)
    has_ci = (repo_path / ".github" / "workflows").is_dir() or (
        repo_path / ".gitlab-ci.yml"
    ).exists()

    return Repo(
        path=repo_path,
        name=name,
        primary_language=primary,
        first_commit=first,
        last_commit=last,
        commit_count=count,
        size_bytes=size,
        has_tests=has_tests,
        has_ci=has_ci,
    )


def _detect_primary_language(path: Path) -> str | None:
    counts: Counter[str] = Counter()
    for p in _iter_source_files(path, max_files=2000):
        ext = p.suffix.lower()
        lang = _LANG_BY_EXT.get(ext)
        if lang:
            counts[lang] += 1
    if not counts:
        return None
    # If only Markdown, return Markdown. Otherwise prefer code over Markdown.
    most = counts.most_common()
    code_only = [(lang, c) for (lang, c) in most if lang != "Markdown"]
    if code_only:
        return code_only[0][0]
    return most[0][0]


def _iter_source_files(path: Path, max_files: int) -> list[Path]:
    out: list[Path] = []
    skip_dirs = {".git", "node_modules", ".venv", "venv", "vendor", "target", "build", "dist"}
    for p in path.rglob("*"):
        if len(out) >= max_files:
            break
        if any(part in skip_dirs for part in p.parts):
            continue
        if p.is_file():
            out.append(p)
    return out


def _git_history(path: Path) -> tuple[datetime | None, datetime | None, int]:
    """Return (first_commit, last_commit, commit_count). All None / 0 if no commits."""
    try:
        first = _git_first_commit_time(path)
        last = _git_last_commit_time(path)
        count = _git_commit_count(path)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None, 0
    return first, last, count


def _git_run(path: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return res.stdout.strip()


def _git_last_commit_time(path: Path) -> datetime | None:
    out = _git_run(path, "log", "-1", "--format=%ct")
    if not out:
        return None
    return datetime.fromtimestamp(int(out), tz=UTC)


def _git_first_commit_time(path: Path) -> datetime | None:
    """Return the timestamp of the repo's earliest (root) commit.

    `git log --reverse --max-count=1` is a footgun: git applies the count
    limit BEFORE reversing the output, so it returns the most recent commit,
    not the first. Use `--max-parents=0` to find the actual root commit(s)
    instead — there is usually exactly one, and we take the oldest if a repo
    has multiple roots (e.g. after `git replace` or octopus history rewrites).
    """
    out = _git_run(path, "log", "--max-parents=0", "--format=%ct", "HEAD")
    if not out:
        return None
    timestamps = [int(line) for line in out.splitlines() if line.strip().isdigit()]
    if not timestamps:
        return None
    return datetime.fromtimestamp(min(timestamps), tz=UTC)


def _git_commit_count(path: Path) -> int:
    try:
        out = _git_run(path, "rev-list", "--count", "HEAD")
    except subprocess.CalledProcessError:
        return 0
    return int(out) if out.isdigit() else 0


def _dir_size(path: Path) -> int:
    total = 0
    skip = {".git", "node_modules", ".venv", "venv", "target", "build", "dist"}
    for p in path.rglob("*"):
        if any(part in skip for part in p.parts):
            continue
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def _has_tests(path: Path) -> bool:
    for hint in _TEST_HINTS:
        if (path / hint).exists():
            return True
    if list(path.glob("**/test_*.py"))[:1]:
        return True
    return bool(list(path.glob("**/*.test.ts"))[:1] or list(path.glob("**/*.test.js"))[:1])
