"""Verb tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tama import verbs
from tama.verbs import _goto_argv, detect_runner, feed, pet


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


@pytest.fixture
def captured_run(monkeypatch):
    """Stub subprocess.run inside `tama.verbs` and capture its argv."""
    captured: dict[str, list[str]] = {}

    def _fake_run(args, **kwargs):
        captured["args"] = list(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(verbs.subprocess, "run", _fake_run)
    return captured


def test_pet_tokenizes_editor_with_flags(tmp_path: Path, monkeypatch, captured_run) -> None:
    """Regression: `EDITOR='code --wait'` must split into ['code', '--wait', <path>]."""
    monkeypatch.setenv("EDITOR", "code --wait")
    rc = pet(tmp_path)
    assert rc == 0
    assert captured_run["args"] == ["code", "--wait", str(tmp_path)]


def test_pet_handles_bare_editor(tmp_path: Path, monkeypatch, captured_run) -> None:
    monkeypatch.setenv("EDITOR", "vim")
    pet(tmp_path)
    assert captured_run["args"] == ["vim", str(tmp_path)]


def test_pet_handles_quoted_editor_args(tmp_path: Path, monkeypatch, captured_run) -> None:
    """A path with spaces inside an EDITOR string must survive shlex tokenisation."""
    monkeypatch.setenv(
        "EDITOR", '"/Applications/Visual Studio Code.app/Contents/MacOS/Electron" --wait'
    )
    pet(tmp_path)
    assert captured_run["args"] == [
        "/Applications/Visual Studio Code.app/Contents/MacOS/Electron",
        "--wait",
        str(tmp_path),
    ]


def test_pet_returns_127_when_no_editor_and_no_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr(verbs.shutil, "which", lambda _name: None)
    assert pet(tmp_path) == 127


def test_goto_argv_falls_back_to_repo_when_no_file() -> None:
    assert _goto_argv("code", Path("/r/a"), None, None) == ["/r/a"]
    assert _goto_argv("vim", Path("/r/a"), None, None) == ["/r/a"]


def test_goto_argv_code_uses_goto_flag() -> None:
    argv = _goto_argv("code", Path("/r/a"), Path("/r/a/main.py"), 42)
    assert argv == ["--goto", "/r/a/main.py:42"]


def test_goto_argv_cursor_uses_goto_flag() -> None:
    argv = _goto_argv("cursor", Path("/r/a"), Path("/r/a/main.py"), 42)
    assert argv == ["--goto", "/r/a/main.py:42"]


def test_goto_argv_sublime_uses_colon_form() -> None:
    argv = _goto_argv("subl", Path("/r/a"), Path("/r/a/main.py"), 42)
    assert argv == ["/r/a/main.py:42"]


def test_goto_argv_vim_uses_plus_line() -> None:
    argv = _goto_argv("vim", Path("/r/a"), Path("/r/a/main.py"), 42)
    assert argv == ["+42", "/r/a/main.py"]


def test_goto_argv_emacs_uses_plus_line() -> None:
    argv = _goto_argv("emacsclient", Path("/r/a"), Path("/r/a/main.py"), 42)
    assert argv == ["+42", "/r/a/main.py"]


def test_goto_argv_unknown_editor_opens_just_the_file() -> None:
    argv = _goto_argv("nano", Path("/r/a"), Path("/r/a/main.py"), 42)
    assert argv == ["/r/a/main.py"]


def test_goto_argv_strips_path_to_get_binary_name() -> None:
    """An $EDITOR like `/usr/local/bin/code` should still match the 'code' goto form."""
    argv = _goto_argv("/usr/local/bin/code", Path("/r/a"), Path("/r/a/x.py"), 7)
    assert argv == ["--goto", "/r/a/x.py:7"]
