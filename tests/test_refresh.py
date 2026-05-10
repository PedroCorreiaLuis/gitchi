"""End-to-end refresh test on a tmp filesystem."""

from __future__ import annotations

from pathlib import Path

from tama import config as config_mod
from tama import refresh as refresh_mod
from tama.models import Config


def test_refresh_full_pipeline(tmp_path: Path, monkeypatch, make_repo) -> None:
    db = tmp_path / "tama.db"
    monkeypatch.setattr(config_mod, "db_path", lambda: db)
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)

    make_repo("alpha", files={"main.py": "x = 1\n"}, commits=2)
    make_repo("beta", files={"main.go": "package main\n"}, commits=1)

    cfg = Config()
    cfg.scan.paths = [str(tmp_path)]
    cfg.scan.depth = 2

    summary = refresh_mod.refresh(cfg)
    assert summary.scanned == 2

    pets = refresh_mod.list_pets()
    assert {p.repo.name for p in pets} == {"alpha", "beta"}
