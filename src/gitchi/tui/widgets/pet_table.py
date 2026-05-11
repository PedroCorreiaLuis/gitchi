"""DataTable subclass that renders pets through AppState."""

from __future__ import annotations

from textual.widgets import DataTable

from ...models import Pet, Stage
from ...rarity import emoji_for as rarity_emoji_for
from ...species import emoji_for
from ..state import AppState, SortKey, apply_filter, apply_sort

_COLUMNS: tuple[tuple[SortKey, str], ...] = (
    ("name", "NAME"),
    ("rarity", "RARITY"),
    ("hunger", "HUNGER"),
    ("mood", "MOOD"),
    ("age", "AGE"),
)


def _bar(value: int, width: int = 8) -> str:
    """4-shade ramp using shaded blocks for higher contrast than the default 2-shade bar."""
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


class PetTable(DataTable[str]):
    """DataTable that renders a list of pets according to AppState.

    On each `render_pets(pets, state)` call the table is cleared and rebuilt.
    Columns are recreated each render so the active sort key can be marked
    with an arrow without depending on Textual's internal column-mutation API.
    """

    def __init__(self) -> None:
        super().__init__(zebra_stripes=True, cursor_type="row")

    def render_pets(self, pets: list[Pet], state: AppState) -> list[Pet]:
        """Apply state filters/sort to pets, repopulate the table, return the visible list."""
        visible: list[Pet] = list(pets)
        if not state.show_ghosts:
            visible = [p for p in visible if p.stage is not Stage.GHOST]
        if not state.show_buried:
            visible = [p for p in visible if not p.buried]
        visible = apply_filter(visible, state.filter_text)
        visible = apply_sort(visible, state.sort_key, desc=state.sort_desc)

        arrow = "▾" if state.sort_desc else "▴"
        marked_labels: list[str] = []
        for key, label in _COLUMNS:
            marked_labels.append(f"{label}{arrow}" if key == state.sort_key else label)
        marked_labels.append("STATUS")

        self.clear(columns=True)
        self.add_columns(*marked_labels)

        for pet in visible:
            stage_marker = "👻" if pet.stage is Stage.GHOST else pet.stage.value
            self.add_row(
                pet.repo.name,
                f"{rarity_emoji_for(pet.rarity)} {pet.rarity.value}",
                _bar(pet.vitals.hunger),
                _bar(pet.vitals.mood),
                f"{pet.vitals.age_days}d",
                f"{emoji_for(pet.species)} {stage_marker} · {pet.status_word}",
                key=str(pet.repo.path),
            )
        return visible
