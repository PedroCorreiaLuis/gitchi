"""Human-readable 'why' for each pet status word.

Parallels the threshold logic in `Pet.status_word`; both should be kept in
sync (changes in one require updating the other).
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..models import Pet, Stage


def _days_since_commit(pet: Pet) -> int | None:
    last = pet.repo.last_commit
    if last is None:
        return None
    now = datetime.now(UTC)
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return max(0, (now - last).days)


def derive_reason(pet: Pet) -> str:
    if pet.ignored:
        return "ignored"
    if pet.buried:
        return f"buried · {pet.bury_reason or 'at peace'}"
    if pet.stage is Stage.GHOST:
        days = _days_since_commit(pet)
        if days is None:
            return "ghost · no commit history"
        return f"ghost · {days}d dormant"

    score = pet.vitals.overall()
    days = _days_since_commit(pet)
    suffix = f" · {days}d since commit" if days is not None and days > 0 else ""

    if score >= 80:
        return f"thriving{suffix}"
    if score >= 60:
        return f"happy{suffix}"
    if score >= 40:
        return f"content{suffix}"
    if score >= 20:
        return f"hungry{suffix}"
    return f"starving{suffix}"
