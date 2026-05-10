"""ASCII art for every (Species, Stage) pair.

Each renderer returns a multi-line string with no leading/trailing newline.
Designed to fit in a ~16 wide × 7 tall cell so a grid of pets fits in the TUI.
"""

from __future__ import annotations

from .models import Species, Stage


def render(species: Species, stage: Stage) -> str:
    if stage is Stage.EGG:
        return _EGG[species]
    if stage is Stage.GHOST:
        return _GHOST[species]

    bank = {
        Stage.BABY: _BABY,
        Stage.TEEN: _TEEN,
        Stage.ADULT: _ADULT,
        Stage.ELDER: _ELDER,
    }[stage]

    return bank.get(species, bank[Species.GENERIC_BLOB])


# ---------------------------------------------------------------------------
# eggs — small variations hint at species
# ---------------------------------------------------------------------------

_EGG_BASE = """\
    .---.
   /     \\
  |  {h}  |
   \\     /
    '---'"""


def _egg(hint: str) -> str:
    return _EGG_BASE.format(h=hint.center(3))


_EGG: dict[Species, str] = {
    Species.DRAGON: _egg("🜂"),
    Species.SNAKE: _egg("~"),
    Species.BLOB: _egg("o"),
    Species.GOPHER: _egg("•"),
    Species.FALCON: _egg("^"),
    Species.GEM: _egg("◆"),
    Species.GHOST_CAT: _egg("∴"),
    Species.SCROLL: _egg("§"),
    Species.GENERIC_BLOB: _egg("·"),
}


# ---------------------------------------------------------------------------
# ghosts — universal silhouette
# ---------------------------------------------------------------------------

_GHOST_FORM = """\
   .-~~~-.
  /  o o  \\
 (    >    )
  \\ '~~~' /
   ~~~~~~~"""


_GHOST: dict[Species, str] = dict.fromkeys(Species, _GHOST_FORM)


# ---------------------------------------------------------------------------
# babies
# ---------------------------------------------------------------------------

_BABY: dict[Species, str] = {
    Species.DRAGON: """\
     /\\_/\\
    ( o.o )
    > ^ <
    /| |\\
    """.rstrip(),
    Species.SNAKE: """\
       __
     _/  \\_
    (  oo  )
     \\____/
      ~~~""".rstrip(),
    Species.BLOB: """\
     .---.
    ( o o )
    | --- |
     '---'""".rstrip(),
    Species.GOPHER: """\
     /---\\
    ( o o )
    | <_> |
     \\___/""".rstrip(),
    Species.FALCON: """\
      ___
     /o o\\
    < \\_/ >
     \\___/
      ^^^""".rstrip(),
    Species.GEM: """\
      /\\
     /  \\
    < ◆◆ >
     \\  /
      \\/""".rstrip(),
    Species.GHOST_CAT: """\
    /\\___/\\
   ( o.o   )~
    > ^ <
    """.rstrip(),
    Species.SCROLL: """\
    .-----.
    |~~~~~|
    | -- |
    |~~~~~|
    '-----'""".rstrip(),
    Species.GENERIC_BLOB: """\
     .---.
    ( . . )
    | ___ |
     '---'""".rstrip(),
}


# ---------------------------------------------------------------------------
# teens
# ---------------------------------------------------------------------------

_TEEN: dict[Species, str] = {
    Species.DRAGON: """\
      /\\_/\\
     ( O.O )
    /  ^_^  \\
    \\__|_|__/
       /|\\""".rstrip(),
    Species.SNAKE: """\
        ___
      _/   \\_
     ( O   O )
      \\_____/
       ~~~~~""".rstrip(),
    Species.BLOB: """\
     .-----.
    ( O   O )
    |  ___  |
     '-----'""".rstrip(),
    Species.GOPHER: """\
     .------.
    ( o    o )
    |   __   |
     \\______/""".rstrip(),
    Species.FALCON: """\
       _____
      /O   O\\
     <  \\_/  >
      \\_____/
       ^   ^""".rstrip(),
    Species.GEM: """\
       /\\
      /  \\
     /    \\
    < ◆◆◆◆ >
     \\    /
      \\  /
       \\/""".rstrip(),
    Species.GHOST_CAT: """\
    /\\___/\\
   ( O   O ) ~
    >  ^  <
    /| | | |\\""".rstrip(),
    Species.SCROLL: """\
    .--------.
    |~~~~~~~~|
    | --- -- |
    | --- -  |
    |~~~~~~~~|
    '--------'""".rstrip(),
    Species.GENERIC_BLOB: """\
     .-----.
    ( O   O )
    |  ---  |
     '-----'""".rstrip(),
}


