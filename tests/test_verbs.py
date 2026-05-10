"""Verb tests."""

from __future__ import annotations

from pathlib import Path

from tama.verbs import detect_runner, feed


def test_feed_finds_a_todo(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("# TODO: rewrite this in rust\nprint('hi')\n")
    hit = feed(tmp_path)
    assert hit is not None
    assert hit.line == 1
    assert "rust" in hit.message


def test_feed_returns_none_when_clean(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hi')\n")
    assert feed(tmp_path) is None


def test_detect_runner_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert detect_runner(tmp_path) == ["pytest"]


def test_detect_runner_rust(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    assert detect_runner(tmp_path) == ["cargo", "test"]


def test_detect_runner_none_when_no_marker(tmp_path: Path) -> None:
    assert detect_runner(tmp_path) is None
