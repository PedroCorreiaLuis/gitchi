"""News panel widget — most recent state transitions."""

from __future__ import annotations

from textual.widgets import Static

from ...models import NewsEvent

NEWS_PANEL_LIMIT = 6


class NewsPanel(Static):
    """Footer-area panel showing the latest state-change events."""

    def show_events(self, events: list[NewsEvent]) -> None:
        if not events:
            self.update("[dim]news: (rescan to start tracking)[/dim]")
            return
        lines = ["[bold]news[/bold]"]
        for event in events[:NEWS_PANEL_LIMIT]:
            lines.append(f"  {event.headline}")
        self.update("\n".join(lines))
