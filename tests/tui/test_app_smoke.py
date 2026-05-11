"""Smoke tests for the GitchiApp via Textual's Pilot.

These tests verify the app composes, mounts, and responds to bindings without
crashing. They do NOT validate visual layout.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gitchi.models import Config, Pet, Rarity, Repo, Species, Stage, TuiConfig, Vitals


def _pet(name: str, stage: Stage = Stage.ADULT) -> Pet:
    return Pet(
        repo=Repo(
            path=Path(f"/tmp/{name}"),
            name=name,
            primary_language="python",
            first_commit=datetime.now(UTC) - timedelta(days=30),
            last_commit=datetime.now(UTC) - timedelta(days=1),
            commit_count=10,
            size_bytes=1024,
            has_tests=True,
            has_ci=False,
        ),
        species=Species.BLOB,
        stage=stage,
        vitals=Vitals(hunger=70, health=80, energy=60, mood=75, age_days=30),
        rarity=Rarity.COMMON,
    )


@pytest.fixture
def patched_app(monkeypatch: pytest.MonkeyPatch) -> type:
    from gitchi import config as config_mod
    from gitchi import refresh as refresh_mod

    pets = [_pet("alpha"), _pet("beta", stage=Stage.GHOST), _pet("gamma")]
    monkeypatch.setattr(refresh_mod, "list_pets", lambda **_kw: pets)
    monkeypatch.setattr(refresh_mod, "list_recent_news", lambda **_kw: [])
    monkeypatch.setattr(config_mod, "load", lambda: Config(tui=TuiConfig()))
    monkeypatch.setattr(config_mod, "save", lambda _cfg: Path("/tmp/fake-config.toml"))

    # Patch DetailPanel's data loaders so we don't open SQLite or scan the FS.
    from gitchi.tui.widgets import detail_panel as dp

    monkeypatch.setattr(dp.DetailPanel, "_load_history", lambda self, pet: {})
    monkeypatch.setattr(dp.DetailPanel, "_load_play_result", lambda self, pet: None)
    monkeypatch.setattr(dp.DetailPanel, "_safe_todo_count", lambda self, pet: None)

    from gitchi.tui import GitchiApp

    return GitchiApp


async def test_app_mounts_and_renders_pets(patched_app: type) -> None:
    app = patched_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        # 3 pets fixture; ghost is included by default
        assert len(app.visible_pets) == 3


async def test_app_sort_cycles(patched_app: type) -> None:
    app = patched_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.app_state.sort_key == "name"
        await pilot.press("s")
        await pilot.pause()
        assert app.app_state.sort_key == "hunger"
        await pilot.press("s")
        await pilot.pause()
        assert app.app_state.sort_key == "health"


async def test_app_toggle_ghosts(patched_app: type) -> None:
    app = patched_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.app_state.show_ghosts is True
        assert len(app.visible_pets) == 3
        await pilot.press("g")
        await pilot.pause()
        assert app.app_state.show_ghosts is False
        assert len(app.visible_pets) == 2


async def test_app_toggle_animation(patched_app: type) -> None:
    app = patched_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.app_state.animation_enabled is True
        await pilot.press("a")
        await pilot.pause()
        assert app.app_state.animation_enabled is False


async def test_app_search_opens_and_filters(patched_app: type) -> None:
    app = patched_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("slash")
        await pilot.pause()
        # Type "alp"
        for ch in "alp":
            await pilot.press(ch)
        await pilot.pause()
        assert app.app_state.filter_text == "alp"
        assert len(app.visible_pets) == 1
        assert app.visible_pets[0].repo.name == "alpha"


async def test_app_quits_cleanly(patched_app: type) -> None:
    app = patched_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
