"""Kubernetes target: control plane, node pools and Helm add-ons."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from ascendra.agents import Agent
from ascendra.config import Config
from ascendra.llm import build_llm
from ascendra.models import UpgradeContext
from ascendra.targets.base import Target
from ascendra.targets.kubernetes.compatibility import CompatibilityAgent
from ascendra.targets.kubernetes.config import KubernetesConfig
from ascendra.targets.kubernetes.planner import PlannerAgent
from ascendra.targets.kubernetes.researcher import ResearcherAgent
from ascendra.targets.kubernetes.scout import ScoutAgent, ScoutInputs


class KubernetesTarget(Target):
    name = "kubernetes"
    aliases = ("k8s",)
    title = "Kubernetes"
    status = "available"
    description = "Control plane, node pools and Helm add-ons, one minor version at a time"

    def domain_agents(self, options: dict[str, Any]) -> list[Agent]:
        cfg: KubernetesConfig = options.get("config") or KubernetesConfig()
        live = options.get("live", True)
        return [
            ScoutAgent(ScoutInputs(live=live, current_version=options.get("current_version"),
                                   manifest_paths=options.get("manifests") or [],
                                   helm_releases_file=options.get("helm_releases"),
                                   ignore_releases=cfg.ignore_releases)),
            CompatibilityAgent(),
            ResearcherAgent(cfg.charts, discover_repos=live, allow_prerelease=cfg.allow_prerelease_charts),
            PlannerAgent(),
        ]

    def cli(self) -> typer.Typer:
        app = typer.Typer(help=self.description, no_args_is_help=True)

        @app.command()
        def plan(
            target: Annotated[str, typer.Option("--target", "-t", help="Target Kubernetes version, e.g. 1.32")],
            config: Annotated[Path | None, typer.Option("--config", "-c", exists=True,
                                                        help="ascendra.yaml")] = None,
            current_version: Annotated[str | None, typer.Option(help="Skip discovery of the version")] = None,
            manifests: Annotated[list[Path] | None, typer.Option(
                "--manifests", "-m", exists=True, help="Manifest file/dir to scan (repeatable)")] = None,
            helm_releases: Annotated[Path | None, typer.Option(
                exists=True, help="Output of `helm list -A -o json`")] = None,
            offline: Annotated[bool, typer.Option(help="Do not call kubectl/helm; use only files")] = False,
            no_llm: Annotated[bool, typer.Option("--no-llm", help="Deterministic heuristics only")] = False,
            out: Annotated[Path, typer.Option("--out", "-o")] = Path("ascendra-out"),
        ) -> None:
            """Analyse the cluster and produce an agent-reviewed upgrade plan. Read-only."""
            from ascendra.pipeline import run_cli_pipeline

            cfg = Config.load(config)
            kcfg = KubernetesConfig.model_validate(cfg.section(self.name))
            agents = self.domain_agents({"config": kcfg, "live": not offline, "current_version": current_version,
                                         "manifests": manifests, "helm_releases": helm_releases})
            ctx = UpgradeContext(target=self.name, subject=kcfg.cluster, target_version=target)
            run_cli_pipeline(ctx, agents, None if no_llm else build_llm(cfg.llm), out)

        return app
