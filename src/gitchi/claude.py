"""Optional Mood enrichment via the Anthropic Messages API.

We sample the last 30 commit messages from a repo, hash them as the cache key,
and ask Claude to score the developer's emotional tone 0–100 (0 = exhausted /
frustrated / despairing, 100 = energised / proud / playful). The system prompt
is reused across repos and benefits from prompt caching.

Hard guardrails:
- Disabled by default; requires `claude.enabled = true` and ANTHROPIC_API_KEY.
- Monthly token cap from config; we refuse to call past it.
- Per-repo caching keyed on the message-set hash so identical history is a
  single API call. Cache lives in `mood_cache` (see store.py).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import db_path
from .models import ClaudeConfig
from .store import connect, get_meta, get_mood, set_meta, upsert_mood

SYSTEM_PROMPT = """\
You score the emotional tone of a developer based on the last commit messages
of one of their git repositories. Output a single integer 0-100 with no other
text. 0 means exhausted, frustrated, or despairing. 50 means neutral. 100
means energised, proud, or playful. Consider: word choice, exclamation,
self-deprecation, frustration markers ("fix again", "wtf", "ugh"), pride
markers ("ship", "done", "love"), and the cadence of the messages. Reply with
only the integer.
"""


def mood_score(
    repo_path: Path,
    cfg: ClaudeConfig,
    *,
    api_key: str | None = None,
    client_factory: Any | None = None,
) -> int | None:
    """Return mood 0–100, or None if disabled / capped / no commits."""
    if not cfg.enabled:
        return None
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    messages = _last_commit_messages(repo_path, count=30)
    if not messages:
        return None

    sample_hash = _hash_messages(messages)

    with connect(db_path()) as conn:
        cached = get_mood(conn, repo_path, sample_hash)
        if cached is not None:
            return cached

        if _over_monthly_cap(conn, cfg):
            return None

        # Lazy import: anthropic is heavy and we want CLI startup fast.
        from anthropic import Anthropic  # noqa: PLC0415

        client = (client_factory or Anthropic)(api_key=api_key)
        result = client.messages.create(
            model=cfg.model,
            max_tokens=8,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": "\n".join(f"- {m}" for m in messages)}],
        )

        score = _parse_score(_first_text(result))
        if score is None:
            return None

        usage = getattr(result, "usage", None)
        tokens = 0
        if usage is not None:
            tokens = int(getattr(usage, "input_tokens", 0)) + int(
                getattr(usage, "output_tokens", 0)
            )
        _bump_monthly_usage(conn, tokens)
        upsert_mood(conn, repo_path, score, sample_hash)
        return score


def _last_commit_messages(path: Path, count: int) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "log", f"-{count}", "--format=%s"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return [line for line in out.splitlines() if line.strip()]


def _hash_messages(messages: list[str]) -> str:
    h = hashlib.sha256()
    for m in messages:
        h.update(m.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _first_text(result: Any) -> str:
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            return text
    return ""


def _parse_score(raw: str) -> int | None:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    try:
        n = int(digits[:3])
    except ValueError:
        return None
    return max(0, min(100, n))


def _over_monthly_cap(conn: Any, cfg: ClaudeConfig) -> bool:
    used = _monthly_usage(conn)
    return used >= cfg.monthly_token_cap


def _monthly_usage(conn: Any) -> int:
    bucket_key, _ = _bucket_keys()
    raw = get_meta(conn, bucket_key)
    if raw is None:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def _bump_monthly_usage(conn: Any, tokens: int) -> None:
    bucket_key, marker_key = _bucket_keys()
    current = _monthly_usage(conn)
    set_meta(conn, bucket_key, str(current + max(0, tokens)))
    set_meta(conn, marker_key, datetime.now(UTC).isoformat())


def _bucket_keys() -> tuple[str, str]:
    now = datetime.now(UTC)
    bucket = f"claude_tokens_{now.year:04d}_{now.month:02d}"
    return bucket, f"{bucket}_last_used"
