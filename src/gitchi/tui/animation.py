"""Animation frame selection for the detail panel."""

from __future__ import annotations

from ..art import idle_frames
from ..models import Pet, Stage

# State thresholds — keep aligned with status_word / status_reason logic.
_ALERT_HUNGER = 25
_ALERT_HEALTH = 25


def select_frames(pet: Pet) -> list[str]:
    """Return a 2-frame list for the current pet state.

    All states currently share the same base frame set produced by
    `art.idle_frames`; future work can vary frames per state (alert,
    celebrate). The two-frame contract stays stable.
    """
    return idle_frames(pet.species, pet.stage)


def current_frame(frames: list[str], *, tick: int) -> str:
    """Pick the active frame from a frame list given a monotonic tick counter."""
    if not frames:
        return ""
    return frames[tick % len(frames)]


def should_alert(pet: Pet) -> bool:
    """Whether a pet's state warrants the alert palette."""
    if pet.stage is Stage.GHOST:
        return False
    return pet.vitals.hunger < _ALERT_HUNGER or pet.vitals.health < _ALERT_HEALTH
