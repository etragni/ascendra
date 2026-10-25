# Contributing to Ascendra

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

- Keep the rule: facts in code, judgement in LLM agents.
- New agents implement `ascendra.agents.base.Agent` and must work (degraded) without an LLM.
- New platforms are targets, see [docs/adding-a-target.md](docs/adding-a-target.md).
- Every behaviour change needs a test; fixtures live in `tests/fixtures` and tests run offline.
- Use Conventional Commits (`feat:`, `fix:`, `docs:`...).
