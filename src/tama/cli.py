"""Typer-driven entry point for `tama`."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import config as config_mod
from . import cron as cron_mod
from . import refresh as refresh_mod
from . import verbs as verbs_mod
from .art import render
from .history import sparkline
from .models import Pet
from .species import emoji_for
from .store import all_pets, connect, find_repo_by_name, get_pet, vitals_history

app = typer.Typer(
    name="tama",
    help="A virtual pet for every git repo.",
    no_args_is_help=False,
    add_completion=False,
)
config_app = typer.Typer(help="Manage tama configuration.")
cron_app = typer.Typer(help="Manage the nightly refresh launchd job (macOS).")
menubar_app = typer.Typer(help="Manage the menu-bar app (macOS).")
app.add_typer(config_app, name="config")
app.add_typer(cron_app, name="cron")
app.add_typer(menubar_app, name="menubar")

console = Console()


# ---------------------------------------------------------------------------
# default: open dashboard
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from .tui import run as tui_run  # noqa: PLC0415  (heavy import; only when needed)

        tui_run()


# ---------------------------------------------------------------------------
# explicit subcommands
# ---------------------------------------------------------------------------


@app.command()
def refresh() -> None:
    """Re-scan all configured paths and recompute every pet."""
    summary = refresh_mod.refresh()
    console.print(
        f"[bold]Scanned[/bold] {summary.scanned} repos · "
        f"[bold]ghosts[/bold] {summary.ghosts} · "
        f"github={summary.enriched_with_github} · "
        f"local_energy={summary.enriched_with_local_energy} · "
        f"claude={summary.enriched_with_claude}"
    )
    if summary.news_events:
        console.print()
        console.print("[bold]news[/bold]")
        for event in summary.news_events:
            console.print(f"  {event.headline}")


@app.command()
def news(limit: int = typer.Option(20, help="how many recent events to show")) -> None:
    """Print the most recent state-change events across the pet zoo."""
    events = refresh_mod.list_recent_news(limit=limit)
    if not events:
        console.print(
            "[yellow]No news yet. Run [bold]tama refresh[/bold] a few times "
            "and we'll have something to report.[/yellow]"
        )
        return
    for event in events:
        console.print(event.headline)


@app.command(name="list")
def list_cmd(
    sort: str = typer.Option("hunger", help="hunger | health | mood | age | name"),
    show_ignored: bool = typer.Option(
        False, "--all", help="include pets you've explicitly `tama ignore`d"
    ),
) -> None:
    """List all pets in a sortable table."""
    with connect() as conn:
        pets = all_pets(conn, include_ignored=show_ignored)
    if not pets:
        console.print("[yellow]No pets yet. Run [bold]tama refresh[/bold] first.[/yellow]")
        return
    pets.sort(key=_sort_key(sort))
    table = Table(title=f"tama — {len(pets)} pets")
    table.add_column("name")
    table.add_column("species")
    table.add_column("stage")
    table.add_column("hunger")
    table.add_column("health")
    table.add_column("mood")
    table.add_column("status")
    for pet in pets:
        table.add_row(
            pet.repo.name,
            f"{emoji_for(pet.species)} {pet.species.value}",
            pet.stage.value,
            _bar(pet.vitals.hunger),
            _bar(pet.vitals.health),
            _bar(pet.vitals.mood),
            pet.status_word,
        )
    console.print(table)


@app.command()
def show(name: str) -> None:
    """Show detail for a single pet by repo name."""
    pet = _resolve(name)
    if pet is None:
        raise typer.Exit(code=1)
    console.print(
        f"[bold]{pet.repo.name}[/bold]  {emoji_for(pet.species)} {pet.species.value} · {pet.stage.value}"
    )
    console.print(f"[dim]{pet.repo.path}[/dim]\n")
    console.print(render(pet.species, pet.stage))
    console.print("")
    table = Table(show_header=False, box=None)
    table.add_column()
    table.add_column()
    table.add_column()
    table.add_row("hunger", _bar(pet.vitals.hunger), _sparkline_for(pet, "hunger"))
    table.add_row("health", _bar(pet.vitals.health), _sparkline_for(pet, "health"))
    table.add_row("energy", _bar(pet.vitals.energy), _sparkline_for(pet, "energy"))
    table.add_row("mood", _bar(pet.vitals.mood), _sparkline_for(pet, "mood"))
    table.add_row("age", f"{pet.vitals.age_days} days", "")
    table.add_row("status", pet.status_word, "")
    console.print(table)


@app.command()
def feed(
    name: str,
    open_editor: bool = typer.Option(
        True,
        "--open/--no-open",
        help="open $EDITOR at the TODO's file:line when a TODO is found",
    ),
) -> None:
    """Find one stale TODO/FIXME and (by default) jump $EDITOR straight to it."""
    pet = _resolve(name)
    if pet is None:
        raise typer.Exit(code=1)
    hit = verbs_mod.feed(pet.repo.path)
    if hit is None:
        console.print(f"[green]{pet.repo.name} purrs. No TODOs found.[/green]")
        return
    console.print(f"[bold]{pet.repo.name}[/bold] is hungry. It says:")
    console.print(f"  [yellow]{hit.file}:{hit.line}[/yellow]  {hit.message}")
    if open_editor:
        rc = verbs_mod.pet(pet.repo.path, file=hit.file, line=hit.line)
        if rc == 127:
            console.print("[dim](no $EDITOR set and no fallback found — skipping open)[/dim]")


@app.command()
def play(name: str) -> None:
    """Run the repo's test suite. Print result."""
    pet = _resolve(name)
    if pet is None:
        raise typer.Exit(code=1)
    result = verbs_mod.play(pet.repo.path)
    if result is None:
        console.print(f"[yellow]{pet.repo.name} has no test runner. It looks bored.[/yellow]")
        return
    runner_str = " ".join(result.runner)
    if result.returncode == 0:
        console.print(f"[green]{pet.repo.name} bounces happily — {runner_str} passed.[/green]")
    else:
        console.print(
            f"[red]{pet.repo.name} sulks — {runner_str} returned {result.returncode}.[/red]"
        )
        if result.stderr.strip():
            console.print(result.stderr.strip().splitlines()[-1])


