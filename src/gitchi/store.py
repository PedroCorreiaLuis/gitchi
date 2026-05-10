"""SQLite persistence layer.

Migrations live in `src/gitchi/migrations/` and are applied in filename order
on every connection. Applied filenames are recorded in the `schema_migrations`
table; the `meta` table is reserved for application key/value state such as
the monthly Claude token budget.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

from .config import db_path
from .models import NewsEvent, Pet, Repo, Species, Stage, Vitals, VitalsSnapshot


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, run pending migrations, close on exit.

    Used as a context manager: ``with connect() as conn: ...``. The bare
    ``sqlite3.Connection.__exit__`` only commits/rolls back, so wrapping it
    here ensures the connection is actually closed and the file descriptor
    released — important for long-running processes (TUI, menu-bar).
    """
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, detect_types=sqlite3.PARSE_DECLTYPES, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        _migrate(conn)
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# migrations
# ---------------------------------------------------------------------------


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at INTEGER NOT NULL)"
    )
    applied = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
    for fname, sql in _iter_migration_files():
        if fname in applied:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
            (fname, _now_epoch()),
        )


def _iter_migration_files() -> Iterator[tuple[str, str]]:
    pkg = files("gitchi").joinpath("migrations")
    names = sorted(p.name for p in pkg.iterdir() if p.name.endswith(".sql"))
    for name in names:
        yield name, pkg.joinpath(name).read_text(encoding="utf-8")


def _now_epoch() -> int:
    return int(datetime.now(UTC).timestamp())


# ---------------------------------------------------------------------------
# repo CRUD
# ---------------------------------------------------------------------------


def upsert_repo(conn: sqlite3.Connection, repo: Repo) -> None:
    conn.execute(
        """
        INSERT INTO repos (path, name, primary_language, first_commit, last_commit,
                          commit_count, size_bytes, has_tests, has_ci, last_scanned)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            name=excluded.name,
            primary_language=excluded.primary_language,
            first_commit=excluded.first_commit,
            last_commit=excluded.last_commit,
            commit_count=excluded.commit_count,
            size_bytes=excluded.size_bytes,
            has_tests=excluded.has_tests,
            has_ci=excluded.has_ci,
            last_scanned=excluded.last_scanned
        """,
        (
            str(repo.path),
            repo.name,
            repo.primary_language,
            int(repo.first_commit.timestamp()) if repo.first_commit else None,
            int(repo.last_commit.timestamp()) if repo.last_commit else None,
            repo.commit_count,
            repo.size_bytes,
            1 if repo.has_tests else 0,
            1 if repo.has_ci else 0,
            _now_epoch(),
        ),
    )


def all_repos(conn: sqlite3.Connection) -> list[Repo]:
    rows = conn.execute("SELECT * FROM repos ORDER BY path").fetchall()
    return [_row_to_repo(r) for r in rows]


def get_repo(conn: sqlite3.Connection, path: str | Path) -> Repo | None:
    row = conn.execute("SELECT * FROM repos WHERE path = ?", (str(path),)).fetchone()
    return _row_to_repo(row) if row else None


def find_repo_by_name(conn: sqlite3.Connection, name: str) -> Repo | None:
    """Look up a repo by its short name (last path component). First match wins."""
    row = conn.execute(
        "SELECT * FROM repos WHERE name = ? ORDER BY path LIMIT 1", (name,)
    ).fetchone()
    return _row_to_repo(row) if row else None


def _row_to_repo(row: sqlite3.Row) -> Repo:
    return Repo(
        path=Path(row["path"]),
        name=row["name"],
        primary_language=row["primary_language"],
        first_commit=_epoch_to_dt(row["first_commit"]),
        last_commit=_epoch_to_dt(row["last_commit"]),
        commit_count=row["commit_count"],
        size_bytes=row["size_bytes"],
        has_tests=bool(row["has_tests"]),
        has_ci=bool(row["has_ci"]),
    )


def _epoch_to_dt(epoch: int | None) -> datetime | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=UTC)


# ---------------------------------------------------------------------------
# vitals cache
# ---------------------------------------------------------------------------


def upsert_vitals(
    conn: sqlite3.Connection,
    repo_path: Path,
    vitals: Vitals,
    stage: Stage,
    species: Species,
) -> None:
    conn.execute(
        """
        INSERT INTO vitals_cache (repo_path, hunger, health, energy, mood, age_days,
                                  stage, species, computed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(repo_path) DO UPDATE SET
            hunger=excluded.hunger,
            health=excluded.health,
            energy=excluded.energy,
            mood=excluded.mood,
            age_days=excluded.age_days,
            stage=excluded.stage,
            species=excluded.species,
            computed_at=excluded.computed_at
        """,
        (
            str(repo_path),
            vitals.hunger,
            vitals.health,
            vitals.energy,
            vitals.mood,
            vitals.age_days,
            stage.value,
            species.value,
            _now_epoch(),
        ),
    )


