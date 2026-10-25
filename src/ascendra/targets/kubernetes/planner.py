"""Planner: turns findings and components into ordered upgrade waves (deterministic, explainable)."""
from __future__ import annotations

from ascendra.agents.base import Agent
from ascendra.models import ComponentUpgrade, Finding, PlanStep, Severity, UpgradeContext
from ascendra.versions import Version, minor_hops, supports_minor


class PlannerAgent(Agent):
    name = "planner"
    role = "Orders the work into waves that respect version skew and add-on compatibility windows"

    def run(self, ctx: UpgradeContext) -> str:
        current, target = Version.parse(ctx.current_version), Version.parse(ctx.target_version)
        hops = minor_hops(current, target)
        steps: list[PlanStep] = []
        wave = 0

        migrations = [f for f in ctx.findings if f.category == "deprecated-api" and f.severity == Severity.BLOCKER]
        if migrations:
            wave += 1
            for f in migrations:
                steps.append(PlanStep(wave=wave, wave_name="Migrate removed APIs", action="migrate-manifest",
                                      target=f.component, rationale=f"{f.message}; {f.fix} (in {f.source})"))

        upgradable = [c for c in ctx.components
                      if c.target_version and c.target_version.lstrip("v") != c.current_version.lstrip("v")]
        before = [c for c in upgradable if not c.needs_newer_platform]
        during = [c for c in upgradable if c.needs_newer_platform]

        if before:
            wave += 1
            for c in before:
                why = ("current version does not support the target Kubernetes" if c.blocks_platform_upgrade else
                       "target version supports both current and target Kubernetes, so upgrade it first")
                steps.append(self._component_step(wave, "Prepare add-ons", c, why))

        # Add-ons whose target chart needs a newer Kubernetes are slotted into the hop where the target
        # chart first becomes supported, i.e. inside the window where old and new versions overlap.
        slot: dict[str, list[ComponentUpgrade]] = {}
        for c in during:
            first = next(h for h in hops if supports_minor(h, c.attributes.get("target_kube_constraint")))
            slot.setdefault(first.minor_str, []).append(c)
            gap = [h for h in hops if h < first and not supports_minor(h, c.attributes.get("current_kube_constraint"))]
            if gap:
                ctx.findings.append(Finding(
                    severity=Severity.BLOCKER, category="component-compat", component=c.name,
                    message=f"no compatible version window: {c.current_version} stops before {gap[0].minor_str} "
                            f"but {c.target_version} needs {first.minor_str}", found_by=self.name))

        prev = current
        for hop in hops:
            wave += 1
            name = f"Kubernetes {hop.minor_str}"
            steps.append(PlanStep(wave=wave, wave_name=name, action="upgrade-control-plane", target="control-plane",
                                  from_version=prev.minor_str, to_version=hop.minor_str,
                                  rationale="control plane moves one minor at a time"))
            steps.append(PlanStep(wave=wave, wave_name=name, action="upgrade-nodes", target="all node pools",
                                  from_version=prev.minor_str, to_version=hop.minor_str,
                                  rationale="keep kubelets within the supported skew; drain and roll pool by pool"))
            for c in slot.get(hop.minor_str, []):
                steps.append(self._component_step(
                    wave, name, c, f"{c.target_version} first supports Kubernetes {hop.minor_str}; "
                                   "upgrade right after the nodes, before the next hop"))
            prev = hop

        ctx.plan = steps
        return f"{len(steps)} steps in {wave} waves"

    @staticmethod
    def _component_step(wave: int, wave_name: str, c: ComponentUpgrade, why: str) -> PlanStep:
        return PlanStep(wave=wave, wave_name=wave_name, action="upgrade-addon", target=c.name,
                        from_version=c.current_version, to_version=c.target_version, rationale=why)
