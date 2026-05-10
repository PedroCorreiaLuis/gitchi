"""Config TOML round-trip + dotted-key set."""

from __future__ import annotations

from pathlib import Path

from gitchi import config as config_mod
from gitchi.models import Config


def test_round_trip(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "config.toml"
    monkeypatch.setattr(config_mod, "config_path", lambda: target)

    cfg = Config()
    cfg.scan.depth = 5
    cfg.claude.enabled = True
    cfg.claude.monthly_token_cap = 250_000
    config_mod.save(cfg)

    loaded = config_mod.load()
    assert loaded.scan.depth == 5
    assert loaded.claude.enabled is True
    assert loaded.claude.monthly_token_cap == 250_000


def test_load_returns_defaults_when_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_mod, "config_path", lambda: tmp_path / "missing.toml")
    cfg = config_mod.load()
    assert cfg.scan.paths == ["~/"]
    assert cfg.claude.enabled is False


def test_set_value_handles_dotted_keys() -> None:
    cfg = Config()
    config_mod.set_value(cfg, "scan.depth", "7")
    assert cfg.scan.depth == 7
    config_mod.set_value(cfg, "scan.paths", "~/code, ~/projects")
    assert cfg.scan.paths == ["~/code", "~/projects"]
    config_mod.set_value(cfg, "claude.enabled", "true")
    assert cfg.claude.enabled is True
