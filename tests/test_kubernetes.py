from pathlib import Path

from ascendra.models import ComponentUpgrade, RiskLevel, UpgradeContext
from ascendra.orchestrator import Orchestrator
from ascendra.pipeline import shared_agents
from ascendra.targets.kubernetes import KubernetesTarget
from ascendra.targets.kubernetes.config import KubernetesConfig
from ascendra.targets.kubernetes.planner import PlannerAgent

FIX = Path(__file__).parent / "fixtures"
REPO = str(FIX / "repo")


class FakeLLM:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def complete_json(self, system, user):
        self.calls += 1
        return {"executive_summary": "Fine.",
                "assessments": [{"component": "ops/legacy", "level": "high", "summary": "CRD migration"}]}


def run(tmp_path, target="1.32", llm=None):
    cfg = KubernetesConfig(charts={c: REPO for c in ("cert-manager", "ingress-nginx", "legacy-operator")})
    agents = KubernetesTarget().domain_agents({
        "config": cfg, "live": False, "current_version": "1.29.4",
        "manifests": [FIX / "manifests"], "helm_releases": FIX / "helm-releases.json"})
    ctx = UpgradeContext(target="kubernetes", subject="test", target_version=target)
    return Orchestrator(agents + shared_agents(llm, tmp_path)).run(ctx)


def test_removed_apis_are_blockers(tmp_path):
    ctx = run(tmp_path)
    kinds = sorted(f.component.split()[0] for f in ctx.blockers if f.category == "deprecated-api")
    assert kinds == ["CronJob", "FlowSchema", "PodDisruptionBudget"]


def test_flowschema_not_blocking_before_132(tmp_path):
    ctx = run(tmp_path, target="1.31")
    assert not any("FlowSchema" in f.component for f in ctx.blockers)


def test_plan_orders_addons_around_control_plane(tmp_path):
    ctx = run(tmp_path)
    by_target = {s.target: s for s in ctx.plan if s.action == "upgrade-addon"}
    cp_waves = [s.wave for s in ctx.plan if s.action == "upgrade-control-plane"]
    assert len(cp_waves) == 3
    assert by_target["cert-manager/cert-manager"].wave < min(cp_waves)
    assert by_target["cert-manager/cert-manager"].to_version == "v1.16.2"
    # legacy-operator 2.4.1 supports <1.32 and 3.0.0 needs >=1.31 -> inside the 1.31 hop, before 1.32
    legacy = by_target["ops/legacy"]
    assert legacy.wave_name == "Kubernetes 1.31"
    assert ctx.plan.index(legacy) > next(i for i, s in enumerate(ctx.plan)
                                          if s.action == "upgrade-nodes" and s.to_version == "1.31")


def test_heuristic_risk_and_report(tmp_path):
    ctx = run(tmp_path)
    levels = {r.component: r.level for r in ctx.risks}
    assert levels["ops/legacy"] == RiskLevel.HIGH  # major jump
    assert any(r.status == "degraded" and r.agent == "risk" for r in ctx.runs)
    assert (tmp_path / "upgrade-plan.md").read_text().startswith("# Upgrade plan: test (kubernetes)")
    assert '"helm_releases"' in (tmp_path / "upgrade-plan.json").read_text()  # inventory is serialised


def test_llm_risk(tmp_path):
    llm = FakeLLM()
    ctx = run(tmp_path, llm=llm)
    assert llm.calls == 1 and ctx.executive_summary == "Fine."
    assert ctx.risks[0].assessed_by == "fake"


def test_no_compatibility_window_is_blocker():
    ctx = UpgradeContext(target="kubernetes", current_version="1.29", target_version="1.32", components=[
        ComponentUpgrade(name="ns/x", kind="helm-chart", package="x", current_version="1.0.0", target_version="2.0.0",
                         needs_newer_platform=True,
                         attributes={"current_kube_constraint": "<1.30.0-0", "target_kube_constraint": ">=1.31.0-0"})])
    PlannerAgent().run(ctx)
    assert any("no compatible version window" in f.message for f in ctx.blockers)
