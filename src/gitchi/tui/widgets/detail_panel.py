"""Detail panel widget — selected pet's art and vitals."""

from __future__ import annotations

from textual.widgets import Static

from ...art import render
from ...models import Pet
from ...rarity import emoji_for as rarity_emoji_for
from ...species import emoji_for


def _bar(value: int, width: int = 12) -> str:
    filled = max(0, min(width, round(value / 100 * width)))
    return f"{'█' * filled}{'░' * (width - filled)}"


class DetailPanel(Static):
    """Right-hand pane that shows the selected pet's art + vitals."""

    def show_pet(self, pet: Pet | None) -> None:
        if pet is None:
            self.update("[dim]no pets — run `gitchi refresh` to scan.[/dim]")
            return
        rarity_tag = f"{rarity_emoji_for(pet.rarity)} {pet.rarity.value}"
        lines = [
            f"[bold]{pet.repo.name}[/bold]  {emoji_for(pet.species)} {pet.species.value} · "
            f"{pet.stage.value} · {rarity_tag}",
            f"[dim]{pet.repo.path}[/dim]",
            "",
            render(pet.species, pet.stage),
            "",
            f"hunger {_bar(pet.vitals.hunger)} {pet.vitals.hunger:3d}",
            f"health {_bar(pet.vitals.health)} {pet.vitals.health:3d}",
            f"energy {_bar(pet.vitals.energy)} {pet.vitals.energy:3d}",
            f"mood   {_bar(pet.vitals.mood)} {pet.vitals.mood:3d}",
            "",
            f"age    {pet.vitals.age_days} days",
            f"rarity {rarity_tag}",
            f"state  {pet.status_word}",
        ]
        if pet.ignored:
            lines.append("[dim italic]ignored[/dim italic]")
        elif pet.buried:
            lines.append(
                "[dim italic]buried · " + (pet.bury_reason or "at peace") + "[/dim italic]"
            )
        self.update("\n".join(lines))
