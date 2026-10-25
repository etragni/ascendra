"""Release researcher: finds the right target version for every Helm add-on and gathers its changelog."""
from __future__ import annotations

import httpx
import yaml

from ascendra.agents.base import Agent, Degraded
from ascendra.models import ComponentUpgrade, Finding, Severity, UpgradeContext
from ascendra.targets.kubernetes.models import HelmRelease, releases
from ascendra.targets.kubernetes.sources import cluster
from ascendra.targets.kubernetes.sources.helmrepo import HelmRepoIndex
from ascendra.versions import Version, supports_minor

CHANGES_ANNOTATION = "artifacthub.io/changes"
MAX_CHANGES = 40


def parse_changes(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return [raw.strip()]
    out = []
    for item in data or []:
        if isinstance(item, dict):
            out.append(f"[{item.get('kind', 'change')}] {item.get('description', '').strip()}")
        else:
            out.append(str(item).strip())
    return out


class ResearcherAgent(Agent):
    name = "researcher"
    role = "Picks, per Helm add-on, the newest chart version that supports the target Kubernetes; collects changes"

    def __init__(self, charts: dict[str, str], discover_repos: bool, allow_prerelease: bool = False,
                 index: HelmRepoIndex | None = None) -> None:
        self.charts = charts
        self.discover_repos = discover_repos
        self.allow_prerelease = allow_prerelease
        self.index = index or HelmRepoIndex()
        self._repos: dict[str, str] | None = None

    def _repo_for(self, r: HelmRelease) -> str | None:
        if r.chart in self.charts:
            return self.charts[r.chart]
        if r.repo_url:
            return r.repo_url
        if self.discover_repos:
            if self._repos is None:
                self._repos = cluster.helm_repos()
            for url in self._repos.values():
                if self.index.has_chart(url, r.chart):
                    return url
        return None

    def run(self, ctx: UpgradeContext) -> str:
        current = Version.parse(ctx.current_version)
        target = Version.parse(ctx.target_version)
        rels = releases(ctx)
        unresolved = 0
        for r in rels:
            comp = ComponentUpgrade(name=f"{r.namespace}/{r.name}", kind="helm-chart", package=r.chart,
                                    current_version=r.chart_version,
                                    attributes={"release": r.name, "namespace": r.namespace})
            ctx.components.append(comp)
            repo = self._repo_for(r)
            if not repo:
                unresolved += 1
                comp.note = "Helm repository unknown: add it under `kubernetes.charts` in ascendra.yaml"
                ctx.findings.append(Finding(severity=Severity.WARNING, category="component-compat",
                                            component=comp.name, message=comp.note, found_by=self.name))
                continue
            try:
                entries = self.index.entries(repo, r.chart, self.allow_prerelease)
            except (OSError, ValueError, KeyError, httpx.HTTPError, yaml.YAMLError) as e:
                unresolved += 1
                comp.note = f"could not read Helm repo index: {e}"
                continue

            cur_v = Version.try_parse(r.chart_version)
            cur_entry = next((e for e in entries if cur_v and e["_v"] == cur_v), None)
            if cur_entry:
                comp.attributes["current_kube_constraint"] = cur_entry.get("kubeVersion")
                comp.blocks_platform_upgrade = not supports_minor(target, cur_entry.get("kubeVersion"))

            compatible = [e for e in entries if supports_minor(target, e.get("kubeVersion"))]
            if not compatible:
                comp.note = f"no chart version declares support for Kubernetes {target.minor_str}"
                ctx.findings.append(Finding(severity=Severity.BLOCKER, category="component-compat",
                                            component=comp.name, message=comp.note, found_by=self.name))
                continue

            best = compatible[0]
            comp.target_version = best["version"]
            comp.attributes["target_kube_constraint"] = best.get("kubeVersion")
            comp.needs_newer_platform = not supports_minor(current, best.get("kubeVersion"))
            comp.major_jump = bool(cur_v and best["_v"].major > cur_v.major)
            for e in entries:
                if cur_v and cur_v < e["_v"] <= best["_v"]:
                    comp.changes += [f"{e['version']}: {c}" for c in
                                     parse_changes((e.get("annotations") or {}).get(CHANGES_ANNOTATION))]
            comp.changes = comp.changes[:MAX_CHANGES]

            if comp.blocks_platform_upgrade:
                ctx.findings.append(Finding(
                    severity=Severity.WARNING, category="component-compat", component=comp.name,
                    message=f"{r.chart} {r.chart_version} does not declare support for {target.minor_str}; "
                            f"upgrade to {comp.target_version} is required", found_by=self.name))

        summary = f"{len(rels) - unresolved}/{len(rels)} add-ons resolved"
        if unresolved:
            raise Degraded(summary)
        return summary
