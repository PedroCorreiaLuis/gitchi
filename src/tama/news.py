"""Compute notable state-change events between two scans.

`diff_snapshots(before, after)` returns a list of `NewsEvent`. The orchestrator
in `refresh.py` calls this once per refresh, then persists the events via
`store.append_news_events`. The CLI surfaces them via `tama news` and the TUI
shows the most recent ones in a side panel.

Events we surface (in priority order):

- hatched          first time we see a repo → there's a new egg
- evolved          stage advanced (egg → baby → teen → adult → elder)
- became_ghost     stage transitioned to ghost (90+ days of silence)
- revived          stage transitioned OUT of ghost (a buried pet got committed to)
- became_hungry    hunger crossed below the 30-point threshold (was healthy, now not)
- recovered_from_hunger  hunger crossed above 80 after being below it

We intentionally do NOT surface every numeric change — only crossings of named
thresholds. Otherwise the news log would be a wall of noise on every refresh.
"""

from __future__ import annotations

from .models import NewsEvent, Stage, VitalsSnapshot

HUNGER_THRESHOLD = 30
RECOVERY_THRESHOLD = 80


def diff_snapshots(
    before: dict[str, VitalsSnapshot],
    after: dict[str, VitalsSnapshot],
    *,
    name_for: dict[str, str],
) -> list[NewsEvent]:
    """Compare two scan snapshots keyed by string repo-path → list of events.

    `name_for` maps repo_path-strings to short display names so events can be
    rendered as 'coldpipe evolved' rather than a full absolute path.
    """
    events: list[NewsEvent] = []

    for path, current in after.items():
        prev = before.get(path)
        repo_name = name_for.get(path, _basename(path))

        if prev is None:
            events.append(
                NewsEvent(
                    repo_path=current.repo_path,
                    repo_name=repo_name,
                    event_type="hatched",
                    from_value=None,
                    to_value=current.stage.value,
                    detail=f"hatched (egg, {current.stage.value})",
                )
            )
            continue

        events.extend(_stage_events(prev, current, repo_name))
        events.extend(_hunger_events(prev, current, repo_name))

    return events


def _stage_events(prev: VitalsSnapshot, curr: VitalsSnapshot, name: str) -> list[NewsEvent]:
    if prev.stage == curr.stage:
        return []

    if curr.stage is Stage.GHOST:
        return [
            NewsEvent(
                repo_path=curr.repo_path,
                repo_name=name,
                event_type="became_ghost",
                from_value=prev.stage.value,
                to_value=curr.stage.value,
                detail=f"became a ghost ({prev.stage.value} → ghost)",
            )
        ]

    if prev.stage is Stage.GHOST:
        return [
            NewsEvent(
                repo_path=curr.repo_path,
                repo_name=name,
                event_type="revived",
                from_value=prev.stage.value,
                to_value=curr.stage.value,
                detail=f"came back to life ({prev.stage.value} → {curr.stage.value})",
            )
        ]

    order = [Stage.EGG, Stage.BABY, Stage.TEEN, Stage.ADULT, Stage.ELDER]
    if (
        prev.stage in order
        and curr.stage in order
        and order.index(curr.stage) > order.index(prev.stage)
    ):
        return [
            NewsEvent(
                repo_path=curr.repo_path,
                repo_name=name,
                event_type="evolved",
                from_value=prev.stage.value,
                to_value=curr.stage.value,
                detail=f"evolved: {prev.stage.value} → {curr.stage.value}",
            )
        ]
    return []


def _hunger_events(prev: VitalsSnapshot, curr: VitalsSnapshot, name: str) -> list[NewsEvent]:
    if prev.hunger >= HUNGER_THRESHOLD and curr.hunger < HUNGER_THRESHOLD:
        return [
            NewsEvent(
                repo_path=curr.repo_path,
                repo_name=name,
                event_type="became_hungry",
                from_value=str(prev.hunger),
                to_value=str(curr.hunger),
                detail=f"is hungry (hunger {prev.hunger} → {curr.hunger})",
            )
        ]
    if prev.hunger < RECOVERY_THRESHOLD <= curr.hunger:
        return [
            NewsEvent(
                repo_path=curr.repo_path,
                repo_name=name,
                event_type="recovered_from_hunger",
                from_value=str(prev.hunger),
                to_value=str(curr.hunger),
                detail=f"recovered (hunger {prev.hunger} → {curr.hunger})",
            )
        ]
    return []


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1] or path
