"""Generate and install a launchd plist that refreshes gitchi nightly.

macOS only. The plist runs `<python> -m gitchi refresh` at 03:30 every day,
logging stdout/stderr to ~/.local/share/gitchi/cron.log.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from .config import cron_log_path

LABEL = "com.gitchi.refresh"


def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def render_plist(python: str | None = None, hour: int = 3, minute: int = 30) -> str:
    py = python or sys.executable or shutil.which("python3") or "/usr/bin/env python3"
    log = cron_log_path()
    return dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
            "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>{LABEL}</string>
            <key>ProgramArguments</key>
            <array>
                <string>{py}</string>
                <string>-m</string>
                <string>gitchi</string>
                <string>refresh</string>
            </array>
            <key>StartCalendarInterval</key>
            <dict>
                <key>Hour</key>
                <integer>{hour}</integer>
                <key>Minute</key>
                <integer>{minute}</integer>
            </dict>
            <key>RunAtLoad</key>
            <false/>
            <key>StandardOutPath</key>
            <string>{log}</string>
            <key>StandardErrorPath</key>
            <string>{log}</string>
        </dict>
        </plist>
        """
    )


def install(hour: int = 3, minute: int = 30) -> Path:
    path = plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_plist(hour=hour, minute=minute), encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(path)], capture_output=True, check=False)
    subprocess.run(["launchctl", "load", str(path)], capture_output=True, check=False)
    return path


def uninstall() -> bool:
    path = plist_path()
    if not path.exists():
        return False
    subprocess.run(["launchctl", "unload", str(path)], capture_output=True, check=False)
    path.unlink()
    return True
