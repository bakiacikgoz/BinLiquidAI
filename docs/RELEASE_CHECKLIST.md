# RELEASE_CHECKLIST

## Quality Gates

- [ ] `uv run ruff check .`
- [ ] `uv run pytest -q`
- [ ] `uv run binliquid doctor --profile balanced`
- [ ] `uv run binliquid benchmark ablation --mode all --profile balanced --task-limit 2`
- [ ] `uv run binliquid benchmark energy --profile balanced --energy-mode measured`

## Research Gates

- [ ] `uv run binliquid research train-router --dataset .binliquid/research/router_dataset.jsonl`
- [ ] `uv run binliquid research eval-router --dataset .binliquid/research/router_dataset.jsonl`

## Artifact Checks

- [ ] JSON benchmark outputs exist in `benchmarks/results/`
- [ ] Markdown ablation report exists
- [ ] Router train/eval reports exist in `research/sltc_experiments/artifacts/`
- [ ] README command examples are current
