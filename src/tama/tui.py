"""Textual dashboard.

Layout:
- Header: project title + counts
- Main: DataTable on the left, Detail panel on the right
- Footer: keybindings
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from . import refresh as refresh_mod
from . import verbs as verbs_mod
from .art import render
from .models import Pet, Stage
from .species import emoji_for


def _bar(value: int, width: int = 12) -> str:
    filled = max(0, min(width, round(value / 100 * width)))
    return f"{'█' * filled}{'░' * (width - filled)}"


class DetailPanel(Static):
    """Right-hand pane that shows the selected pet's art + vitals."""

    def show_pet(self, pet: Pet | None) -> None:
        if pet is None:
            self.update("[dim]no pets — run `tama refresh` to scan.[/dim]")
            return
        lines = [
            f"[bold]{pet.repo.name}[/bold]  {emoji_for(pet.species)} {pet.species.value} · {pet.stage.value}",
            f"[dim]{pet.repo.path}[/dim]",
            "",
            render(pet.species, pet.stage),
            "",
            f"hunger {_bar(pet.vitals.hunger)} {pet.vitals.hunger:3d}",
            f"health {_bar(pet.vitals.health)} {pet.vitals.health:3d}",
            f"energy {_bar(pet.vitals.energy)} {pet.vitals.energy:3d}",
            f"mood   {_bar(pet.vitals.mood)} {pet.vitals.mood:3d}",
            "",
            f"age   {pet.vitals.age_days} days",
            f"state {pet.status_word}",
        ]
        if pet.buried:
            lines.append(
                "[dim italic]buried · " + (pet.bury_reason or "at peace") + "[/dim italic]"
            )
        self.update("\n".join(lines))


class TamaApp(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    DataTable { width: 50%; }
    DetailPanel {
        width: 50%;
        padding: 1 2;
        border: round $primary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "quit"),
        Binding("r", "rescan", "rescan"),
        Binding("f", "feed", "feed"),
        Binding("p", "play", "play"),
        Binding("e", "pet", "edit"),
        Binding("b", "bury", "bury"),
        Binding("v", "revive", "revive"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.pets: list[Pet] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            with Vertical():
                table: DataTable[str] = DataTable(zebra_stripes=True, cursor_type="row")
                table.add_columns("name", "species", "stage", "hunger", "mood", "status")
                yield table
            yield DetailPanel(id="detail")
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "tama"
        self.sub_title = "your codebase as a tamagotchi"
        self._reload()

    def _reload(self) -> None:
        self.pets = refresh_mod.list_pets()
        table = self.query_one(DataTable)
        table.clear()
        for pet in self.pets:
            stage_marker = "👻" if pet.stage is Stage.GHOST else pet.stage.value
            table.add_row(
                pet.repo.name,
                f"{emoji_for(pet.species)} {pet.species.value}",
                stage_marker,
                _bar(pet.vitals.hunger, 8),
                _bar(pet.vitals.mood, 8),
                pet.status_word,
                key=str(pet.repo.path),
            )
        if self.pets:
            self._show_index(0)
        else:
            self.query_one(DetailPanel).show_pet(None)

    def _show_index(self, index: int) -> None:
        if 0 <= index < len(self.pets):
            self.query_one(DetailPanel).show_pet(self.pets[index])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.cursor_row is None:
            return
        self._show_index(event.cursor_row)

    def _selected(self) -> Pet | None:
        table = self.query_one(DataTable)
        if table.cursor_row is None or not self.pets:
            return None
        return self.pets[table.cursor_row]

    def action_rescan(self) -> None:
        summary = refresh_mod.refresh()
        self._reload()
        self.notify(f"rescanned {summary.scanned} repos · {summary.ghosts} ghosts")

    def action_feed(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        hit = verbs_mod.feed(pet.repo.path)
        if hit is None:
            self.notify(f"{pet.repo.name} purrs. no TODOs found.")
        else:
            self.notify(f"{pet.repo.name}: {hit.file.name}:{hit.line} — {hit.message[:60]}")

    def action_play(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        result = verbs_mod.play(pet.repo.path)
        if result is None:
            self.notify(f"{pet.repo.name} has no test runner")
        elif result.returncode == 0:
            self.notify(f"{pet.repo.name} bounces — tests passed")
        else:
            self.notify(
                f"{pet.repo.name} sulks — tests failed (rc={result.returncode})", severity="warning"
            )

    def action_pet(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.pet(pet.repo.path)
        self.notify(f"opened {pet.repo.name} in editor")

    def action_bury(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.bury(pet.repo.path, None)
        self._reload()
        self.notify(f"{pet.repo.name} laid to rest")

    def action_revive(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.revive(pet.repo.path)
        self._reload()
        self.notify(f"{pet.repo.name} stirs")


def run() -> None:
    TamaApp().run()
