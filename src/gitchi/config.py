"""Config file IO. Lives at platformdirs user_config_dir / 'gitchi' / 'config.toml'."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_dir, user_data_dir

from .models import ClaudeConfig, Config, GitHubConfig, ScanConfig, StatsConfig, TuiConfig

APP_NAME = "gitchi"


def config_path() -> Path:
    return Path(user_config_dir(APP_NAME)) / "config.toml"


def data_dir() -> Path:
    p = Path(user_data_dir(APP_NAME))
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "gitchi.db"


def cron_log_path() -> Path:
    return data_dir() / "cron.log"


def load() -> Config:
    """Load config from disk, applying defaults for missing keys."""
    path = config_path()
    if not path.exists():
        return Config()

    with path.open("rb") as f:
        raw = tomllib.load(f)

    return _from_dict(raw)


def save(cfg: Config) -> Path:
    """Persist config to disk, creating parent dirs as needed."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(_to_dict(cfg), f)
    return path


def _from_dict(raw: dict[str, Any]) -> Config:
    scan_raw = raw.get("scan", {}) or {}
    stats_raw = raw.get("stats", {}) or {}
    claude_raw = raw.get("claude", {}) or {}
    github_raw = raw.get("github", {}) or {}
    tui_raw = raw.get("tui", {}) or {}

    weights = stats_raw.get("weights", {}) or {}

    return Config(
        scan=ScanConfig(
            paths=list(scan_raw.get("paths", ScanConfig().paths)),
            depth=int(scan_raw.get("depth", ScanConfig().depth)),
            ignore=list(scan_raw.get("ignore", ScanConfig().ignore)),
        ),
        stats=StatsConfig(
            ghost_after_days=int(stats_raw.get("ghost_after_days", StatsConfig().ghost_after_days)),
            weight_hunger=float(weights.get("hunger", 1.0)),
            weight_health=float(weights.get("health", 1.0)),
            weight_energy=float(weights.get("energy", 1.0)),
            weight_mood=float(weights.get("mood", 1.0)),
        ),
        claude=ClaudeConfig(
            enabled=bool(claude_raw.get("enabled", False)),
            model=str(claude_raw.get("model", ClaudeConfig().model)),
            monthly_token_cap=int(
                claude_raw.get("monthly_token_cap", ClaudeConfig().monthly_token_cap)
            ),
        ),
        github=GitHubConfig(
            enabled=bool(github_raw.get("enabled", False)),
        ),
        tui=TuiConfig(
            theme=str(tui_raw.get("theme", TuiConfig().theme)),
            animation=bool(tui_raw.get("animation", TuiConfig().animation)),
        ),
    )


def _to_dict(cfg: Config) -> dict[str, Any]:
    return {
        "scan": {
            "paths": cfg.scan.paths,
            "depth": cfg.scan.depth,
            "ignore": cfg.scan.ignore,
        },
        "stats": {
            "ghost_after_days": cfg.stats.ghost_after_days,
            "weights": {
                "hunger": cfg.stats.weight_hunger,
                "health": cfg.stats.weight_health,
                "energy": cfg.stats.weight_energy,
                "mood": cfg.stats.weight_mood,
            },
        },
        "claude": {
            "enabled": cfg.claude.enabled,
            "model": cfg.claude.model,
            "monthly_token_cap": cfg.claude.monthly_token_cap,
        },
        "github": {
            "enabled": cfg.github.enabled,
        },
        "tui": {
            "theme": cfg.tui.theme,
            "animation": cfg.tui.animation,
        },
    }


def set_value(cfg: Config, dotted_key: str, value: str) -> Config:
    """Mutate cfg by setting a dotted-key path. Used by `gitchi config set`."""
    parts = dotted_key.split(".")
    if len(parts) != 2:
        raise ValueError(f"expected dotted.key, got {dotted_key!r}")
    section, key = parts

    if section == "scan":
        if key == "paths":
            cfg.scan.paths = [p.strip() for p in value.split(",") if p.strip()]
        elif key == "depth":
            cfg.scan.depth = int(value)
        elif key == "ignore":
            cfg.scan.ignore = [p.strip() for p in value.split(",") if p.strip()]
        else:
            raise KeyError(key)
    elif section == "stats":
        if key == "ghost_after_days":
            cfg.stats.ghost_after_days = int(value)
        else:
            raise KeyError(key)
    elif section == "claude":
        if key == "enabled":
            cfg.claude.enabled = value.lower() in {"1", "true", "yes", "on"}
        elif key == "model":
            cfg.claude.model = value
        elif key == "monthly_token_cap":
            cfg.claude.monthly_token_cap = int(value)
        else:
            raise KeyError(key)
    elif section == "github":
        if key == "enabled":
            cfg.github.enabled = value.lower() in {"1", "true", "yes", "on"}
        else:
            raise KeyError(key)
    elif section == "tui":
        if key == "theme":
            cfg.tui.theme = value
        elif key == "animation":
            cfg.tui.animation = value.lower() in {"1", "true", "yes", "on"}
        else:
            raise KeyError(key)
    else:
        raise KeyError(section)
    return cfg
