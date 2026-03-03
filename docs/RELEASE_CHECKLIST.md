# RELEASE_CHECKLIST

## Quality Gates

- [ ] `uv run ruff check .`
- [ ] `uv run pytest -q`
- [ ] `uv run binliquid config resolve --profile balanced --json`
- [ ] `uv run binliquid doctor --profile balanced`
- [ ] `uv run binliquid benchmark smoke --mode all --profile balanced`
- [ ] `uv run binliquid benchmark team --profile restricted --suite smoke --spec team.yaml --deterministic-mock`
- [ ] `uv run binliquid benchmark team --profile balanced --suite smoke --spec team.yaml`
- [ ] `uv run binliquid benchmark ablation --mode all --profile balanced --suite quality`
- [ ] `uv run binliquid benchmark energy --profile balanced --energy-mode measured`
- [ ] `uv run pytest -q tests/test_memory_concurrency.py`
- [ ] `uv run pytest -q tests/test_team_checkpoint_concurrency.py`

## Research Gates

- [ ] `uv run binliquid research train-router --dataset .binliquid/research/router_dataset.jsonl`
- [ ] `uv run binliquid research eval-router --dataset .binliquid/research/router_dataset.jsonl`

## Artifact Checks

- [ ] `artifacts/status.json` exists and valid JSON
- [ ] `artifacts/test_summary.json` exists and valid JSON
- [ ] `artifacts/benchmark_summary.json` exists and valid JSON
- [ ] `artifacts/router_shadow_summary.json` exists and valid JSON
- [ ] `artifacts/research_summary.json` exists and valid JSON
- [ ] `artifacts/team_summary.json` exists and valid JSON
- [ ] Benchmark JSON outputs exist under `benchmarks/results/`
- [ ] Ablation Markdown report exists
- [ ] Team run artifacts exist under `.binliquid/team/jobs/<job_id>/`
- [ ] `uv run binliquid team resume --spec team.yaml --job-id <id> --root-dir .binliquid/team/jobs --json` works when approvals are resolved
- [ ] README command examples are current
- [ ] Pre-production: one real provider team E2E run completed in target environment
