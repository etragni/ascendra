# Roadmap

## v0.1 (now): read-only planning, Kubernetes
- [x] Pluggable target architecture with a generic upgrade model
- [x] Kubernetes target: Scout, Compatibility, Researcher, Planner
- [x] Shared agents: Risk (LLM + heuristics), Reporter
- [x] Anthropic and OpenAI-compatible (on-prem) LLM backends; offline mode; CI exit codes

## v0.2: rehearse and verify
- [ ] **Rehearsal agent**: ephemeral cluster (kind / vcluster / hosted control plane) at the current version,
      install inventoried releases with their values, execute the plan wave by wave
- [ ] **Verifier agent**: workload health, events, failed probes; LLM explains failures
- [ ] Supervisor loop: re-plan on rehearsal failure (bounded)
- [ ] Release-notes agent: upstream GitHub releases when charts publish no changelog annotation
- [ ] Rendered manifest diff per add-on, fed to the Risk agent

## v0.3: act through GitOps, first new target
- [ ] **Publisher agent**: one PR per wave in the GitOps repo (Argo CD / Flux), plan as PR description
- [ ] Autonomy levels per environment (advise / PR / auto-merge in dev)
- [ ] Managed control planes: Cluster API, EKS, GKE, AKS, STACKIT SKE...
- [ ] **Linux target**: inventory via SSH / Ansible facts / cloud APIs, upgrade paths (Leapp, LTS to LTS),
      security advisories, rolling waves respecting service redundancy

## v0.4 and beyond
- [ ] **VMware target**: vCenter then ESXi hosts, maintenance mode and DRS evacuation, hardware compatibility
- [ ] Operator with `UpgradePlan` / `UpgradeRun` CRDs
- [ ] Eval harness: replay historical upgrades, measure plan correctness
