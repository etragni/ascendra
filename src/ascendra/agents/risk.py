"""Risk analyst: LLM-powered, target-agnostic. Reads changelogs and findings, judges risk, explains it.

Falls back to transparent heuristics when no LLM is configured or the call fails.
"""
from __future__ import annotations

import json

from ascendra.agents.base import Agent, Degraded
from ascendra.llm import LLM, LLMError
from ascendra.models import ComponentUpgrade, RiskAssessment, RiskLevel, UpgradeContext

SYSTEM_PROMPT = """You are the Risk Analyst agent in Ascendra, a multi-agent infrastructure upgrade system.
The platform being upgraded is given as `target` (e.g. kubernetes, linux, vmware).
Other agents have already established the FACTS (inventory, findings, component versions, changelogs, plan).
Your job is JUDGEMENT: for each component upgrade, assess the operational risk and say what a platform
engineer must do. Base every claim on the provided data; never invent changes. If a changelog is empty,
say so and rate the risk from the version jump alone.

Return ONLY a JSON object, no prose, with this shape:
{
  "executive_summary": "3-5 sentences for a platform team lead",
  "assessments": [
    {"component": "<component name exactly as given>", "level": "low|medium|high",
     "summary": "one sentence", "breaking_changes": ["..."], "recommended_actions": ["..."]}
  ]
}"""

BREAKING_HINTS = ("breaking", "removed", "remove ", "deprecat", "renamed", "no longer", "migrat", "[removed]",
                  "[changed]", "[security]")


def heuristic_assessment(c: ComponentUpgrade) -> RiskAssessment:
    hits = [ch for ch in c.changes if any(h in ch.lower() for h in BREAKING_HINTS)]
    if c.major_jump:
        level = RiskLevel.HIGH
    elif hits or c.needs_newer_platform:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    reasons = []
    if c.major_jump:
        reasons.append("major version jump")
    if hits:
        reasons.append(f"{len(hits)} changelog entries look potentially breaking")
    if c.needs_newer_platform:
        reasons.append("must be upgraded during the platform upgrade")
    if not c.changes:
        reasons.append("no structured changelog published, so read upstream release notes")
    return RiskAssessment(
        component=c.name, level=level,
        summary=f"{c.package} {c.current_version} -> {c.target_version}: " + ("; ".join(reasons) or "routine bump"),
        breaking_changes=hits[:10],
        recommended_actions=["diff the rendered configuration before applying",
                             "review your overrides against the new defaults"] if level != RiskLevel.LOW else [],
    )


class RiskAgent(Agent):
    name = "risk"
    role = "Judges the risk of each component upgrade from changelogs and findings, writes the summary"
    uses_llm = True

    def __init__(self, llm: LLM | None) -> None:
        self.llm = llm

    def _payload(self, ctx: UpgradeContext) -> str:
        return json.dumps({
            "target": ctx.target,
            "subject": ctx.subject,
            "current_version": ctx.current_version,
            "target_version": ctx.target_version,
            "findings": [f.model_dump(mode="json") for f in ctx.findings],
            "component_upgrades": [c.model_dump(mode="json") for c in ctx.components if c.target_version],
            "plan": [s.model_dump(mode="json") for s in ctx.plan],
        }, indent=1)

    def run(self, ctx: UpgradeContext) -> str:
        upgrades = [c for c in ctx.components if c.target_version]
        if self.llm is None:
            ctx.risks = [heuristic_assessment(c) for c in upgrades]
            raise Degraded(f"no LLM configured, {len(ctx.risks)} heuristic assessments")
        try:
            data = self.llm.complete_json(SYSTEM_PROMPT, self._payload(ctx))
            ctx.executive_summary = data.get("executive_summary")
            ctx.risks = [RiskAssessment(**a, assessed_by=self.llm.name) for a in data.get("assessments", [])]
        except (LLMError, TypeError, ValueError) as e:
            ctx.risks = [heuristic_assessment(c) for c in upgrades]
            raise Degraded(f"LLM failed ({e}); fell back to heuristics") from e
        return f"{len(ctx.risks)} assessments by {self.llm.name}"
