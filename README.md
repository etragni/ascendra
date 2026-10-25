<div align="center">

# ▲ Ascendra

**Agentic infrastructure upgrades.**
*Your infrastructure, always ascending.*

[![ci](https://github.com/evantragni/ascendra/actions/workflows/ci.yaml/badge.svg)](https://github.com/evantragni/ascendra/actions/workflows/ci.yaml)
![license](https://img.shields.io/badge/license-Apache%202.0-blue)
![status](https://img.shields.io/badge/status-v0.1%20early-orange)

</div>

Upgrading infrastructure is a climb: Kubernetes every few months, Linux fleets, VMware estates, each with
its own compatibility matrix, changelogs and failure modes. Ascendra hands that climb to a crew of AI agents,
each owning one step, while keeping humans in charge of every change.

> **v0.1 is read-only.** Ascendra analyses and plans. It never mutates your infrastructure.

## Targets

| Target | Status | What it upgrades |
|---|---|---|
| `kubernetes` | ✅ available | Control plane, node pools and Helm add-ons, one minor version at a time |
| `linux` | 🗺️ planned | Distribution upgrades and patching for cloud and on-prem machines |
| `vmware` | 🗺️ planned | vCenter and ESXi hosts, cluster by cluster |

Every target plugs domain agents into the same shared core, so a new platform is a plugin, not a rewrite.

## How it works

```
              ┌─────────────── target-specific agents ───────────────┐   ┌──────────── shared agents ────────────┐
 platform ──▶ │ Scout ─▶ Compatibility ─▶ Researcher ─▶ Planner       │──▶│ Risk ─▶ Rehearsal ─▶ Reporter         │──▶ plan.md / PR
              └───────────────────────────────────────────────────────┘   └───────────────────────────────────────┘
               inventory   removed APIs,     component      ordered          LLM       ephemeral     Markdown
                           version skew      versions,      waves            judgement dry-run       + JSON
                                             changelogs                                (v0.2)
```

| Agent | Scope | Responsibility | LLM |
|---|---|---|---|
| **Scout** | target | Inventory: platform version, nodes or hosts, components, objects in use | no |
| **Compatibility** | target | Removed APIs, version skew, unsupported upgrade paths | no |
| **Researcher** | target | Newest component version compatible with the target platform, plus changelogs | no |
| **Planner** | target | Ordered waves that respect skew rules and each component's compatibility window | no |
| **Risk** | shared | Reads changelogs and findings, judges risk per component, writes the executive summary | **yes** |
| **Rehearsal** | shared | Replays the plan on an ephemeral environment *(v0.2)* | planned |
| **Reporter** | shared | Renders the plan as a reviewable Markdown checklist and JSON | no |

### Design principles

1. **Facts are deterministic, judgement is agentic.** Version math, API removals and compatibility constraints
   are computed in code. LLMs interpret changelogs, weigh risk and explain. An LLM never decides whether an API exists.
2. **Agents propose, humans approve.** Output is a plan (and soon a GitOps pull request), never a silent change.
3. **Graceful degradation.** Without an LLM every agent still works, with transparent heuristics.
4. **Sovereign by design.** Any OpenAI-compatible endpoint works, so Ascendra can run fully on-prem with open-weight models.
5. **Auditable.** Every run records which agent did what, with what result, in the plan itself.

## Quickstart

```bash
pip install -e .                 # Python 3.11+
ascendra targets                 # what can be upgraded
ascendra agents kubernetes       # meet the crew

# Offline demo, no cluster needed
ascendra kubernetes plan --target 1.32 --offline --current-version 1.29.4 \
  --config examples/ascendra.yaml --helm-releases examples/helm-releases.json \
  --manifests examples/manifests --no-llm
cat ascendra-out/upgrade-plan.md

# Against your current kube-context (read-only: kubectl get, helm list/get)
ascendra k8s plan --target 1.32 --config ascendra.yaml --manifests ./gitops-repo
```

### LLM backends

```bash
# Claude
export ANTHROPIC_API_KEY=...
# Any OpenAI-compatible endpoint (vLLM, Ollama, LiteLLM...), e.g. fully local:
export ASCENDRA_LLM_PROVIDER=openai ASCENDRA_LLM_BASE_URL=http://localhost:11434/v1 ASCENDRA_LLM_MODEL=qwen2.5:32b
```

Exit codes: `0` no blockers, `1` blockers found, `2` pipeline error. Handy in CI.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md): rehearsal and verification on ephemeral environments, GitOps pull
requests, then the Linux and VMware targets.

## Contributing

Issues and PRs are welcome, see [CONTRIBUTING.md](CONTRIBUTING.md) and the guide to
[adding a target](docs/adding-a-target.md). An easy first contribution: extend the Kubernetes
[`deprecated_apis.yaml`](src/ascendra/targets/kubernetes/data/deprecated_apis.yaml).

## License

Apache 2.0 © Evangelista Tragni
