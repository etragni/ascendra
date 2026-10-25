"""Runs the agent pipeline over a shared UpgradeContext.

v0.1 is a fixed sequence. The roadmap moves to a supervisor agent that can loop
(e.g. Rehearsal fails -> Planner re-plans) with a hard limit on iterations.
"""
from __future__ import annotations

import time
from collections.abc import Callable

from ascendra.agents import Agent, Degraded, SkipAgent
from ascendra.models import AgentRun, UpgradeContext


class PipelineError(RuntimeError):
    pass


class Orchestrator:
    def __init__(self, agents: list[Agent], on_event: Callable[[AgentRun], None] | None = None) -> None:
        self.agents = agents
        self.on_event = on_event or (lambda run: None)

    def run(self, ctx: UpgradeContext) -> UpgradeContext:
        for agent in self.agents:
            start = time.monotonic()
            try:
                detail, status = agent.run(ctx), "ok"
            except SkipAgent as e:
                detail, status = str(e), "skipped"
            except Degraded as e:
                detail, status = str(e), "degraded"
            except Exception as e:
                run = AgentRun(agent=agent.name, status="failed", detail=str(e),
                               seconds=time.monotonic() - start)
                ctx.runs.append(run)
                self.on_event(run)
                raise PipelineError(f"agent '{agent.name}' failed: {e}") from e
            run = AgentRun(agent=agent.name, status=status, detail=detail, seconds=time.monotonic() - start)
            ctx.runs.append(run)
            self.on_event(run)
        return ctx
