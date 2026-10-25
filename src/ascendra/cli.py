from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ascendra import __version__
from ascendra.pipeline import shared_agents
from ascendra.targets import TARGETS, get_target

app = typer.Typer(help="Ascendra: agentic infrastructure upgrades.", no_args_is_help=True)
console = Console()

for _t in TARGETS.values():
    if (sub := _t.cli()) is not None:
        app.add_typer(sub, name=_t.name)
        for alias in _t.aliases:
            app.add_typer(_t.cli(), name=alias, hidden=True)


@app.command()
def targets() -> None:
    """List the platforms Ascendra can upgrade."""
    t = Table("Target", "Status", "What it upgrades")
    for tg in TARGETS.values():
        status = "[green]available[/]" if tg.status == "available" else "[dim]planned[/]"
        t.add_row(tg.name, status, tg.description)
    console.print(t)


@app.command()
def agents(target: Annotated[str, typer.Argument(help="Target name")] = "kubernetes") -> None:
    """List the agents of a target and what each one is responsible for."""
    tg = get_target(target)
    if tg.status != "available":
        console.print(f"[yellow]{tg.name} is planned:[/] see the module docstring and docs/roadmap.md")
        raise typer.Exit(0)
    t = Table("Agent", "Scope", "Responsibility", "LLM")
    for a in tg.domain_agents({"live": False}):
        t.add_row(a.name, tg.name, a.role, "yes" if a.uses_llm else "no")
    for a in shared_agents(None, out=__import__("pathlib").Path(".")):
        t.add_row(a.name, "shared", a.role, "yes" if a.uses_llm else "no")
    console.print(t)


@app.command()
def version() -> None:
    console.print(__version__)
