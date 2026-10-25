# Adding a target

A target teaches Ascendra to upgrade one kind of platform. The shared Risk, Rehearsal and Reporter
agents come for free; you write the domain agents.

1. Create `src/ascendra/targets/<name>/__init__.py` with a `Target` subclass:

   ```python
   class LinuxTarget(Target):
       name = "linux"
       title = "Linux OS"
       status = "available"
       description = "Distribution upgrades and patching"

       def domain_agents(self, options):
           return [LinuxScout(...), LinuxCompatibility(...), AdvisoryResearcher(...), RollingPlanner(...)]

       def cli(self):   # optional: exposes `ascendra linux plan ...`
           ...
   ```

2. Your agents fill the generic context:
   - `ctx.current_version` / `ctx.target_version` for the platform (e.g. `22.04` -> `24.04`)
   - `ctx.components`: one `ComponentUpgrade` per package, driver, VIB... with `changes` for the Risk agent
   - `ctx.findings`: blockers and warnings, with a `fix` when you know it
   - `ctx.plan`: ordered `PlanStep`s grouped in waves
   - anything raw in `ctx.inventory`
3. Register it in `src/ascendra/targets/__init__.py`.
4. Read config from your own section of `ascendra.yaml` via `Config.section("<name>")`.
5. Add fixtures and tests that run fully offline.

Rule of thumb: facts in code, judgement in LLM agents, and every agent must still work without an LLM.