_PETS_SELECT = """
    SELECT r.*, v.hunger, v.health, v.energy, v.mood, v.age_days, v.stage, v.species,
           b.buried_at, b.reason AS bury_reason,
           i.ignored_at
    FROM repos r
    LEFT JOIN vitals_cache v ON v.repo_path = r.path
    LEFT JOIN bury_state b ON b.repo_path = r.path
    LEFT JOIN ignore_state i ON i.repo_path = r.path
"""


def all_pets(conn: sqlite3.Connection, *, include_ignored: bool = False) -> list[Pet]:
    """Return every pet with cached vitals.

    Ignored pets are filtered out by default — `include_ignored=True` for the
    `gitchi list --all` view that surfaces them.
    """
    rows = conn.execute(_PETS_SELECT + " ORDER BY r.path").fetchall()
    pets: list[Pet] = []
    for row in rows:
        if row["hunger"] is None:
            continue  # no vitals yet
        if row["ignored_at"] is not None and not include_ignored:
            continue
        pets.append(_row_to_pet(row))
    return pets


def get_pet(conn: sqlite3.Connection, repo_path: Path) -> Pet | None:
    rows = conn.execute(_PETS_SELECT + " WHERE r.path = ?", (str(repo_path),)).fetchall()
    if not rows or rows[0]["hunger"] is None:
        return None
    return _row_to_pet(rows[0])


def _row_to_pet(row: sqlite3.Row) -> Pet:
    repo = _row_to_repo(row)
    vitals = Vitals(
        hunger=row["hunger"],
        health=row["health"],
        energy=row["energy"],
        mood=row["mood"],
        age_days=row["age_days"],
    )
    return Pet(
        repo=repo,
        species=Species(row["species"]),
        stage=Stage(row["stage"]),
        vitals=vitals,
        buried=row["buried_at"] is not None,
        bury_reason=row["bury_reason"],
        ignored=row["ignored_at"] is not None,
    )


# ---------------------------------------------------------------------------
# bury / revive
# ---------------------------------------------------------------------------


def bury(conn: sqlite3.Connection, repo_path: Path, reason: str | None) -> None:
    conn.execute(
        """
        INSERT INTO bury_state (repo_path, buried_at, reason) VALUES (?, ?, ?)
        ON CONFLICT(repo_path) DO UPDATE SET buried_at=excluded.buried_at, reason=excluded.reason
        """,
        (str(repo_path), _now_epoch(), reason),
    )


def revive(conn: sqlite3.Connection, repo_path: Path) -> None:
    conn.execute("DELETE FROM bury_state WHERE repo_path = ?", (str(repo_path),))


# ---------------------------------------------------------------------------
# mood cache
# ---------------------------------------------------------------------------


def get_mood(conn: sqlite3.Connection, repo_path: Path, sample_hash: str) -> int | None:
    row = conn.execute(
        "SELECT score FROM mood_cache WHERE repo_path = ? AND sample_hash = ?",
        (str(repo_path), sample_hash),
    ).fetchone()
    return int(row["score"]) if row else None


def upsert_mood(conn: sqlite3.Connection, repo_path: Path, score: int, sample_hash: str) -> None:
    conn.execute(
        """
        INSERT INTO mood_cache (repo_path, score, sample_hash, computed_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(repo_path) DO UPDATE SET
            score=excluded.score,
            sample_hash=excluded.sample_hash,
            computed_at=excluded.computed_at
        """,
        (str(repo_path), score, sample_hash, _now_epoch()),
    )


# ---------------------------------------------------------------------------
# meta KV — used to track the monthly Claude token budget
# ---------------------------------------------------------------------------


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# ---------------------------------------------------------------------------
# ignore_state — pets the user has explicitly removed from the dashboard
# ---------------------------------------------------------------------------


def ignore(conn: sqlite3.Connection, repo_path: Path, reason: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO ignore_state (repo_path, ignored_at, reason) VALUES (?, ?, ?)
        ON CONFLICT(repo_path) DO UPDATE SET
            ignored_at = excluded.ignored_at,
            reason = excluded.reason
        """,
        (str(repo_path), _now_epoch(), reason),
    )


def unignore(conn: sqlite3.Connection, repo_path: Path) -> None:
    conn.execute("DELETE FROM ignore_state WHERE repo_path = ?", (str(repo_path),))


def is_ignored(conn: sqlite3.Connection, repo_path: Path) -> bool:
    row = conn.execute(
        "SELECT 1 FROM ignore_state WHERE repo_path = ?", (str(repo_path),)
    ).fetchone()
    return row is not None


def currently_ignored_paths(conn: sqlite3.Connection) -> set[str]:
    """Return the set of currently-ignored repo paths (as path strings).

    Used by the refresh orchestrator to filter ignored repos out of the news
    events stream — the `gitchi ignore` docstring promises this and `all_pets`
    alone only filters the list view, not the news feed.
    """
    rows = conn.execute("SELECT repo_path FROM ignore_state").fetchall()
    return {row["repo_path"] for row in rows}


# ---------------------------------------------------------------------------
# news_events
# ---------------------------------------------------------------------------


def append_news_events(conn: sqlite3.Connection, events: list[NewsEvent]) -> None:
    if not events:
        return
    now = _now_epoch()
    conn.executemany(
        """
        INSERT INTO news_events (repo_path, event_type, from_value, to_value, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                str(e.repo_path),
                e.event_type,
                e.from_value,
                e.to_value,
                e.detail,
                now,
            )
            for e in events
        ],
    )


