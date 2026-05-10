"""macOS menu-bar app — shows the most malnourished pets at a glance.

Optional. Install with `pip install -e ".[menubar]"` and run `gitchi-menubar`
or `gitchi menubar run` to launch it. The icon is a small heart that updates
its title with `🐣 N · 👻 M` (alive / ghosts).

This module imports `rumps` lazily so the rest of gitchi works on systems
without it (Linux, CI).
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import refresh as refresh_mod
from . import verbs as verbs_mod
from .models import Pet, Stage
from .species import emoji_for

REFRESH_INTERVAL_SECONDS = 15 * 60
TOP_HUNGRY_LIMIT = 5


def _dashboard_launch_argv() -> list[str]:
    """Build the argv that opens a fresh Terminal window running `gitchi`.

    `open -a Terminal gitchi` would tell macOS to open a *file* named "gitchi"; to
    actually run the CLI we use ``osascript`` to drive Terminal.app's
    ``do script`` directly. We invoke ``sys.executable -m gitchi`` so the new
    shell hits the same Python the menu-bar process is using, rather than
    relying on PATH lookup in the user's default login shell.

    The command string traverses two escaping layers — first a shell layer
    (``shlex.quote``) and then an AppleScript string-literal layer (the
    ``"..."`` of ``do script``). ``shlex.quote`` emits literal ``"`` chars
    whenever the input contains a single-quote (e.g. a username like
    ``o'brien``), so we must additionally escape ``\\`` and ``"`` for the
    AppleScript layer.
    """
    cmd = f"{shlex.quote(sys.executable)} -m gitchi"
    cmd_for_applescript = cmd.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "Terminal" to do script "{cmd_for_applescript}"'
    return ["osascript", "-e", script]


def main() -> None:
    if sys.platform != "darwin":
        print("gitchi menubar is macOS-only; on other platforms run `gitchi` instead.")
        sys.exit(2)
    try:
        import rumps  # type: ignore[import-not-found]
    except ImportError:
        print('rumps is not installed. Install with `pip install -e ".[menubar]"`.')
        sys.exit(2)
    _MenubarApp(rumps).app.run()


class _MenubarApp:
    """Wraps rumps so it can be lazily imported and tested by injection."""

    def __init__(self, rumps_module: Any) -> None:
        self.rumps = rumps_module
        self.app = rumps_module.App("gitchi", title="🐣")
        self.refresh_item = rumps_module.MenuItem("Refresh now", callback=self._refresh)
        self.dashboard_item = rumps_module.MenuItem("Open dashboard", callback=self._open_dashboard)
        self.quit_item = rumps_module.MenuItem("Quit gitchi", callback=self._quit)
        self.app.menu = [self.refresh_item, None, self.dashboard_item, None, self.quit_item]
        self._timer = rumps_module.Timer(self._tick, REFRESH_INTERVAL_SECONDS)
        self._timer.start()
        self._tick(None)

    def _tick(self, _sender: object) -> None:
        try:
            refresh_mod.refresh()
        except Exception:  # noqa: BLE001 — menu-bar must never crash
            return
        pets = refresh_mod.list_pets()
        self._render(pets)

    def _render(self, pets: list[Pet]) -> None:
        alive = [p for p in pets if p.stage is not Stage.GHOST and not p.buried]
        ghosts = [p for p in pets if p.stage is Stage.GHOST and not p.buried]
        self.app.title = f"🐣 {len(alive)} · 👻 {len(ghosts)}"

        # Replace dynamic items: clear keys after the static head and re-add.
        static_keys = {"Refresh now", "Open dashboard", "Quit gitchi"}
        for key in list(self.app.menu.keys()):
            if key in static_keys or key is None:
                continue
            del self.app.menu[key]

        hungry = sorted(alive, key=lambda p: p.vitals.hunger)[:TOP_HUNGRY_LIMIT]
        if hungry:
            self.app.menu.insert_before("Refresh now", self.rumps.MenuItem("— hungriest —"))
            for pet in hungry:
                title = f"{emoji_for(pet.species)} {pet.repo.name}  hunger {pet.vitals.hunger}"
                item = self.rumps.MenuItem(title, callback=self._make_feed_handler(pet.repo.path))
                self.app.menu.insert_before("Refresh now", item)
            self.app.menu.insert_before("Refresh now", self.rumps.separator)

    def _make_feed_handler(self, repo_path: Path) -> Any:
        def handler(_sender: object) -> None:
            hit = verbs_mod.feed(repo_path)
            if hit is None:
                self.rumps.notification("gitchi", repo_path.name, "purrs. no TODOs found.")
            else:
                self.rumps.notification(
                    "gitchi",
                    repo_path.name,
                    f"{hit.file.name}:{hit.line} — {hit.message[:80]}",
                )

        return handler

    def _refresh(self, _sender: object) -> None:
        self._tick(_sender)

    def _open_dashboard(self, _sender: object) -> None:
        subprocess.Popen(_dashboard_launch_argv())

    def _quit(self, _sender: object) -> None:
        self.rumps.quit_application()