def _pet_cmd(name: str = typer.Argument(..., metavar="NAME")) -> None:
    """Open the repo in $EDITOR."""
    p = _resolve(name)
    if p is None:
        raise typer.Exit(code=1)
    rc = verbs_mod.pet(p.repo.path)
    if rc == 127:
        console.print("[red]No $EDITOR set and no fallback (cursor/code/subl/vim) found.[/red]")
        raise typer.Exit(code=127)


app.command(name="pet", help="Open the repo in $EDITOR.")(_pet_cmd)


@app.command()
def bury(
    name: str,
    reason: str = typer.Option("", help="optional eulogy"),
) -> None:
    """Mark a repo as at peace. Pet stays visible but greyed out."""
    pet = _resolve(name)
    if pet is None:
        raise typer.Exit(code=1)
    verbs_mod.bury(pet.repo.path, reason or None)
    console.print(f"[dim]{pet.repo.name} laid to rest.[/dim] {reason}")


@app.command()
def revive(name: str) -> None:
    """Un-bury a pet."""
    pet = _resolve(name)
    if pet is None:
        raise typer.Exit(code=1)
    verbs_mod.revive(pet.repo.path)
    console.print(f"[green]{pet.repo.name} stirs.[/green]")


@app.command()
def ignore(
    name: str,
    reason: str = typer.Option("", help="optional note: why this repo doesn't belong"),
) -> None:
    """Hide a pet from `tama list` and the news feed.

    Use this for repos you don't actually maintain (vendored forks, clones you
    inherited). Different from `bury` — burying is for projects that died with
    dignity. Ignored pets are still in the DB and reappear with `tama list --all`.
    """
    pet = _resolve(name)
    if pet is None:
        raise typer.Exit(code=1)
    verbs_mod.ignore(pet.repo.path, reason or None)
    console.print(f"[dim]{pet.repo.name} ignored.[/dim] {reason}")


