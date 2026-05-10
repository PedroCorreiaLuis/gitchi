"""Tests for the ignore / unignore feature."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tama.models import Repo, Species, Stage, Vitals
from tama.store import (
    all_pets,
    connect,
    get_pet,
    ignore,
    is_ignored,
    unignore,
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
        commit_count=20,
        size_bytes=1024,
        has_tests=True,
        has_ci=True,
    )


def _vitals() -> Vitals:
    return Vitals(hunger=80, health=70, energy=60, mood=50, age_days=120)


def test_ignored_pet_is_hidden_from_default_list(tmp_path: Path) -> None:
    db = tmp_path / "x.db"
    repo = _repo(tmp_path / "alpha")
    with connect(db) as conn:
        upsert_repo(conn, repo)
        upsert_vitals(conn, repo.path, _vitals(), Stage.ADULT, Species.SNAKE)
        ignore(conn, repo.path, "vendored fork")
        assert all_pets(conn) == []
        assert len(all_pets(conn, include_ignored=True)) == 1


def test_get_pet_still_finds_ignored(tmp_path: Path) -> None:
    """`tama show <name>` should still resolve an ignored pet — the user asked for it directly."""
    db = tmp_path / "x.db"
    repo = _repo(tmp_path / "beta")
    with connect(db) as conn:
        upsert_repo(conn, repo)
        upsert_vitals(conn, repo.path, _vitals(), Stage.TEEN, Species.BLOB)
        ignore(conn, repo.path, None)
        pet = get_pet(conn, repo.path)
        assert pet is not None
        assert pet.ignored is True
        assert pet.status_word == "ignored"


def test_unignore_makes_pet_visible_again(tmp_path: Path) -> None:
    db = tmp_path / "x.db"
    repo = _repo(tmp_path / "gamma")
    with connect(db) as conn:
        upsert_repo(conn, repo)
        upsert_vitals(conn, repo.path, _vitals(), Stage.BABY, Species.GOPHER)
        ignore(conn, repo.path, None)
        assert is_ignored(conn, repo.path) is True
        unignore(conn, repo.path)
        assert is_ignored(conn, repo.path) is False
        assert len(all_pets(conn)) == 1
