# OPERATIONS_RUNBOOK

## 1. Resolve Config

```bash
uv run binliquid config resolve --profile balanced --json
```

## 2. Health Check

```bash
uv run binliquid doctor --profile balanced
```

## 3. Functional Smoke

```bash
uv run binliquid chat --profile balanced --once "selam" --stream --fast-path
uv run binliquid benchmark smoke --mode all --profile balanced
```

## 4. Quality Ablation

```bash
uv run binliquid benchmark ablation --mode all --profile balanced --suite quality
```

## 5. Energy Check

```bash
uv run binliquid benchmark energy --profile balanced --energy-mode measured
```

If measured mode cannot run due permissions, confirm deterministic `error_reason` in JSON output.

## 6. Research Calibration

```bash
uv run binliquid research train-router --dataset .binliquid/research/router_dataset.jsonl
uv run binliquid research eval-router --dataset .binliquid/research/router_dataset.jsonl
```

## 7. Artifact Verification

Check that all files exist:

- `artifacts/status.json`
- `artifacts/test_summary.json`
- `artifacts/benchmark_summary.json`
- `artifacts/router_shadow_summary.json`
- `artifacts/research_summary.json`

## 8. Incident Hints

- Planner fallback spikes: inspect `planner_parse_fail_rate` and `planner_fallback_rate`.
- Router drift: inspect `router_shadow_agreement_rate` and disagreement samples.
- Fast-path quality drift: inspect `fast_path_regret_rate`.
- Unexpected memory growth: verify `memory_ttl_days`, dedup hits, prune behavior.
