"""Tests for the deterministic-gacha rarity assignment."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from gitchi.models import Rarity, Repo
from gitchi.rarity import _BUCKETS, color_for, emoji_for, rarity_for


def _repo(path: str, first: datetime | None = None) -> Repo:
    return Repo(
        path=Path(path),
        name=Path(path).name,
        primary_language="Python",
        first_commit=first or datetime(2025, 1, 1, tzinfo=UTC),
        last_commit=first or datetime(2025, 1, 1, tzinfo=UTC),
        commit_count=1,
        size_bytes=0,
        has_tests=False,
        has_ci=False,
    )


def test_rarity_is_deterministic() -> None:
    """Same inputs must always produce the same tier — across processes too."""
    r = _repo("/repos/alpha")
    assert rarity_for(r) == rarity_for(r)


def test_different_paths_get_different_seeds() -> None:
    """Different repos almost certainly land in different buckets (collisions exist but are rare)."""
    paths = [f"/repos/r{i}" for i in range(50)]
    rarities = {rarity_for(_repo(p)) for p in paths}
    # We should see at least 3 distinct tiers across 50 randomly-seeded repos.
    assert len(rarities) >= 3


def test_distribution_matches_target_percentages_within_tolerance() -> None:
    """Sample 20 000 synthetic repos, check the empirical distribution.

    Targets: 50 / 25 / 15 / 7 / 2.5 / 0.5 for common/uncommon/rare/epic/mythic/legendary.
    Tolerance of 2.0 percentage points absolute (legendary is the noisiest at 0.5%).
    """
    n = 20_000
    counts: Counter[Rarity] = Counter(
        rarity_for(_repo(f"/r/{i}", datetime(2025, 1, 1, tzinfo=UTC))) for i in range(n)
    )

    expected = {
        Rarity.COMMON: 50.0,
        Rarity.UNCOMMON: 25.0,
        Rarity.RARE: 15.0,
        Rarity.EPIC: 7.0,
        Rarity.MYTHIC: 2.5,
        Rarity.LEGENDARY: 0.5,
    }
    tolerance = 2.0  # percentage points

    for tier, target_pct in expected.items():
        observed_pct = (counts[tier] / n) * 100
        assert abs(observed_pct - target_pct) < tolerance, (
            f"{tier}: observed {observed_pct:.2f}%, expected {target_pct}% (±{tolerance})"
        )


def test_every_tier_in_buckets_table() -> None:
    """All six tiers must appear in the bucket table — guards against future drift."""
    tiers_in_buckets = {tier for _, tier in _BUCKETS}
    assert tiers_in_buckets == set(Rarity)


def test_color_and_emoji_defined_for_every_tier() -> None:
    """Every rarity needs a color + emoji; lookups must not raise."""
    for tier in Rarity:
        assert color_for(tier), f"missing color for {tier}"
        assert emoji_for(tier), f"missing emoji for {tier}"


def test_rarity_handles_empty_repo_with_no_first_commit() -> None:
    """A brand-new git repo with no commits still gets a stable rarity."""
    repo = Repo(
        path=Path("/r/empty"),
        name="empty",
        primary_language=None,
        first_commit=None,
        last_commit=None,
        commit_count=0,
        size_bytes=0,
        has_tests=False,
        has_ci=False,
    )
    a = rarity_for(repo)
    b = rarity_for(repo)
    assert a == b
    assert a in set(Rarity)
