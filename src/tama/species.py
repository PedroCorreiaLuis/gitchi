"""Map a repo to a Species based on its primary language."""

from __future__ import annotations

from .models import Repo, Species

_BY_LANGUAGE: dict[str, Species] = {
    "Rust": Species.DRAGON,
    "Python": Species.SNAKE,
    "TypeScript": Species.BLOB,
    "JavaScript": Species.BLOB,
    "Go": Species.GOPHER,
    "Swift": Species.FALCON,
    "Ruby": Species.GEM,
    "GDScript": Species.GHOST_CAT,
    "Markdown": Species.SCROLL,
}


def species_for(repo: Repo) -> Species:
    if repo.primary_language is None:
        return Species.GENERIC_BLOB
    return _BY_LANGUAGE.get(repo.primary_language, Species.GENERIC_BLOB)


def emoji_for(species: Species) -> str:
    return {
        Species.DRAGON: "🐉",
        Species.SNAKE: "🐍",
        Species.BLOB: "🟢",
        Species.GOPHER: "🦫",
        Species.FALCON: "🦅",
        Species.GEM: "💎",
        Species.GHOST_CAT: "👻",
        Species.SCROLL: "📜",
        Species.GENERIC_BLOB: "🟦",
    }[species]
