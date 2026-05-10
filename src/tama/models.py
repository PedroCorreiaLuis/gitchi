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

    @property
    def display_name(self) -> str:
        return self.repo.name

    @property
    def status_word(self) -> str:
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