def recent_news(
    conn: sqlite3.Connection,
    *,
    limit: int = 20,
    repo_path: Path | None = None,
) -> list[NewsEvent]:
    if repo_path is None:
        rows = conn.execute(
            """
            SELECT n.*, r.name AS repo_name
            FROM news_events n
            LEFT JOIN repos r ON r.path = n.repo_path
            -- Within one refresh every event shares the same `created_at` (one
-- `_now_epoch()` per batch), so we tiebreak with `id ASC` to preserve
-- the insertion order the `news` module uses for priority. `id DESC`
-- would invert that order and make hunger events surface before stage
-- transitions, contradicting the news.py module docstring.
ORDER BY n.created_at DESC, n.id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT n.*, r.name AS repo_name
            FROM news_events n
            LEFT JOIN repos r ON r.path = n.repo_path
            WHERE n.repo_path = ?
            -- Within one refresh every event shares the same `created_at` (one
-- `_now_epoch()` per batch), so we tiebreak with `id ASC` to preserve
-- the insertion order the `news` module uses for priority. `id DESC`
-- would invert that order and make hunger events surface before stage
-- transitions, contradicting the news.py module docstring.
ORDER BY n.created_at DESC, n.id ASC
            LIMIT ?
            """,
            (str(repo_path), limit),
        ).fetchall()
    out: list[NewsEvent] = []
    for row in rows:
        out.append(
            NewsEvent(
                repo_path=Path(row["repo_path"]),
                repo_name=row["repo_name"] or _basename(row["repo_path"]),
                event_type=row["event_type"],
                from_value=row["from_value"],
                to_value=row["to_value"],
                detail=row["detail"],
            )
        )
    return out


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1] or path


# ---------------------------------------------------------------------------
# vitals_history — point-in-time snapshots for sparklines
# ---------------------------------------------------------------------------


def append_vitals_history(
    conn: sqlite3.Connection,
    repo_path: Path,
    vitals: Vitals,
    stage: Stage,
    species: Species,
) -> None:
    conn.execute(
        """
        INSERT INTO vitals_history (repo_path, hunger, health, energy, mood, age_days,
                                    stage, species, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(repo_path),
            vitals.hunger,
            vitals.health,
            vitals.energy,
            vitals.mood,
            vitals.age_days,
            stage.value,
            species.value,
            _now_epoch(),
        ),
    )


def vitals_history(conn: sqlite3.Connection, repo_path: Path, *, limit: int = 20) -> list[Vitals]:
    """Return the most recent `limit` Vitals records for a repo, OLDEST first."""
    rows = conn.execute(
        """
        SELECT hunger, health, energy, mood, age_days
        FROM vitals_history
        WHERE repo_path = ?
        ORDER BY recorded_at DESC
        LIMIT ?
        """,
        (str(repo_path), limit),
    ).fetchall()
    return [
        Vitals(
            hunger=r["hunger"],
            health=r["health"],
            energy=r["energy"],
            mood=r["mood"],
            age_days=r["age_days"],
        )
        for r in reversed(rows)
    ]


def snapshot_current_vitals(conn: sqlite3.Connection) -> dict[str, VitalsSnapshot]:
    """Read the current `vitals_cache` as a snapshot keyed by repo-path string.

    Used by the refresh orchestrator to compare pre- vs post-scan state.
    """
    rows = conn.execute(
        """
        SELECT repo_path, hunger, health, energy, mood, stage
        FROM vitals_cache
        """
    ).fetchall()
    out: dict[str, VitalsSnapshot] = {}
    for row in rows:
        out[row["repo_path"]] = VitalsSnapshot(
            repo_path=Path(row["repo_path"]),
            stage=Stage(row["stage"]),
            hunger=row["hunger"],
            health=row["health"],
            energy=row["energy"],
            mood=row["mood"],
        )
    return out


def repo_name_map(conn: sqlite3.Connection) -> dict[str, str]:
    """Map repo-path strings to short display names — used by news diff rendering."""
    rows = conn.execute("SELECT path, name FROM repos").fetchall()
    return {row["path"]: row["name"] for row in rows}
