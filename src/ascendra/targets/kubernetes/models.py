"""Kubernetes-specific inventory, stored in UpgradeContext.inventory."""
from __future__ import annotations

from pydantic import BaseModel

from ascendra.models import UpgradeContext


class KubeObject(BaseModel):
    api_version: str
    kind: str
    name: str
    namespace: str | None = None
    source: str  # file path or "helm:<namespace>/<release>"


class HelmRelease(BaseModel):
    name: str
    namespace: str
    chart: str
    chart_version: str
    app_version: str | None = None
    repo_url: str | None = None


class Node(BaseModel):
    name: str
    kubelet_version: str


def nodes(ctx: UpgradeContext) -> list[Node]:
    return ctx.inventory.setdefault("nodes", [])


def releases(ctx: UpgradeContext) -> list[HelmRelease]:
    return ctx.inventory.setdefault("helm_releases", [])


def objects(ctx: UpgradeContext) -> list[KubeObject]:
    return ctx.inventory.setdefault("objects", [])
