"""ASCII art coverage — every (species, stage) returns non-empty multi-line art."""

from __future__ import annotations

from gitchi.art import render
from gitchi.models import Species, Stage


def test_every_combination_renders() -> None:
    for species in Species:
        for stage in Stage:
            art = render(species, stage)
            assert art, f"empty art for {species}/{stage}"
            assert "\n" in art, f"single-line art for {species}/{stage}"
            for line in art.splitlines():
                assert len(line) <= 30, f"line too wide for {species}/{stage}: {line!r}"


def test_idle_frames_returns_two_strings_for_baby_blob() -> None:
    from gitchi.art import idle_frames
    from gitchi.models import Species, Stage

    frames = idle_frames(Species.BLOB, Stage.BABY)
    assert isinstance(frames, list)
    assert len(frames) == 2
    assert frames[0] != frames[1]


def test_idle_frames_egg_is_static() -> None:
    from gitchi.art import idle_frames, render
    from gitchi.models import Species, Stage

    frames = idle_frames(Species.DRAGON, Stage.EGG)
    assert frames[0] == render(Species.DRAGON, Stage.EGG)
    assert frames[1] == frames[0]


def test_idle_frames_ghost_is_static() -> None:
    from gitchi.art import idle_frames, render
    from gitchi.models import Species, Stage

    frames = idle_frames(Species.DRAGON, Stage.GHOST)
    assert frames[0] == render(Species.DRAGON, Stage.GHOST)
    assert frames[1] == frames[0]


def test_idle_frames_for_every_species_stage_pair_returns_two() -> None:
    from gitchi.art import idle_frames
    from gitchi.models import Species, Stage

    for species in Species:
        for stage in Stage:
            frames = idle_frames(species, stage)
            assert len(frames) == 2, f"{species} {stage}"


def test_idle_frames_first_frame_matches_render() -> None:
    from gitchi.art import idle_frames, render
    from gitchi.models import Species, Stage

    for species in Species:
        for stage in Stage:
            frames = idle_frames(species, stage)
            assert frames[0] == render(species, stage), f"{species} {stage}"
