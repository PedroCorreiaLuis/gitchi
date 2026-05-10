"""Scanner tests — uses real git repos in tmp_path."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from gitchi.models import ScanConfig
from gitchi.scanner import find_repos


def test_finds_a_simple_repo(make_repo, tmp_path: Path) -> None:
    make_repo("alpha", files={"main.py": "print('hi')"})
    repos = find_repos([tmp_path], ScanConfig())
    assert len(repos) == 1
    repo = repos[0]
    assert repo.name == "alpha"
    assert repo.primary_language == "Python"
    assert repo.commit_count == 1


def test_ignores_node_modules(make_repo, tmp_path: Path) -> None:
    make_repo("nm_repo", files={"index.ts": "x"})
    nested = tmp_path / "nm_repo" / "node_modules" / "foo"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / ".git").mkdir()
    repos = find_repos([tmp_path], ScanConfig())
    # only the outer repo should be discovered, never the nested node_modules fake
    assert len(repos) == 1
    assert repos[0].name == "nm_repo"
    for repo in repos:
        assert "node_modules" not in repo.path.parts


def test_respects_depth(make_repo, tmp_path: Path) -> None:
    make_repo("a/b/c/deep", files={"x.py": ""})
    found = find_repos([tmp_path], ScanConfig(depth=2))
    assert found == []
    found = find_repos([tmp_path], ScanConfig(depth=4))
    assert len(found) == 1


def test_detects_tests_and_ci(make_repo, tmp_path: Path) -> None:
    make_repo("tested", with_tests=True, with_ci=True)
    repos = find_repos([tmp_path], ScanConfig())
    assert repos[0].has_tests is True
    assert repos[0].has_ci is True


def test_markdown_only_repo_classified_as_markdown(make_repo, tmp_path: Path) -> None:
    make_repo("notes", files={"README.md": "# x", "guide.md": "..."})
    repos = find_repos([tmp_path], ScanConfig())
    assert repos[0].primary_language == "Markdown"


def test_code_wins_over_markdown(make_repo, tmp_path: Path) -> None:
    make_repo(
        "mixed",
        files={"README.md": "# x", "main.go": "package main", "lib.go": "package main"},
    )
    repos = find_repos([tmp_path], ScanConfig())
    assert repos[0].primary_language == "Go"


def test_first_commit_is_root_not_latest(make_repo, tmp_path: Path) -> None:
    """Regression test for the `git log --reverse --max-count=1` footgun.

    git applies `--max-count` BEFORE reversing the output, so the previous
    implementation returned the most recent commit rather than the root
    commit — making every repo appear 0 days old. The fix uses
    `--max-parents=0` to find root commits directly. This test builds a
    three-commit repo whose root is ~60 days old and asserts the scanner
    sees the actual age, not today's date.
    """
    make_repo(
        "old_repo",
        commits=3,
        first_offset_days=60,
        last_offset_days=0,
    )
    repos = find_repos([tmp_path], ScanConfig())
    assert len(repos) == 1
    repo = repos[0]
    assert repo.first_commit is not None, "first_commit should be detected"
    assert repo.last_commit is not None

    age_days_first = (datetime.now(UTC) - repo.first_commit).days
    age_days_last = (datetime.now(UTC) - repo.last_commit).days

    # Root commit was backdated 60 days; allow a generous fuzz for clock drift.
    assert age_days_first >= 55, (
        f"first_commit looks like the LATEST commit (age={age_days_first} days); "
        "the --reverse + --max-count footgun is back."
    )
    assert age_days_last <= 1, f"last_commit should be near now, got {age_days_last} days"
