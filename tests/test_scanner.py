"""Scanner tests — uses real git repos in tmp_path."""

from __future__ import annotations

from pathlib import Path

from tama.models import ScanConfig
from tama.scanner import find_repos


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