@app.command()
def unignore(name: str) -> None:
    """Bring a previously ignored pet back into the dashboard."""
    pet = _resolve(name)
    if pet is None:
        raise typer.Exit(code=1)
    verbs_mod.unignore(pet.repo.path)
    console.print(f"[green]{pet.repo.name} is visible again.[/green]")


# ---------------------------------------------------------------------------
# config subcommands
# ---------------------------------------------------------------------------


@config_app.command("show")
def config_show() -> None:
    cfg = config_mod.load()
    table = Table(title=f"config @ {config_mod.config_path()}")
    table.add_column("key")
    table.add_column("value")
    table.add_row("scan.paths", ", ".join(cfg.scan.paths))
    table.add_row("scan.depth", str(cfg.scan.depth))
    table.add_row("scan.ignore", ", ".join(cfg.scan.ignore))
    table.add_row("stats.ghost_after_days", str(cfg.stats.ghost_after_days))
    table.add_row("claude.enabled", str(cfg.claude.enabled))
    table.add_row("claude.model", cfg.claude.model)
    table.add_row("claude.monthly_token_cap", str(cfg.claude.monthly_token_cap))
    table.add_row("github.enabled", str(cfg.github.enabled))
    console.print(table)


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    cfg = config_mod.load()
    try:
        config_mod.set_value(cfg, key, value)
    except (KeyError, ValueError) as e:
        console.print(f"[red]bad key:[/red] {e}")
        raise typer.Exit(code=2) from None
    config_mod.save(cfg)
    console.print(f"[green]ok[/green] {key} = {value}")


@config_app.command("path")
def config_path() -> None:
    console.print(str(config_mod.config_path()))


# ---------------------------------------------------------------------------
# cron subcommands
# ---------------------------------------------------------------------------


@cron_app.command("install")
def cron_install(hour: int = 3, minute: int = 30) -> None:
    path = cron_mod.install(hour=hour, minute=minute)
    console.print(f"[green]installed[/green] {path}")


@cron_app.command("uninstall")
def cron_uninstall() -> None:
    removed = cron_mod.uninstall()
    if removed:
        console.print("[green]uninstalled[/green]")
    else:
        console.print("[yellow]no plist installed[/yellow]")


@cron_app.command("show")
def cron_show() -> None:
    console.print(cron_mod.render_plist())


# ---------------------------------------------------------------------------
# menubar subcommands
# ---------------------------------------------------------------------------


@menubar_app.command("run")
def menubar_run() -> None:
    """Run the menu-bar app in the foreground."""
    from . import menubar  # noqa: PLC0415

    menubar.main()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _resolve(name: str) -> Pet | None:
    """Resolve a pet by short name or absolute path."""
    with connect() as conn:
        candidate = Path(name).expanduser()
        if candidate.is_absolute():
            pet = get_pet(conn, candidate)
            if pet is not None:
                return pet
        repo = find_repo_by_name(conn, name)
        if repo is None:
            console.print(f"[red]no pet named[/red] {name}. Try [bold]tama list[/bold].")
            return None
        return get_pet(conn, repo.path)


def _sort_key(field: str):  # type: ignore[no-untyped-def]
    field = field.lower()
    if field == "hunger":
        return lambda p: p.vitals.hunger
    if field == "health":
        return lambda p: p.vitals.health
    if field == "mood":
        return lambda p: p.vitals.mood
    if field == "age":
        return lambda p: -p.vitals.age_days
    return lambda p: p.repo.name


def _bar(value: int, width: int = 10) -> str:
    filled = max(0, min(width, round(value / 100 * width)))
    return f"[{'█' * filled}{'░' * (width - filled)}] {value:3d}"


def _sparkline_for(pet: Pet, field: str, *, width: int = 20) -> str:
    """Render a Unicode sparkline for one vital across the pet's recent history."""
    with connect() as conn:
        history = vitals_history(conn, pet.repo.path, limit=width)
    if not history:
        return ""
    series = [getattr(v, field) for v in history]
    return sparkline(series, width=width)


if __name__ == "__main__":
    app()
