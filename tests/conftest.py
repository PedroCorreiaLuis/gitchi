"""Shared pytest fixtures."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.fixture
def make_repo(tmp_path: Path):
    """Factory fixture: build a real git repo with a configurable history."""

    def _make(
        name: str,
        *,
        files: dict[str, str] | None = None,
        commits: int = 1,
        first_offset_days: int = 0,
        last_offset_days: int = 0,
        with_tests: bool = False,
        with_ci: bool = False,
    ) -> Path:
        path = tmp_path / name
        path.mkdir(parents=True, exist_ok=True)

        run = lambda *args: subprocess.run(  # noqa: E731
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
        )

        run("init", "-q", "-b", "main")
        run("config", "user.email", "test@example.com")
        run("config", "user.name", "Test")

        for relpath, content in (files or {"README.md": "hello"}).items():
            target = path / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

        if with_tests:
            (path / "tests").mkdir(exist_ok=True)
            (path / "tests" / "test_smoke.py").write_text("def test_ok():\n    assert True\n")
        if with_ci:
            (path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")

        run("add", "-A")

        first_dt = datetime.now(UTC).replace(microsecond=0).timestamp() - first_offset_days * 86400
        last_dt = datetime.now(UTC).replace(microsecond=0).timestamp() - last_offset_days * 86400

        for i in range(commits):
            ts = first_dt if i == 0 else last_dt if i == commits - 1 else (first_dt + last_dt) / 2
            iso = datetime.fromtimestamp(ts, tz=UTC).isoformat()
            env = {
                "GIT_AUTHOR_DATE": iso,
                "GIT_COMMITTER_DATE": iso,
                "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
            }
            if i > 0:
                # add an empty incremental change so commits aren't no-ops
                (path / f"commit_{i}.txt").write_text(str(i))
                run("add", "-A")
            subprocess.run(
                ["git", "-C", str(path), "commit", "-q", "-m", f"commit {i}"],
                check=True,
                env=env,
                capture_output=True,
                text=True,
            )

        return path

    return _make
