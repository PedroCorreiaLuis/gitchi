"""Allow `python -m tama ...` invocation (used by the launchd plist)."""

from .cli import app

if __name__ == "__main__":
    app()
