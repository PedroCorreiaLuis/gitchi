"""Per-session UI state for the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..models import Pet, Rarity

SortKey = Literal["name", "hunger", "health", "mood", "age", "rarity"]

_SORT_ORDER: tuple[SortKey, ...] = ("name", "hunger", "health", "mood", "age", "rarity")


@dataclass
class AppState:
    """In-memory per-session UI state.

    Theme and `animation_enabled` persist via `config.toml`. Everything here
    that isn't a mirror of config (sort, filter, show toggles, news_collapsed)
    is per-session and resets to defaults on restart.
    """

    sort_key: SortKey = "name"
    sort_desc: bool = False
    filter_text: str = ""
    show_ghosts: bool = True
    show_buried: bool = True
    animation_enabled: bool = True  # mirror of tui.animation in config
    news_collapsed: bool = False


def cycle_sort(current: SortKey) -> SortKey:
    """Return the next sort key in the cycle."""
    idx = _SORT_ORDER.index(current)
    return _SORT_ORDER[(idx + 1) % len(_SORT_ORDER)]


_RARITY_RANK: dict[Rarity, int] = {
    Rarity.COMMON: 0,
    Rarity.UNCOMMON: 1,
    Rarity.RARE: 2,
    Rarity.EPIC: 3,
    Rarity.MYTHIC: 4,
    Rarity.LEGENDARY: 5,
}


def apply_sort(pets: list[Pet], key: SortKey, *, desc: bool) -> list[Pet]:
    """Return a new list of pets sorted by `key` direction `desc`."""

    def keyfn(p: Pet) -> str | int:
        if key == "name":
            return p.repo.name.lower()
        if key == "hunger":
            return p.vitals.hunger
        if key == "health":
            return p.vitals.health
        if key == "mood":
            return p.vitals.mood
        if key == "age":
            return p.vitals.age_days
        if key == "rarity":
            return _RARITY_RANK[p.rarity]
        raise ValueError(f"unknown sort key: {key}")

    return sorted(pets, key=keyfn, reverse=desc)


def apply_filter(pets: list[Pet], text: str) -> list[Pet]:
    """Case-insensitive substring filter on repo name."""
    if not text:
        return list(pets)
    needle = text.casefold()
    return [p for p in pets if needle in p.repo.name.casefold()]
