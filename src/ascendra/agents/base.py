from __future__ import annotations

from abc import ABC, abstractmethod

from ascendra.models import UpgradeContext


class Agent(ABC):
    """An agent owns one step of the upgrade. It reads and writes the shared UpgradeContext.

    Rule of thumb: facts come from deterministic code (APIs, indexes, version math);
    LLMs are used for judgement (risk, interpretation of release notes, explanation).
    """

    name: str = "agent"
    role: str = ""
    uses_llm: bool = False

    @abstractmethod
    def run(self, ctx: UpgradeContext) -> str:
        """Do the work, mutate ctx, return a one-line summary. Raise SkipAgent to skip."""


class SkipAgent(Exception):
    pass


class Degraded(Exception):
    """Raised (with a summary) when the agent fell back to a weaker strategy but still produced output."""
