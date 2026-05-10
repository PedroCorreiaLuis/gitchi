"""Core data types shared across modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class Species(StrEnum):
    DRAGON = "dragon"
    SNAKE = "snake"
    BLOB = "blob"
    GOPHER = "gopher"
    FALCON = "falcon"
    GEM = "gem"
    GHOST_CAT = "ghost_cat"
    SCROLL = "scroll"
    GENERIC_BLOB = "generic_blob"


class Stage(StrEnum):
    EGG = "egg"
    BABY = "baby"
    TEEN = "teen"
    ADULT = "adult"
    ELDER = "elder"
    GHOST = "ghost"


@dataclass(frozen=True, slots=True)
class Repo:
    path: Path
    name: str
    primary_language: str | None
    first_commit: datetime | None
    last_commit: datetime | None
    commit_count: int
    size_bytes: int
    has_tests: bool
    has_ci: bool


@dataclass(frozen=True, slots=True)
class Vitals:
    hunger: int
    health: int
    energy: int
    mood: int
    age_days: int

    def overall(self) -> int:
        return (self.hunger + self.health + self.energy + self.mood) // 4


@dataclass(frozen=True, slots=True)
class Pet:
    repo: Repo
    species: Species
    stage: Stage
    vitals: Vitals
    buried: bool = False
    bury_reason: str | None = None
    ignored: bool = False

    @property
    def display_name(self) -> str:
        return self.repo.name

    @property
    def status_word(self) -> str:
        if self.ignored:
            return "ignored"
        if self.buried:
            return "buried"
        if self.stage is Stage.GHOST:
            return "haunting"
        score = self.vitals.overall()
        if score >= 80:
            return "thriving"
        if score >= 60:
            return "happy"
        if score >= 40:
            return "content"
        if score >= 20:
            return "hungry"
        return "starving"


@dataclass(frozen=True, slots=True)
class LocalEnergySignals:
    """Local-only signals used to compute Energy when GitHub enrichment is off.

    Each field is a small integer count derived from a single `git` invocation.
    The combiner in stats.py turns these into a 0-100 Energy score.
    """

    uncommitted_files: int  # `git status --porcelain` line count
    stale_local_branches: int  # local branches >30d old that aren't the default
    untracked_dirs: int  # untracked top-level dirs (work hanging around)


@dataclass(frozen=True, slots=True)
class VitalsSnapshot:
    """A point-in-time snapshot of a pet's stage + key vitals.

    Used by `news.diff_snapshots` to compute the events between two scans.
    """

    repo_path: Path
    stage: Stage
    hunger: int
    health: int
    energy: int
    mood: int


@dataclass(frozen=True, slots=True)
class NewsEvent:
    """A single notable transition observed between two scans."""

    repo_path: Path
    repo_name: str
    event_type: str  # 'evolved', 'hatched', 'became_hungry', 'became_ghost',
    # 'revived', 'recovered_from_hunger'
    from_value: str | None
    to_value: str | None
    detail: str  # human-readable summary used by `gitchi news` and refresh output

    @property
    def headline(self) -> str:
        """Pre-formatted single-line headline like '✨ coldpipe evolved: baby → teen'."""
        icon = _EVENT_ICONS.get(self.event_type, "·")
        return f"{icon} {self.repo_name} {self.detail}"


_EVENT_ICONS: dict[str, str] = {
    "evolved": "✨",
    "hatched": "🥚",
    "became_hungry": "🍽",
    "became_ghost": "👻",
    "revived": "💫",
    "recovered_from_hunger": "🌱",
}


@dataclass(slots=True)
class ScanConfig:
    paths: list[str] = field(default_factory=lambda: ["~/"])
    depth: int = 3
    ignore: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".venv",
            "venv",
            "vendor",
            "target",
            ".Trash",
            "Library",
            "build",
            "dist",
            ".tox",
            ".pytest_cache",
        ]
    )


@dataclass(slots=True)
class StatsConfig:
    ghost_after_days: int = 90
    weight_hunger: float = 1.0
    weight_health: float = 1.0
    weight_energy: float = 1.0
    weight_mood: float = 1.0


@dataclass(slots=True)
class ClaudeConfig:
    enabled: bool = False
    model: str = "claude-haiku-4-5-20251001"
    monthly_token_cap: int = 100_000


@dataclass(slots=True)
class GitHubConfig:
    enabled: bool = False


@dataclass(slots=True)
class Config:
    scan: ScanConfig = field(default_factory=ScanConfig)
    stats: StatsConfig = field(default_factory=StatsConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
