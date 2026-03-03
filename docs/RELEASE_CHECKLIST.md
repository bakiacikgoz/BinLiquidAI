# RELEASE_CHECKLIST

## Quality Gates

- [ ] `uv run ruff check .`
- [ ] `uv run pytest -q`
- [ ] `uv run binliquid config resolve --profile balanced --json`
- [ ] `uv run binliquid doctor --profile balanced`
- [ ] `uv run binliquid benchmark smoke --mode all --profile balanced`
- [ ] `uv run binliquid benchmark team --profile balanced --suite smoke --spec team.yaml`
- [ ] `uv run binliquid benchmark ablation --mode all --profile balanced --suite quality`
- [ ] `uv run binliquid benchmark energy --profile balanced --energy-mode measured`

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
- [ ] README command examples are current
