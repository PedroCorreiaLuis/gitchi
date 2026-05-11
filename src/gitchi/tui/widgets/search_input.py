"""Search input overlay — live-filters the pet table."""

from __future__ import annotations

from textual.binding import Binding
from textual.message import Message
from textual.widgets import Input


class SearchInput(Input):
    """Single-line input that emits FilterChanged on every keystroke.

    Pressing Esc clears the value, emits FilterChanged with the empty string,
    and emits Closed (so the app can hide the overlay and re-focus the table).
    """

    BINDINGS = [Binding("escape", "close", "close", show=False)]

    class FilterChanged(Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class Closed(Message):
        pass

    def __init__(self) -> None:
        super().__init__(placeholder="filter by name…")

    def on_input_changed(self, event: Input.Changed) -> None:
        self.post_message(self.FilterChanged(event.value))

    def action_close(self) -> None:
        self.value = ""
        self.post_message(self.FilterChanged(""))
        self.post_message(self.Closed())
