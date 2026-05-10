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


def test_first_refresh_emits_hatched_news_for_each_new_repo(
    tmp_path: Path, monkeypatch, make_repo
) -> None:
    db = tmp_path / "tama.db"
    monkeypatch.setattr(config_mod, "db_path", lambda: db)
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)

    make_repo("alpha", files={"main.py": "x = 1\n"}, commits=1)

    cfg = Config()
    cfg.scan.paths = [str(tmp_path)]
    cfg.scan.depth = 2

    summary = refresh_mod.refresh(cfg)
    assert len(summary.news_events) == 1
    event = summary.news_events[0]
    assert event.event_type == "hatched"
    assert event.repo_name == "alpha"


def test_second_refresh_with_no_change_emits_no_news(
    tmp_path: Path, monkeypatch, make_repo
) -> None:
    db = tmp_path / "tama.db"
    monkeypatch.setattr(config_mod, "db_path", lambda: db)
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)

    make_repo("alpha", files={"main.py": "x = 1\n"}, commits=1)

    cfg = Config()
    cfg.scan.paths = [str(tmp_path)]
    cfg.scan.depth = 2

    refresh_mod.refresh(cfg)  # first scan: hatched
    second = refresh_mod.refresh(cfg)  # second scan: nothing changed
    assert second.news_events == []


def test_refresh_writes_to_vitals_history(tmp_path: Path, monkeypatch, make_repo) -> None:
    """Each refresh should append exactly one history row per repo."""
    db = tmp_path / "tama.db"
    monkeypatch.setattr(config_mod, "db_path", lambda: db)
    monkeypatch.setattr(config_mod, "data_dir", lambda: tmp_path)

    make_repo("alpha", files={"main.py": "x = 1\n"}, commits=1)

    cfg = Config()
    cfg.scan.paths = [str(tmp_path)]
    cfg.scan.depth = 2

    refresh_mod.refresh(cfg)
    refresh_mod.refresh(cfg)
    refresh_mod.refresh(cfg)

    from tama.store import connect, vitals_history

    pets = refresh_mod.list_pets()
    alpha = next(p for p in pets if p.repo.name == "alpha")
    with connect() as conn:
        history = vitals_history(conn, alpha.repo.path, limit=10)
    assert len(history) == 3
