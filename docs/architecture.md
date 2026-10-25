# Architecture

## Core and targets

```
src/ascendra/
├── models.py          generic blackboard: UpgradeContext, ComponentUpgrade, Finding, PlanStep...
├── orchestrator.py    runs agents in order, records the trace
├── pipeline.py        target agents + shared agents, CLI output and exit codes
├── llm.py             Anthropic / OpenAI-compatible backends, JSON-only answers
├── versions.py        version parsing and constraint matching
├── agents/            shared, target-agnostic agents: risk, rehearsal, reporter
└── targets/
    ├── base.py        the Target plugin contract
    ├── kubernetes/    scout, compatibility, researcher, planner + Helm/kubectl sources
    ├── linux/         planned
    └── vmware/        planned
```

Every upgrade has the same shape whatever the platform: a **platform** moving from one version to another
(Kubernetes control plane, a Linux release, ESXi) and **components** running on it (Helm charts, packages,
VIBs) that must stay compatible along the way. The generic model captures exactly that, so the shared
agents work for every target. Raw, target-specific facts go into `UpgradeContext.inventory`.

## Blackboard pattern

Agents never call each other. They read and write the shared `UpgradeContext`. Each agent is testable in
isolation and the whole run is serialisable (`upgrade-plan.json`), the basis for audit, replay and evaluation.

## Agent contract

```python
class Agent:
    name: str
    role: str
    uses_llm: bool
    def run(self, ctx: UpgradeContext) -> str: ...   # returns a one-line summary
```

An agent may raise `SkipAgent` (not applicable) or `Degraded` (output produced with a weaker strategy,
e.g. heuristics instead of an LLM). Any other exception stops the pipeline.

## Where LLMs are allowed

| Question | Who answers |
|---|---|
| Is `batch/v1beta1 CronJob` served by Kubernetes 1.25? | code (`deprecated_apis.yaml`) |
| Does chart 4.12.0 accept Kubernetes 1.32? | code (Helm `kubeVersion` constraint) |
| In which order must things happen? | code (Planner) |
| Is "default for enableCertificateOwnerRef changed" dangerous for *us*? | LLM (Risk) |
| What should the team lead read first? | LLM (Risk executive summary) |

## Execution model

v0.1 is a linear pipeline. The target model is a supervisor that can loop with bounded iterations,
for example Rehearsal fails, so the Planner re-plans with the failure as new evidence.
