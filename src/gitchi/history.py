"""Vitals time-series history + sparkline rendering.

Every `gitchi refresh` writes one row per pet to `vitals_history`. `gitchi show`
reads the last N rows for a pet and renders a sparkline so you can see whether
its hunger / health / energy / mood is trending up or down.

Sparkline encoding uses Unicode block elements `▁▂▃▄▅▆▇█` — eight discrete
levels. A `None` slot in the input is rendered as a single space, which keeps
the sparkline width stable even when the history is short.
"""

from __future__ import annotations

from collections.abc import Sequence

_LEVELS = "▁▂▃▄▅▆▇█"
_LEVEL_COUNT = len(_LEVELS)
_EMPTY_SLOT = " "

DEFAULT_HISTORY_LEN = 20


def sparkline(values: Sequence[int | None], *, width: int = DEFAULT_HISTORY_LEN) -> str:
    """Render up to `width` integer values (0-100) as a Unicode sparkline.

    Older values are padded out with empty slots on the LEFT so the line is
    right-aligned, i.e. newest sample is always the rightmost character.
    """
    bounded = list(values)[-width:]
    pad = width - len(bounded)
    cells: list[str] = [_EMPTY_SLOT] * pad
    for v in bounded:
        if v is None:
            cells.append(_EMPTY_SLOT)
            continue
        clipped = max(0, min(100, int(v)))
        bucket = min(_LEVEL_COUNT - 1, clipped * _LEVEL_COUNT // 100)
        cells.append(_LEVELS[bucket])
    return "".join(cells)
