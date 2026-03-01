# BinLiquid AI v0.2.0-beta

Offline-first, local-first hybrid assistant with a production-focused CLI core.

## Feature Status

| Feature | Status | Notes |
|---|---|---|
| Provider chain (`auto -> ollama -> transformers`) | working | `doctor` checks active + fallback chain |
| Planner strict schema + deterministic fallback | working | adversarial tests included |
| Orchestrator timeout/retry/circuit-breaker/tool budget | working | limit enforcement tested |
| Rule router (active) + sLTC shadow router | working | default in `balanced` |
| Fast-path + realtime stream | working | regret metrics enabled |
| Expert contracts (code/research/plan) | working | typed validation + partial failover |
| Memory v2 (dedup + TTL + ranked retrieval) | working | privacy-safe defaults |
| Benchmarks (smoke/ablation/energy) | working | quality suite (120 tasks) available |
| Router train/eval reproducibility scripts | working | JSON + Markdown artifacts |
| Desktop UI (Tauri thin shell) | deferred | v0.3 candidate |

## First 5 Minutes

```bash
make bootstrap
make install
uv run ruff check .
uv run pytest -q
uv run binliquid doctor --profile balanced
```

## Profiles

| Profile | Router | Shadow Router | Memory | Fallback | Telemetry |
|---|---|---|---|---|---|
| `lite` | rule | off | off | off | minimal |
| `balanced` (default daily) | rule | sltc | on | on | short |
| `research` | sltc | rule | on | on | debug-friendly |

## CLI Quickstart

### Chat

```bash
uv run binliquid chat --profile balanced --once "selam" --stream --fast-path
uv run binliquid chat --profile balanced --once "kodu düzelt" --no-fast-path
```

Structured output (thin-shell/UI ready):

```bash
uv run binliquid chat --profile balanced --once "selam" --json
uv run binliquid chat --profile balanced --once "selam" --json-stream --stream
uv run binliquid chat --profile balanced --once "selam" --stdio-json --stream
```

### Config resolve

```bash
uv run binliquid config resolve --profile balanced --json
uv run binliquid config resolve --profile balanced --provider ollama --fallback-provider transformers
```

Precedence order: `defaults < profile < env < CLI flags`.

### Benchmarks

```bash
uv run binliquid benchmark smoke --mode all --profile balanced
uv run binliquid benchmark ablation --mode all --profile balanced --suite smoke
uv run binliquid benchmark ablation --mode all --profile balanced --suite quality
uv run binliquid benchmark energy --profile balanced --energy-mode measured
```

### Memory

```bash
uv run binliquid memory stats --profile balanced
```

### Research

```bash
uv run binliquid research train-router \
  --dataset .binliquid/research/router_dataset.jsonl \
  --output-dir research/sltc_experiments/artifacts \
  --seed 42

uv run binliquid research eval-router \
  --dataset .binliquid/research/router_dataset.jsonl \
  --model research/sltc_experiments/artifacts/router_model.json \
  --output-dir research/sltc_experiments/artifacts
```

## Artifacts

`artifacts/` altında makine-okunur özetler yazılır:

- `status.json`
- `test_summary.json`
- `benchmark_summary.json`
- `router_shadow_summary.json`
- `research_summary.json`

## Privacy and Debug

- Default: `privacy_mode=true`
- Persistent traces only when debug is on and privacy is explicitly off
- Web access default: off

## Known Limits (v0.2)

- `transformers` fallback is for continuity, not quality parity.
- Measured energy depends on platform permissions (`powermetrics`).
- sLTC gains vary by workload distribution.
- UI thin shell is intentionally deferred to keep CLI reliability first.
