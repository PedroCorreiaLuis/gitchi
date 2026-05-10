"""Pet rarities — deterministic gacha-style tier assignment.

Every pet gets a rarity rolled from a stable hash of (repo_path,
first_commit_iso). The hash maps to a 0-9999 bucket, and the bucket falls
into one of six tiers with fixed percentages:

| Tier       | Bucket range | %     |
|------------|--------------|-------|
| common     | 0     – 4999 | 50.0% |
| uncommon   | 5000  – 7499 | 25.0% |
| rare       | 7500  – 8999 | 15.0% |
| epic       | 9000  – 9699 |  7.0% |
| mythic     | 9700  – 9949 |  2.5% |
| legendary  | 9950  – 9999 |  0.5% |

Because the inputs (`repo.path` and the timestamp of the very first commit)
are stable across scans, a given repo always rolls the same tier — there's
no "re-rolling" on each refresh. If a repo's git history is rewritten such
that the first-commit timestamp changes, the rarity might shift; that's
the right behavior (it's effectively a new pet).

Repos with no first commit (empty repos) hash on `repo.path` alone, which
still gives them a stable tier.
"""

from __future__ import annotations

import hashlib

from .models import Rarity, Repo

# (cumulative-upper-bound, tier) entries used to bucket the 0-9999 hash output.
_BUCKETS: tuple[tuple[int, Rarity], ...] = (
    (5000, Rarity.COMMON),
    (7500, Rarity.UNCOMMON),
    (9000, Rarity.RARE),
    (9700, Rarity.EPIC),
    (9950, Rarity.MYTHIC),
    (10000, Rarity.LEGENDARY),
)

_BUCKET_SIZE = 10_000


def rarity_for(repo: Repo) -> Rarity:
    """Return the deterministic rarity tier for `repo`."""
    seed = _seed(repo)
    bucket = _bucket(seed)
    for upper, tier in _BUCKETS:
        if bucket < upper:
            return tier
    return Rarity.LEGENDARY  # unreachable; satisfies the type checker


def _seed(repo: Repo) -> str:
    first = repo.first_commit.isoformat() if repo.first_commit is not None else ""
    return f"{repo.path}|{first}"


def _bucket(seed: str) -> int:
    """Hash → integer in `[0, _BUCKET_SIZE)`.

    SHA-256 is overkill but cheap and gives a uniform distribution. We take
    the first 4 bytes (32 bits) and mod into the bucket size.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(digest[:4], "big")
    return n % _BUCKET_SIZE


def color_for(rarity: Rarity) -> str:
    """Rich-compatible style string for rendering this tier.

    Used by `cli.py`'s table renderer and (indirectly) by the TUI to colour
    the rarity column and row accents.
    """
    return {
        Rarity.COMMON: "dim",
        Rarity.UNCOMMON: "green",
        Rarity.RARE: "blue",
        Rarity.EPIC: "magenta",
        Rarity.MYTHIC: "bright_red",
        Rarity.LEGENDARY: "bright_yellow",
    }[rarity]


def emoji_for(rarity: Rarity) -> str:
    """A single-glyph emoji used in compact list rows and the news log."""
    return {
        Rarity.COMMON: "⚪",
        Rarity.UNCOMMON: "🟢",
        Rarity.RARE: "🔵",
        Rarity.EPIC: "🟣",
        Rarity.MYTHIC: "🟠",
        Rarity.LEGENDARY: "🟡",
    }[rarity]
