"""Tests for tui/state.py."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from gitchi.models import Pet, Rarity, Repo, Species, Stage, Vitals
from gitchi.tui.state import AppState, SortKey, apply_filter, apply_sort, cycle_sort


def _pet(name: str, hunger: int = 50, health: int = 50, mood: int = 50, age: int = 1) -> Pet:
    return Pet(
        repo=Repo(
            path=Path(f"/tmp/{name}"),
            name=name,
            primary_language=None,
            first_commit=None,
            last_commit=None,
            commit_count=0,
            size_bytes=0,
            has_tests=False,
            has_ci=False,
        ),
        species=Species.GENERIC_BLOB,
        stage=Stage.BABY,
        vitals=Vitals(hunger=hunger, health=health, energy=50, mood=mood, age_days=age),
        rarity=Rarity.COMMON,
    )


def test_default_state() -> None:
    s = AppState()
    assert s.sort_key == "name"
    assert s.sort_desc is False
    assert s.filter_text == ""
    assert s.show_ghosts is True
    assert s.show_buried is True
    assert s.animation_enabled is True
    assert s.news_collapsed is False


def test_cycle_sort_advances_through_keys() -> None:
    seq: list[SortKey] = []
    key: SortKey = "name"
    for _ in range(7):
        key = cycle_sort(key)
        seq.append(key)
    assert seq == ["hunger", "health", "mood", "age", "rarity", "name", "hunger"]


def test_apply_sort_name_ascending() -> None:
    pets = [_pet("b"), _pet("a"), _pet("c")]
    out = apply_sort(pets, "name", desc=False)
    assert [p.repo.name for p in out] == ["a", "b", "c"]


def test_apply_sort_hunger_descending() -> None:
    pets = [_pet("a", hunger=10), _pet("b", hunger=90), _pet("c", hunger=50)]
    out = apply_sort(pets, "hunger", desc=True)
    assert [p.repo.name for p in out] == ["b", "c", "a"]


def test_apply_sort_age_descending() -> None:
    pets = [_pet("a", age=1), _pet("b", age=10), _pet("c", age=5)]
    out = apply_sort(pets, "age", desc=True)
    assert [p.repo.name for p in out] == ["b", "c", "a"]


def test_apply_filter_substring_case_insensitive() -> None:
    pets = [_pet("Rasteira"), _pet("gitchi"), _pet("coldpipe")]
    out = apply_filter(pets, "TCH")
    assert [p.repo.name for p in out] == ["gitchi"]


def test_apply_filter_empty_returns_all() -> None:
    pets = [_pet("a"), _pet("b")]
    out = apply_filter(pets, "")
    assert len(out) == 2


def test_replace_preserves_other_fields() -> None:
    s = AppState(sort_key="mood", show_ghosts=False)
    s2 = replace(s, filter_text="ras")
    assert s2.sort_key == "mood"
    assert s2.show_ghosts is False
    assert s2.filter_text == "ras"
