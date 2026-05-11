"""Textual dashboard.

Layout: optional search bar overlay on top · two-pane body (PetTable left,
DetailPanel right) · collapsible NewsPanel · footer. Per-session state is
held in `AppState`; theme CSS is rendered from `themes.render_css` at
startup and applied via the App stylesheet.
"""

from __future__ import annotations

import contextlib

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer

from .. import config as config_mod
from .. import refresh as refresh_mod
from .. import verbs as verbs_mod
from ..models import Pet
from .state import AppState, cycle_sort
from .themes import get_theme, render_css
from .widgets.detail_panel import DetailPanel
from .widgets.news_panel import NEWS_PANEL_LIMIT, NewsPanel
from .widgets.pet_table import PetTable
from .widgets.search_input import SearchInput


class GitchiApp(App[None]):
    BINDINGS = [
        Binding("q", "quit", "quit"),
        Binding("r", "rescan", "rescan"),
        Binding("f", "feed", "feed"),
        Binding("p", "play", "play"),
        Binding("e", "pet", "edit"),
        Binding("b", "bury", "bury"),
        Binding("v", "revive", "revive"),
        Binding("i", "ignore", "ignore"),
        Binding("u", "unignore", "unignore"),
        Binding("slash", "open_search", "search", key_display="/"),
        Binding("s", "sort", "sort"),
        Binding("S", "sort_reverse", "sort↓", show=False),
        Binding("g", "toggle_ghosts", "ghosts"),
        Binding("B", "toggle_buried", "buried"),
        Binding("n", "toggle_news", "news"),
        Binding("a", "toggle_animation", "anim"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.pets: list[Pet] = []
        self.visible_pets: list[Pet] = []
        self.app_state = AppState()
        self.cfg = config_mod.load()
        self.app_state.animation_enabled = self.cfg.tui.animation
        self.theme_css = render_css(get_theme(self.cfg.tui.theme))

    def compose(self) -> ComposeResult:
        yield SearchInput()
        with Horizontal(id="body"):
            yield PetTable()
            yield DetailPanel()
        yield NewsPanel()
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "gitchi"
        self.sub_title = "your codebase as a tamagotchi"
        # Apply theme CSS at runtime. Use `stylesheet.add_source` if available,
        # otherwise fall through silently — default Textual styling still works.
        with contextlib.suppress(Exception):
            self.stylesheet.add_source(self.theme_css)
            self.stylesheet.parse()

        # Hide the search overlay until `/` is pressed.
        search = self.query_one(SearchInput)
        search.add_class("hidden")

        self._reload()
        # Focus the pet table so global key bindings fire — otherwise the
        # hidden SearchInput steals focus on mount (Textual auto-focuses the
        # first focusable widget) and consumes every keystroke as input text.
        self.query_one(PetTable).focus()
        self.set_interval(0.5, self._tick)

    # ---------------------------------------------------------------- data

    def _reload(self) -> None:
        self.pets = refresh_mod.list_pets()
        self._render_table()
        self.query_one(NewsPanel).show_events(
            refresh_mod.list_recent_news(limit=NEWS_PANEL_LIMIT)
        )

    def _render_table(self) -> None:
        table = self.query_one(PetTable)
        self.visible_pets = table.render_pets(self.pets, self.app_state)
        if self.visible_pets:
            self._show_index(0)
        else:
            self.query_one(DetailPanel).show_pet(None)

    def _show_index(self, index: int) -> None:
        if 0 <= index < len(self.visible_pets):
            self.query_one(DetailPanel).show_pet(self.visible_pets[index])

    def _selected(self) -> Pet | None:
        table = self.query_one(PetTable)
        cursor = table.cursor_row
        if cursor is None or not self.visible_pets:
            return None
        if cursor >= len(self.visible_pets):
            return None
        return self.visible_pets[cursor]

    # ---------------------------------------------------------------- events

    def on_data_table_row_highlighted(self, event: PetTable.RowHighlighted) -> None:
        if event.cursor_row is None:
            return
        self._show_index(event.cursor_row)

    def on_search_input_filter_changed(self, event: SearchInput.FilterChanged) -> None:
        self.app_state.filter_text = event.text
        self._render_table()

    def on_search_input_closed(self, _event: SearchInput.Closed) -> None:
        search = self.query_one(SearchInput)
        search.add_class("hidden")
        self.query_one(PetTable).focus()

    def _tick(self) -> None:
        detail = self.query_one(DetailPanel)
        detail.tick(self.app_state.animation_enabled)

    # ---------------------------------------------------------------- actions

    def action_rescan(self) -> None:
        summary = refresh_mod.refresh()
        self.query_one(DetailPanel).clear_todo_cache()
        self._reload()
        suffix = f" · {len(summary.news_events)} news" if summary.news_events else ""
        self.notify(f"rescanned {summary.scanned} repos · {summary.ghosts} ghosts{suffix}")

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
                f"{pet.repo.name} sulks — tests failed (rc={result.returncode})",
                severity="warning",
            )
        # Refresh detail panel to update the CI badge.
        self.query_one(DetailPanel).show_pet(pet)

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

    def action_ignore(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.ignore(pet.repo.path, None)
        self._reload()
        self.notify(f"{pet.repo.name} ignored")

    def action_unignore(self) -> None:
        pet = self._selected()
        if pet is None:
            return
        verbs_mod.unignore(pet.repo.path)
        self._reload()
        self.notify(f"{pet.repo.name} is visible again")

    def action_open_search(self) -> None:
        search = self.query_one(SearchInput)
        search.remove_class("hidden")
        search.focus()

    def action_sort(self) -> None:
        self.app_state.sort_key = cycle_sort(self.app_state.sort_key)
        self.app_state.sort_desc = False
        self._render_table()
        self.notify(f"sort: {self.app_state.sort_key}")

    def action_sort_reverse(self) -> None:
        self.app_state.sort_desc = not self.app_state.sort_desc
        self._render_table()
        arrow = "↓" if self.app_state.sort_desc else "↑"
        self.notify(f"sort: {self.app_state.sort_key} {arrow}")

    def action_toggle_ghosts(self) -> None:
        self.app_state.show_ghosts = not self.app_state.show_ghosts
        self._render_table()

    def action_toggle_buried(self) -> None:
        self.app_state.show_buried = not self.app_state.show_buried
        self._render_table()

    def action_toggle_news(self) -> None:
        self.app_state.news_collapsed = not self.app_state.news_collapsed
        news = self.query_one(NewsPanel)
        if self.app_state.news_collapsed:
            news.add_class("collapsed")
        else:
            news.remove_class("collapsed")

    def action_toggle_animation(self) -> None:
        self.app_state.animation_enabled = not self.app_state.animation_enabled
        self.cfg.tui.animation = self.app_state.animation_enabled
        with contextlib.suppress(Exception):
            config_mod.save(self.cfg)
        state_label = "on" if self.app_state.animation_enabled else "off"
        self.notify(f"animation {state_label}")


def run() -> None:
    GitchiApp().run()


# Keep these names importable from `gitchi.tui` for back-compat with cli.py.
__all__ = [
    "DetailPanel",
    "GitchiApp",
    "NEWS_PANEL_LIMIT",
    "NewsPanel",
    "PetTable",
    "run",
]
