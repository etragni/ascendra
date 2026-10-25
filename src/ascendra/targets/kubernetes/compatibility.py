"""Compatibility analyst: deterministic checks that must never be left to an LLM."""
from __future__ import annotations

from importlib import resources

import yaml

from ascendra.agents.base import Agent
from ascendra.models import Finding, Severity, UpgradeContext
from ascendra.targets.kubernetes.models import nodes, objects
from ascendra.versions import Version


def load_removed_apis() -> list[dict]:
    text = resources.files("ascendra.targets.kubernetes.data").joinpath("deprecated_apis.yaml").read_text()
    return yaml.safe_load(text)


class CompatibilityAgent(Agent):
    name = "compatibility"
    role = "Detects removed APIs and version-skew violations against the target version"

    def __init__(self) -> None:
        self.removed = load_removed_apis()

    def _lookup(self, api_version: str, kind: str) -> dict | None:
        for rule in self.removed:
            if rule["api_version"] == api_version and rule["kind"] in (kind, "*"):
                return rule
        return None

    def run(self, ctx: UpgradeContext) -> str:
        current, target = Version.parse(ctx.current_version), Version.parse(ctx.target_version)
        if target < Version(current.major, current.minor):
            raise ValueError(f"target {target.minor_str} is older than current {current.minor_str}")

        seen: set[tuple] = set()
        for obj in objects(ctx):
            rule = self._lookup(obj.api_version, obj.kind)
            if not rule:
                continue
            removed_in = Version.parse(rule["removed_in"])
            if removed_in > Version(target.major, target.minor):
                continue
            key = (obj.api_version, obj.kind, obj.namespace, obj.name, obj.source)
            if key in seen:
                continue
            seen.add(key)
            already = removed_in <= Version(current.major, current.minor)
            ns = f"{obj.namespace}/" if obj.namespace else ""
            ctx.findings.append(Finding(
                severity=Severity.BLOCKER,
                category="deprecated-api",
                component=f"{obj.kind} {ns}{obj.name}",
                message=(f"{obj.api_version} {obj.kind} was removed in {rule['removed_in']}"
                         + (" (already removed on the current version, the source is stale)" if already else "")),
                source=obj.source,
                fix=f"migrate to {rule['replacement']}",
                found_by=self.name,
            ))

        hops = target.minor - current.minor
        if hops > 1:
            ctx.findings.append(Finding(
                severity=Severity.INFO, category="version-skew", component="control-plane",
                message=f"{hops} minor versions to go: the control plane must be upgraded one minor at a time",
                found_by=self.name))

        for node in nodes(ctx):
            kv = Version.try_parse(node.kubelet_version)
            if kv and current.minor - kv.minor > 0:
                ctx.findings.append(Finding(
                    severity=Severity.WARNING, category="version-skew", component=f"node {node.name}",
                    message=f"kubelet {node.kubelet_version} lags the control plane {current.minor_str}; "
                            "nodes must catch up before the control plane can move past the allowed skew",
                    found_by=self.name))

        n = sum(1 for f in ctx.findings if f.found_by == self.name and f.severity == Severity.BLOCKER)
        return f"{n} removed-API blockers, {hops} control-plane hop(s)"
