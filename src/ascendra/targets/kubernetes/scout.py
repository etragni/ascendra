"""Scout: builds the inventory. Cluster version, nodes, Helm releases and every API object we can see."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ascendra.agents.base import Agent
from ascendra.models import UpgradeContext
from ascendra.targets.kubernetes.models import nodes, objects, releases
from ascendra.targets.kubernetes.sources import cluster
from ascendra.targets.kubernetes.sources.manifests import parse_manifest_text, scan_paths


@dataclass
class ScoutInputs:
    live: bool = True
    current_version: str | None = None
    manifest_paths: list[Path] = field(default_factory=list)
    helm_releases_file: Path | None = None
    ignore_releases: list[str] = field(default_factory=list)


class ScoutAgent(Agent):
    name = "scout"
    role = "Inventories the cluster: version, nodes, Helm releases and API objects in use"

    def __init__(self, inputs: ScoutInputs) -> None:
        self.inputs = inputs

    def run(self, ctx: UpgradeContext) -> str:
        i = self.inputs
        ctx.current_version = i.current_version or (cluster.server_version() if i.live else None)
        if not ctx.current_version:
            raise ValueError("current Kubernetes version unknown: pass --current-version or use a live cluster")

        found = []
        if i.helm_releases_file:
            found = cluster.releases_from_helm_list(json.loads(i.helm_releases_file.read_text()))
        elif i.live:
            found = cluster.helm_releases()
        releases(ctx).extend(r for r in found if f"{r.namespace}/{r.name}" not in i.ignore_releases)

        if i.live:
            nodes(ctx).extend(cluster.nodes())
            for r in releases(ctx):
                objects(ctx).extend(parse_manifest_text(cluster.helm_manifest(r), f"helm:{r.namespace}/{r.name}"))
        objects(ctx).extend(scan_paths(i.manifest_paths))

        return (f"Kubernetes {ctx.current_version}, {len(nodes(ctx))} nodes, "
                f"{len(releases(ctx))} Helm releases, {len(objects(ctx))} objects")