# ---------------------------------------------------------------------------
# adults
# ---------------------------------------------------------------------------

_ADULT: dict[Species, str] = {
    Species.DRAGON: """\
       /\\_/\\
      ( O o O )
     /  \\_/  \\
    | \\__^__/ |
     \\__|_|__/
       /| |\\
      ~~~ ~~~""".rstrip(),
    Species.SNAKE: """\
         _____
       _/     \\_
      ( O     O )
       \\_______/
        ~~~~~~~
         ~~~""".rstrip(),
    Species.BLOB: """\
      .-------.
     ( O  ^  O )
     |   ___   |
     |  '---'  |
      '-------'""".rstrip(),
    Species.GOPHER: """\
     .--------.
    ( o      o )
    |   ____   |
    |  /    \\  |
     \\________/""".rstrip(),
    Species.FALCON: """\
        _______
       /O     O\\
      <   \\_/   >
       \\_______/
        ^^   ^^
       /  | |  \\""".rstrip(),
    Species.GEM: """\
        /\\
       /  \\
      /    \\
     /      \\
    < ◆◆◆◆◆◆ >
     \\      /
      \\    /
       \\  /
        \\/""".rstrip(),
    Species.GHOST_CAT: """\
     /\\____/\\
    ( O      O ) ~
    /  >  ^  <  \\
    \\___|__|___/
        | |""".rstrip(),
    Species.SCROLL: """\
    .----------.
    |~~~~~~~~~~|
    | ---- --- |
    | -- ---- ||
    | ---- -- ||
    |~~~~~~~~~~|
    '----------'""".rstrip(),
    Species.GENERIC_BLOB: """\
      .-------.
     ( O     O )
     |   ___   |
     |  '---'  |
      '-------'""".rstrip(),
}


# ---------------------------------------------------------------------------
# elders — with crowns / canes / wisdom marks
# ---------------------------------------------------------------------------

_ELDER: dict[Species, str] = {
    Species.DRAGON: """\
       _♛_
      /\\_/\\
     ( ◐ ◑ )
    /  \\_/  \\
    | \\___/ |
     \\__|__/
      /| |\\""".rstrip(),
    Species.SNAKE: """\
       __♛___
      /      \\
     ( ◐    ◑ )
      \\______/
       ~~~~~
        ~~~""".rstrip(),
    Species.BLOB: """\
       _♛_
     .------.
    ( ◐    ◑ )
    |  '--'  |
     '------'""".rstrip(),
    Species.GOPHER: """\
        ♛
     .------.
    ( ◐    ◑ )
    |   __   |
    |  '__'  |
     \\______/""".rstrip(),
    Species.FALCON: """\
        _♛_
       /◐ ◑\\
      <  v  >
       \\___/
       /^ ^\\""".rstrip(),
    Species.GEM: """\
        ♛
       /\\
      /◆◆\\
     /◆◆◆◆\\
    < ◆◆◆◆ >
     \\◆◆◆◆/
      \\◆◆/
       \\/""".rstrip(),
    Species.GHOST_CAT: """\
       ♛
    /\\___/\\
   ( ◐   ◑ )~
    > ^^^ <
    /__| |__\\""".rstrip(),
    Species.SCROLL: """\
       ♛
    .--------.
    |≈≈≈≈≈≈≈≈|
    | ◊ ◊  ◊ |
    | ◊◊  ◊  |
    |≈≈≈≈≈≈≈≈|
    '--------'""".rstrip(),
    Species.GENERIC_BLOB: """\
       _♛_
     .------.
    ( ◐    ◑ )
    |  '__'  |
     '------'""".rstrip(),
}
