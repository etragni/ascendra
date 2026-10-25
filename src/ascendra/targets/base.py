"""Target plugin contract. A target teaches Ascendra how to upgrade one kind of platform."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import typer

from ascendra.agents import Agent


class Target(ABC):
    name: str  # cli name and config section, e.g. "kubernetes"
    title: str
    status: str  # available | planned
    description: str
    aliases: tuple[str, ...] = ()

    @abstractmethod
    def domain_agents(self, options: dict[str, Any]) -> list[Agent]:
        """The target-specific agents, in order: typically Scout, Compatibility, Researcher, Planner.
        Shared agents (Risk, Rehearsal, Reporter) are appended by the pipeline."""

    def cli(self) -> typer.Typer | None:
        """Optional Typer sub-app exposed as `ascendra <name> ...`."""
        return None


class PlannedTarget(Target):
    status = "planned"

    def domain_agents(self, options: dict[str, Any]) -> list[Agent]:
        raise NotImplementedError(f"the {self.name} target is on the roadmap, contributions welcome")
