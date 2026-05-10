"""Menubar helpers — pure-function tests that don't require rumps."""

from __future__ import annotations

import sys

from tama.menubar import _dashboard_launch_argv


def test_dashboard_launch_argv_uses_osascript() -> None:
    """Regression: must use AppleScript `do script`, not `open -a Terminal tama`.

    `open -a Terminal tama` would ask macOS to open a *file* named "tama" in
    Terminal.app, which is a no-op at best. The correct invocation is
    osascript driving Terminal.app's `do script` to actually run a command.
    """
    argv = _dashboard_launch_argv()
    assert argv[0] == "osascript"
    assert argv[1] == "-e"
    script = argv[2]
    assert script.startswith('tell application "Terminal"')
    assert "do script" in script
    # The shell command embedded in the AppleScript must reference our
    # Python interpreter so PATH lookup in the new shell doesn't matter.
    assert sys.executable in script
    assert "-m tama" in script


def test_dashboard_launch_argv_quotes_executable_with_spaces(monkeypatch) -> None:
    """A python path with spaces must survive shell quoting."""
    monkeypatch.setattr("tama.menubar.sys.executable", "/Users/pedro alpha/.venv/bin/python")
    argv = _dashboard_launch_argv()
    script = argv[2]
    # Single-quoted by shlex; the literal `pedro alpha` substring must appear.
    assert "'/Users/pedro alpha/.venv/bin/python'" in script
