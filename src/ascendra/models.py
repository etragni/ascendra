"""Target-agnostic data model. Agents communicate only through the UpgradeContext (a blackboard).

Every upgrade, whatever the platform, has the same shape: a *platform* (Kubernetes control plane,
a Linux distribution, an ESXi host...) moving from one version to another, plus *components* running
on it (Helm charts, packages, VIBs...) that must stay compatible along the way. Target-specific raw
facts live in `inventory`; everything the shared agents (Risk, Reporter...) need is generic.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Finding(BaseModel):
    severity: Severity
    category: str  # deprecated-api | version-skew | component-compat | ...
    component: str
    message: str
    source: str | None = None
    fix: str | None = None
    found_by: str


class ComponentUpgrade(BaseModel):
    """Something running on the platform that has its own version: a Helm chart, an OS package, a VIB..."""

    name: str  # unique within the run, e.g. "cert-manager/cert-manager"
    kind: str  # helm-chart | package | ...
    package: str  # chart / package name
    current_version: str
    target_version: str | None = None
    # the current version does not support the target platform version: upgrade it before (or during) the hops
    blocks_platform_upgrade: bool = False
    # the target version needs a newer platform than the current one: upgrade it during the hops
    needs_newer_platform: bool = False
    major_jump: bool = False
    changes: list[str] = Field(default_factory=list)
    note: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)  # target-specific, e.g. kubeVersion constraints


class RiskAssessment(BaseModel):
    component: str
    level: RiskLevel
    summary: str
    breaking_changes: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    assessed_by: str = "heuristic"


class PlanStep(BaseModel):
    wave: int
    wave_name: str
    action: str  # e.g. migrate-manifest | upgrade-component | upgrade-control-plane | upgrade-nodes
    target: str
    from_version: str | None = None
    to_version: str | None = None
    rationale: str


class AgentRun(BaseModel):
    agent: str
    status: str  # ok | degraded | skipped | failed
    detail: str = ""
    seconds: float = 0.0


class UpgradeContext(BaseModel):
    target: str  # which target plugin produced this run: kubernetes | linux | vmware ...
    subject: str = "unnamed"  # cluster name, host group, vCenter...
    current_version: str | None = None
    target_version: str
    inventory: dict[str, Any] = Field(default_factory=dict)
    components: list[ComponentUpgrade] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    risks: list[RiskAssessment] = Field(default_factory=list)
    plan: list[PlanStep] = Field(default_factory=list)
    executive_summary: str | None = None
    runs: list[AgentRun] = Field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.BLOCKER]
