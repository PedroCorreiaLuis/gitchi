"""Interactions: feed / play / pet / bury / revive."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import db_path
from .store import bury as _bury
from .store import connect
from .store import revive as _revive

_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[:\s](?P<msg>.+)$", re.IGNORECASE)
_TEST_RUNNERS: list[tuple[str, list[str]]] = [
    ("pyproject.toml", ["pytest"]),
    ("pytest.ini", ["pytest"]),
    ("tox.ini", ["pytest"]),
    ("Cargo.toml", ["cargo", "test"]),
    ("package.json", ["npm", "test"]),
    ("go.mod", ["go", "test", "./..."]),
    ("Gemfile", ["bundle", "exec", "rspec"]),
    ("project.godot", ["godot", "--headless", "--script", "res://run_tests.gd"]),
]


@dataclass(frozen=True, slots=True)
class TodoHit:
    file: Path
    line: int
    message: str


@dataclass(frozen=True, slots=True)
class PlayResult:
    runner: list[str]
    returncode: int
    stdout: str
    stderr: str


def feed(repo_path: Path, *, max_files: int = 500) -> TodoHit | None:
    """Find one stale TODO/FIXME inside the repo to nudge the user toward."""
    skip = {".git", "node_modules", ".venv", "venv", "vendor", "target", "build", "dist"}
    text_exts = {
        ".py",
        ".rs",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".swift",
        ".rb",
        ".gd",
        ".java",
        ".kt",
        ".scala",
        ".cs",
        ".cpp",
        ".cc",
        ".c",
        ".h",
        ".hpp",
        ".hs",
        ".elm",
        ".ex",
        ".exs",
        ".lua",
        ".php",
        ".dart",
        ".sh",
        ".md",
        ".toml",
        ".yaml",
        ".yml",
    }

    seen = 0
    for p in repo_path.rglob("*"):
        if seen >= max_files:
            break
        if any(part in skip for part in p.parts):
            continue
        if p.suffix.lower() not in text_exts:
            continue
        if not p.is_file():
            continue
        seen += 1
        try:
            with p.open(encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    m = _TODO_RE.search(line)
                    if m:
                        return TodoHit(file=p, line=i, message=m.group("msg").strip())
        except OSError:
            continue
    return None


def play(repo_path: Path) -> PlayResult | None:
    """Detect the test runner and run it. Returns None if no runner is detected."""
    runner = detect_runner(repo_path)
    if runner is None:
        return None
    try:
        proc = subprocess.run(
            runner,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return PlayResult(runner=runner, returncode=-1, stdout="", stderr=str(e))
    return PlayResult(
        runner=runner,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def detect_runner(repo_path: Path) -> list[str] | None:
    for marker, cmd in _TEST_RUNNERS:
        if (repo_path / marker).exists():
            return cmd
    return None


def pet(repo_path: Path) -> int:
    """Open the repo in $EDITOR (or `cursor` / `code` / `vim` fallback)."""
    editor = os.environ.get("EDITOR")
    if not editor:
        for candidate in ("cursor", "code", "subl", "vim"):
            if shutil.which(candidate):
                editor = candidate
                break
    if not editor:
        return 127
    proc = subprocess.run([editor, str(repo_path)], check=False)
    return proc.returncode


def bury(repo_path: Path, reason: str | None = None) -> None:
    with connect(db_path()) as conn:
        _bury(conn, repo_path, reason)


def revive(repo_path: Path) -> None:
    with connect(db_path()) as conn:
        _revive(conn, repo_path)
