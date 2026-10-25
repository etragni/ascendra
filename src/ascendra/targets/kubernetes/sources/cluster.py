"""Read-only access to a live cluster through kubectl and helm. ascendra never mutates the cluster in v0.1."""
from __future__ import annotations

import json
import re
import shutil
import subprocess

from ascendra.targets.kubernetes.models import HelmRelease, Node

_CHART_RE = re.compile(r"^(.*)-(v?\d+\.\d+.*)$")


class ToolError(RuntimeError):
    pass


def _run(*args: str) -> str:
    if shutil.which(args[0]) is None:
        raise ToolError(f"`{args[0]}` not found on PATH")
    proc = subprocess.run(args, check=False, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise ToolError(f"{' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def split_chart(chart: str) -> tuple[str, str]:
    """'cert-manager-v1.14.4' -> ('cert-manager', 'v1.14.4')"""
    m = _CHART_RE.match(chart)
    return (m.group(1), m.group(2)) if m else (chart, "")


def server_version() -> str:
    data = json.loads(_run("kubectl", "version", "-o", "json"))
    return data["serverVersion"]["gitVersion"]


def nodes() -> list[Node]:
    data = json.loads(_run("kubectl", "get", "nodes", "-o", "json"))
    return [
        Node(name=n["metadata"]["name"], kubelet_version=n["status"]["nodeInfo"]["kubeletVersion"])
        for n in data.get("items", [])
    ]


def releases_from_helm_list(items: list[dict]) -> list[HelmRelease]:
    out = []
    for r in items:
        chart, version = split_chart(r["chart"])
        out.append(
            HelmRelease(
                name=r["name"],
                namespace=r["namespace"],
                chart=chart,
                chart_version=version,
                app_version=r.get("app_version"),
                repo_url=r.get("repo") or r.get("repo_url"),
            )
        )
    return out


def helm_releases() -> list[HelmRelease]:
    return releases_from_helm_list(json.loads(_run("helm", "list", "-A", "-o", "json")))


def helm_manifest(release: HelmRelease) -> str:
    return _run("helm", "get", "manifest", release.name, "-n", release.namespace)


def helm_repos() -> dict[str, str]:
    try:
        return {r["name"]: r["url"] for r in json.loads(_run("helm", "repo", "list", "-o", "json"))}
    except (ToolError, json.JSONDecodeError):
        return {}
