"""Store tests against a temp SQLite db."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tama.models import Repo, Species, Stage, Vitals
from tama.store import (
    all_pets,
    bury,
    connect,
    get_meta,
    get_mood,
    get_pet,
    revive,
    set_meta,
    upsert_mood,
    upsert_repo,
    upsert_vitals,
)


def _repo(path: Path) -> Repo:
    return Repo(
        path=path,
        name=path.name,
        primary_language="Python",
        first_commit=datetime(2025, 1, 1, tzinfo=UTC),
        last_commit=datetime(2025, 6, 1, tzinfo=UTC),
        commit_count=10,
        size_bytes=1024,
        has_tests=True,
        has_ci=True,
    )


def _vitals() -> Vitals:
    return Vitals(hunger=80, health=70, energy=60, mood=50, age_days=120)


def test_migrations_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "x.db"
    with connect(db):
        pass
    with connect(db) as conn:
        # second connect should not raise; schema_migrations should have one row
        rows = conn.execute("SELECT * FROM schema_migrations").fetchall()
        assert len(rows) >= 1


def test_repo_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "y.db"
    repo = _repo(tmp_path / "alpha")
    with connect(db) as conn:
        upsert_repo(conn, repo)
        upsert_vitals(conn, repo.path, _vitals(), Stage.ADULT, Species.SNAKE)
        pet = get_pet(conn, repo.path)
    assert pet is not None
    assert pet.species is Species.SNAKE
    assert pet.stage is Stage.ADULT
    assert pet.vitals.hunger == 80


def test_bury_revive(tmp_path: Path) -> None:
    db = tmp_path / "z.db"
    repo = _repo(tmp_path / "beta")
    with connect(db) as conn:
        upsert_repo(conn, repo)
        upsert_vitals(conn, repo.path, _vitals(), Stage.ELDER, Species.DRAGON)
        bury(conn, repo.path, "rest in peace")
        pet = get_pet(conn, repo.path)
        assert pet is not None
        assert pet.buried is True
        assert pet.bury_reason == "rest in peace"
        revive(conn, repo.path)
        pet2 = get_pet(conn, repo.path)
        assert pet2 is not None
        assert pet2.buried is False


def test_mood_cache(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    repo = _repo(tmp_path / "gamma")
    with connect(db) as conn:
        upsert_repo(conn, repo)
        upsert_mood(conn, repo.path, 80, "abc")
        assert get_mood(conn, repo.path, "abc") == 80
        assert get_mood(conn, repo.path, "different") is None


def test_meta_kv(tmp_path: Path) -> None:
    db = tmp_path / "meta.db"
    with connect(db) as conn:
        assert get_meta(conn, "foo") is None
        set_meta(conn, "foo", "1")
        set_meta(conn, "foo", "2")
        assert get_meta(conn, "foo") == "2"


def test_all_pets_empty_when_no_vitals(tmp_path: Path) -> None:
    db = tmp_path / "empty.db"
    repo = _repo(tmp_path / "delta")
    with connect(db) as conn:
        upsert_repo(conn, repo)
        assert all_pets(conn) == []


def test_connect_closes_connection_on_exit(tmp_path: Path) -> None:
    """`with connect()` must actually close the sqlite handle on exit.

    Regression test: bare `sqlite3.Connection.__exit__` only commits/rolls back;
    leaving the file descriptor open. We promote `connect` to a contextmanager
    that explicitly closes, and using a closed connection must raise.
    """
    db = tmp_path / "close.db"
    with connect(db) as conn:
        conn.execute("SELECT 1").fetchone()
        held = conn

    with pytest.raises(sqlite3.ProgrammingError):
        held.execute("SELECT 1")


def test_recent_news_preserves_insertion_order_within_a_batch(tmp_path: Path) -> None:
    """Regression: events appended together in priority order must come out in that order.

    All events in a single refresh share the same `created_at`. If `recent_news`
    used `id DESC` as the tiebreak, events would surface in REVERSE insertion
    order — contradicting `news.py`'s documented priority order (stage events
    before hunger events).
    """
    from tama.models import NewsEvent
    from tama.store import append_news_events, recent_news

    db = tmp_path / "ordering.db"
    events = [
        NewsEvent(
            repo_path=Path("/r/a"),
            repo_name="a",
            event_type="evolved",
            from_value="baby",
            to_value="teen",
            detail="evolved: baby → teen",
        ),
        NewsEvent(
            repo_path=Path("/r/a"),
            repo_name="a",
            event_type="became_hungry",
            from_value="60",
            to_value="10",
            detail="is hungry (hunger 60 → 10)",
        ),
    ]
    with connect(db) as conn:
        append_news_events(conn, events)
        recent = recent_news(conn, limit=10)
    # Newest batch first; within the batch, stage event before hunger event.
    assert [e.event_type for e in recent] == ["evolved", "became_hungry"]
