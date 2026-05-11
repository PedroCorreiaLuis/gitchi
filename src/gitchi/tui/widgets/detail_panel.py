"""Detail panel — animated pet art, sparklines, vital bars, status reason, badges."""

from __future__ import annotations

from datetime import UTC, datetime

from textual.widgets import Static

from ...config import db_path
from ...history import sparkline
from ...models import Pet
from ...rarity import emoji_for as rarity_emoji_for
from ...species import emoji_for
from ...store import connect, last_play_result, vitals_history
from ...verbs import count_todos
from ..animation import current_frame, select_frames, should_alert
from ..status_reason import derive_reason

_BAR_WIDTH = 8
_SPARK_WIDTH = 7
_FRAME_CHAR = "▓"
_FRAME_WIDTH = 18


def _ramp_bar(value: int, width: int = _BAR_WIDTH) -> str:
    """4-shade ramp using █▓▒░."""
    if width <= 0:
        return ""
    pct = max(0, min(100, value)) / 100
    full = int(pct * width)
    remainder = (pct * width) - full
    ramp = "░▒▓█"
    cells = ["█"] * full
    if full < width:
        idx = int(remainder * (len(ramp) - 1))
        cells.append(ramp[idx])
        cells.extend(["░"] * (width - full - 1))
    return "".join(cells)


def _wrap_art(art: str, width: int = _FRAME_WIDTH) -> str:
    """Wrap the art block in a 4-shade frame for CRT vibes.

    Strips the common leading-whitespace prefix from all non-empty lines
    so the art's baked-in indentation doesn't compound with the frame's
    centering. Then centers the block as a whole.
    """
    horizontal = _FRAME_CHAR * width
    inner_width = max(0, width - 2)
    raw_lines = art.splitlines() or [""]

    non_empty = [line for line in raw_lines if line.strip()]
    common = min((len(line) - len(line.lstrip(" ")) for line in non_empty), default=0)
    art_lines = [line[common:] if line.strip() else "" for line in raw_lines]

    block_width = min(inner_width, max((len(line) for line in art_lines), default=0))
    left_pad = max(0, (inner_width - block_width) // 2)
    right_pad_total = inner_width - block_width - left_pad

    lines = [horizontal]
    for line in art_lines:
        if inner_width == 0:
            lines.append(horizontal)
            continue
        body = line[:block_width].ljust(block_width)
        padded = f"{' ' * left_pad}{body}{' ' * right_pad_total}"
        lines.append(f"{_FRAME_CHAR}{padded}{_FRAME_CHAR}")
    lines.append(horizontal)
    return "\n".join(lines)


class DetailPanel(Static):
    """Pet detail with animation tick + sparklines + badges.

    External callers drive animation:
        panel.show_pet(pet)            # loads data, renders frame 0
        panel.tick(animation_enabled)  # advances tick + re-renders if enabled
    """

    def __init__(self) -> None:
        super().__init__()
        self._pet: Pet | None = None
        self._tick = 0
        self._frames: list[str] = []
        self._history: dict[str, list[int]] = {}
        self._todo_count: int | None = None
        self._play_result: tuple[int, int] | None = None
        self._todo_cache: dict[str, int] = {}

    def clear_todo_cache(self) -> None:
        """Invalidate cached todo counts (called on rescan)."""
        self._todo_cache.clear()

    def show_pet(self, pet: Pet | None) -> None:
        self._pet = pet
        self._tick = 0
        if pet is None:
            self._frames = []
            self._history = {}
            self._todo_count = None
            self._play_result = None
            self.update("[dim]no pets — run `gitchi refresh` to scan.[/dim]")
            return

        self._frames = select_frames(pet)
        self._history = self._load_history(pet)
        self._todo_count = self._safe_todo_count(pet)
        self._play_result = self._load_play_result(pet)
        self.refresh_render()

    def tick(self, animation_enabled: bool) -> None:
        """Advance the frame tick. Called by the App's set_interval driver."""
        if self._pet is None or not self._frames:
            return
        if animation_enabled:
            self._tick += 1
            self.refresh_render()

    def refresh_render(self) -> None:
        pet = self._pet
        if pet is None:
            return

        rarity_tag = f"{rarity_emoji_for(pet.rarity)} {pet.rarity.value}"
        title = (
            f"[bold]{pet.repo.name}[/bold]  {emoji_for(pet.species)} {pet.species.value} · "
            f"{pet.stage.value} · {rarity_tag}"
        )

        frame = current_frame(self._frames, tick=self._tick)
        framed_art = _wrap_art(frame)

        alert_active = should_alert(pet)

        def vital_line(name: str, value: int, samples: list[int]) -> str:
            sparkline_str = sparkline(samples, width=_SPARK_WIDTH)
            bar = _ramp_bar(value)
            raw = f"{name:<6} {sparkline_str}  {bar} {value:3d}"
            if alert_active and name in ("hunger", "health") and value < 25:
                return f"[bold red]{raw}[/bold red]"
            return raw

        hist = self._history
        body_lines = [
            title,
            f"[dim]{pet.repo.path}[/dim]",
            "",
            framed_art,
            "",
            vital_line("hunger", pet.vitals.hunger, hist.get("hunger", [])),
            vital_line("health", pet.vitals.health, hist.get("health", [])),
            vital_line("energy", pet.vitals.energy, hist.get("energy", [])),
            vital_line("mood", pet.vitals.mood, hist.get("mood", [])),
            "",
            derive_reason(pet),
            self._badge_line(pet),
        ]
        self.update("\n".join(body_lines))

    # ------------------------------------------------------------------ data

    def _load_history(self, pet: Pet) -> dict[str, list[int]]:
        try:
            with connect(db_path()) as conn:
                rows = vitals_history(conn, pet.repo.path, limit=_SPARK_WIDTH)
        except Exception:
            return {}
        return {
            "hunger": [v.hunger for v in rows],
            "health": [v.health for v in rows],
            "energy": [v.energy for v in rows],
            "mood": [v.mood for v in rows],
        }

    def _load_play_result(self, pet: Pet) -> tuple[int, int] | None:
        try:
            with connect(db_path()) as conn:
                return last_play_result(conn, pet.repo.path)
        except Exception:
            return None

    def _safe_todo_count(self, pet: Pet) -> int | None:
        key = str(pet.repo.path)
        if key in self._todo_cache:
            return self._todo_cache[key]
        try:
            count = count_todos(pet.repo.path)
        except Exception:
            return None
        self._todo_cache[key] = count
        return count

    def _badge_line(self, pet: Pet) -> str:
        parts: list[str] = []
        if self._todo_count is not None and self._todo_count > 0:
            parts.append(f"todo {self._todo_count}")
        if self._play_result is not None:
            rc, ran_at = self._play_result
            tick = "✓" if rc == 0 else "✗"
            age = self._fmt_age(ran_at)
            parts.append(f"ci {tick} ({age})")
        else:
            parts.append("ci —")
        parts.append(f"age {pet.vitals.age_days}d")
        return " · ".join(parts)

    @staticmethod
    def _fmt_age(epoch_seconds: int) -> str:
        delta_s = datetime.now(UTC).timestamp() - epoch_seconds
        if delta_s < 60:
            return f"{int(delta_s)}s"
        if delta_s < 3600:
            return f"{int(delta_s / 60)}m"
        if delta_s < 86400:
            return f"{int(delta_s / 3600)}h"
        return f"{int(delta_s / 86400)}d"
