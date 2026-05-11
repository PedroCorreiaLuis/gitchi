"""Tests for last_play_results storage."""

from __future__ import annotations

from pathlib import Path

from gitchi.store import connect, last_play_result, record_play_result


def test_no_result_returns_none(tmp_path: Path) -> None:
    db = tmp_path / "gitchi.db"
    with connect(db) as conn:
        assert last_play_result(conn, Path("/tmp/whatever")) is None


def test_record_and_read(tmp_path: Path) -> None:
    db = tmp_path / "gitchi.db"
    repo = Path("/tmp/myrepo")
    with connect(db) as conn:
        record_play_result(conn, repo, returncode=0)
        result = last_play_result(conn, repo)
    assert result is not None
    rc, ran_at = result
    assert rc == 0
    assert ran_at > 0


def test_record_overwrites(tmp_path: Path) -> None:
    db = tmp_path / "gitchi.db"
    repo = Path("/tmp/myrepo")
    with connect(db) as conn:
        record_play_result(conn, repo, returncode=0)
        record_play_result(conn, repo, returncode=1)
        result = last_play_result(conn, repo)
    assert result is not None
    assert result[0] == 1


def test_record_negative_returncode(tmp_path: Path) -> None:
    db = tmp_path / "gitchi.db"
    repo = Path("/tmp/myrepo")
    with connect(db) as conn:
        record_play_result(conn, repo, returncode=-1)
        result = last_play_result(conn, repo)
    assert result is not None
    assert result[0] == -1
