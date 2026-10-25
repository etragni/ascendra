"""Rehearsal agent (roadmap v0.2): replays the plan on an ephemeral environment before touching anything real.

Shared contract, target-specific sandboxes: an ephemeral cluster for Kubernetes, a cloned VM for Linux,
a nested ESXi lab for VMware.

Kubernetes design: create a throwaway cluster at the current version (kind, vcluster or a hosted control plane
such as Kamaji), install the inventoried Helm releases with their values, execute the plan wave by wave and
hand the result to a Verifier agent (pod health, events, smoke tests).
"""
from __future__ import annotations

from ascendra.agents.base import Agent, SkipAgent
from ascendra.models import UpgradeContext


class RehearsalAgent(Agent):
    name = "rehearsal"
    role = "Dry-runs the plan on an ephemeral environment (not implemented yet)"

    def run(self, ctx: UpgradeContext) -> str:
        raise SkipAgent("not implemented yet, see docs/roadmap.md")
