"""Tests for the `gitchi theme` CLI verb."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gitchi import config as config_mod
from gitchi.cli import app

runner = CliRunner()


def test_theme_no_arg_prints_current_and_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.toml")
    result = runner.invoke(app, ["theme"])
    assert result.exit_code == 0
    assert "gameboy-green" in result.stdout
    assert "virtual-boy" in result.stdout
    assert "cozy" in result.stdout


def test_theme_set_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr(config_mod, "config_path", lambda: cfg_path)
    result = runner.invoke(app, ["theme", "virtual-boy"])
    assert result.exit_code == 0
    raw = tomllib.loads(cfg_path.read_text())
    assert raw["tui"]["theme"] == "virtual-boy"


def test_theme_set_unknown_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "config.toml")
    result = runner.invoke(app, ["theme", "not-a-theme"])
    assert result.exit_code != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "not-a-theme" in combined
