"""Species mapping tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tama.models import Repo, Species
from tama.species import emoji_for, species_for


def _r(lang: str | None) -> Repo:
    return Repo(
        path=Path("/tmp/x"),
        name="x",
        primary_language=lang,
        first_commit=datetime(2025, 1, 1, tzinfo=UTC),
        last_commit=datetime(2025, 1, 1, tzinfo=UTC),
        commit_count=1,
        size_bytes=0,
        has_tests=False,
        has_ci=False,
    )


def test_known_languages_map_correctly() -> None:
    assert species_for(_r("Rust")) is Species.DRAGON
    assert species_for(_r("Python")) is Species.SNAKE
    assert species_for(_r("TypeScript")) is Species.BLOB
    assert species_for(_r("JavaScript")) is Species.BLOB
    assert species_for(_r("Go")) is Species.GOPHER
    assert species_for(_r("Swift")) is Species.FALCON
    assert species_for(_r("Ruby")) is Species.GEM
    assert species_for(_r("GDScript")) is Species.GHOST_CAT
    assert species_for(_r("Markdown")) is Species.SCROLL


def test_unknown_falls_back_to_generic() -> None:
    assert species_for(_r("Brainfuck")) is Species.GENERIC_BLOB
    assert species_for(_r(None)) is Species.GENERIC_BLOB


def test_every_species_has_an_emoji() -> None:
    for sp in Species:
        assert emoji_for(sp), f"missing emoji for {sp}"
