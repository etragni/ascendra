"""Assembles target agents with the shared agents and runs them with console output."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from ascendra import __version__
from ascendra.agents import Agent, RehearsalAgent, ReporterAgent, RiskAgent
from ascendra.llm import LLM
from ascendra.models import AgentRun, UpgradeContext
from ascendra.orchestrator import Orchestrator, PipelineError

console = Console()
STATUS = {"ok": "[green]✔[/]", "degraded": "[yellow]◐[/]", "skipped": "[dim]–[/]", "failed": "[red]✘[/]"}


def shared_agents(llm: LLM | None, out: Path) -> list[Agent]:
    """Agents every target gets, after its own domain agents."""
    return [RiskAgent(llm), RehearsalAgent(), ReporterAgent(out)]


def _event(run: AgentRun) -> None:
    console.print(f"  {STATUS[run.status]} [bold]{run.agent:<14}[/] {run.detail}")


def run_cli_pipeline(ctx: UpgradeContext, target_agents: list[Agent], llm: LLM | None, out: Path) -> None:
    """Run and exit with 0 (no blockers), 1 (blockers) or 2 (pipeline error). Handy in CI."""
    console.print(f"[bold]Ascendra[/] {__version__}: planning [cyan]{ctx.target}[/] upgrade of "
                  f"[cyan]{ctx.subject}[/] to [cyan]{ctx.target_version}[/] (LLM: {llm.name if llm else 'off'})")
    try:
        Orchestrator(target_agents + shared_agents(llm, out), on_event=_event).run(ctx)
    except PipelineError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(2) from e
    console.print()
    if ctx.blockers:
        console.print(f"[red bold]{len(ctx.blockers)} blocker(s)[/] found. See {out}/upgrade-plan.md")
        raise typer.Exit(1)
    console.print(f"[green bold]No blockers.[/] {len(ctx.plan)} steps planned. See {out}/upgrade-plan.md")
