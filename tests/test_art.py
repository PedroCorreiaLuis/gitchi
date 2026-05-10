"""ASCII art coverage — every (species, stage) returns non-empty multi-line art."""

from __future__ import annotations

from tama.art import render
from tama.models import Species, Stage


def test_every_combination_renders() -> None:
    for species in Species:
        for stage in Stage:
            art = render(species, stage)
            assert art, f"empty art for {species}/{stage}"
            assert "\n" in art, f"single-line art for {species}/{stage}"
            for line in art.splitlines():
                assert len(line) <= 30, f"line too wide for {species}/{stage}: {line!r}"
