# OPERATIONS_RUNBOOK

## 1. Health Check

```bash
uv run binliquid doctor --profile balanced
```

## 2. Functional Smoke

```bash
uv run binliquid chat --profile balanced --once "3 adım plan ver"
uv run binliquid benchmark smoke --mode A --profile balanced --task-limit 1
```

## 3. Full Ablation

```bash
uv run binliquid benchmark ablation --mode all --profile balanced
```

## 4. Energy Check

```bash
uv run binliquid benchmark energy --profile balanced --energy-mode measured
```

If permission is unavailable, verify deterministic measured error detail in JSON output.

## 5. Research Calibration

```bash
uv run binliquid research train-router --dataset .binliquid/research/router_dataset.jsonl
uv run binliquid research eval-router --dataset .binliquid/research/router_dataset.jsonl
```

## 6. Incident Hints

- Planner parse fallback spikes: inspect debug traces under `.binliquid/traces/`
- Repeated expert failures: inspect circuit breaker events in telemetry
- Unexpected memory growth: check TTL and prune behavior via `memory stats`
