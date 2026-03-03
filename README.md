# AegisOS / BinLiquid v0.4.0

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
| Governance v0.4 (policy + approval + audit) | working | fail-closed + async approvals |
| Team Runtime v0.4 (DAG + parallel scheduler + handoff/memory governance) | working | `binliquid team *` command group |
| Desktop UI (Tauri thin shell) | deferred | post-v0.3 (operator panel is available) |

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
| `restricted` (regulated pilot) | rule | sltc | on | on | short |

## CLI Quickstart

### Chat

```bash
uv run binliquid chat --profile balanced --once "selam" --stream --fast-path
uv run binliquid chat --profile balanced --once "kodu düzelt" --no-fast-path
uv run binliquid chat --profile balanced --once "plan çıkar" --model qwen3.5:4b
```

Structured output (thin-shell/UI ready):

```bash
uv run binliquid chat --profile balanced --once "selam" --json
uv run binliquid chat --profile balanced --once "selam" --json-stream --stream
uv run binliquid chat --profile balanced --once "selam" --stdio-json --stream
```

Governance approvals:

```bash
uv run binliquid approval pending --json
uv run binliquid approval decide --id <approval_id> --approve --actor ops-user
uv run binliquid approval execute --id <approval_id> --actor ops-user
```

Operator panel (thin-shell terminal):

```bash
uv run binliquid operator panel --profile balanced
```

### Config resolve

```bash
uv run binliquid config resolve --profile balanced --json
uv run binliquid config resolve --profile balanced --provider ollama --fallback-provider transformers
uv run binliquid config resolve --profile balanced --provider auto --model qwen3.5:4b --hf-model-id Qwen/Qwen3.5-4B-Instruct
```

Precedence order: `defaults < profile < env < CLI flags`.

### Benchmarks

```bash
uv run binliquid benchmark smoke --mode all --profile balanced
uv run binliquid benchmark team --profile balanced --suite smoke --spec team.yaml
uv run binliquid benchmark team --profile restricted --suite smoke --spec team.yaml --deterministic-mock
uv run binliquid benchmark ablation --mode all --profile balanced --suite smoke
uv run binliquid benchmark ablation --mode all --profile balanced --suite quality
uv run binliquid benchmark energy --profile balanced --energy-mode measured
uv run binliquid benchmark smoke --mode A --profile balanced --provider auto --model qwen3.5:4b --hf-model-id Qwen/Qwen3.5-4B-Instruct
```

### Team Runtime

```bash
uv run binliquid team init --output team.yaml
uv run binliquid team init --output team-regulated.yaml --template regulated
uv run binliquid team validate --spec team.yaml --json
uv run binliquid team run --spec team.yaml --once "Build a compliance-aware rollout plan" --json
uv run binliquid team resume --spec team.yaml --job-id <blocked_job_id> --root-dir .binliquid/team/jobs --json
uv run binliquid team status --job-id <id> --root-dir .binliquid/team/jobs --json
uv run binliquid team logs --job-id <id> --root-dir .binliquid/team/jobs --json-stream
uv run binliquid team replay --job-id <id> --root-dir .binliquid/team/jobs
uv run binliquid team artifacts --job-id <id> --root-dir .binliquid/team/jobs --export ./team-artifacts
```

## Model Recipes

### 1) Varsayılan LFM (profile ile)

```bash
uv run binliquid chat --profile balanced --once "selam"
```

### 2) Ollama Qwen modeli

```bash
ollama pull qwen3.5:4b
uv run binliquid doctor --profile balanced --provider ollama --model qwen3.5:4b
uv run binliquid chat --profile balanced --provider ollama --model qwen3.5:4b --once "uzun plan çıkar"
```

### 3) Transformers custom model

```bash
uv run binliquid doctor --profile balanced --provider transformers --hf-model-id Qwen/Qwen3.5-4B-Instruct
uv run binliquid chat --profile balanced --provider transformers --hf-model-id Qwen/Qwen3.5-4B-Instruct --once "özetle"
```

### 4) Auto dual-target (Ollama primary + Transformers fallback)

```bash
uv run binliquid doctor --profile balanced --provider auto --model qwen3.5:4b --hf-model-id Qwen/Qwen3.5-4B-Instruct
uv run binliquid chat --profile balanced --provider auto --model qwen3.5:4b --hf-model-id Qwen/Qwen3.5-4B-Instruct --once "adım adım anlat"
```

### 5) Model yoksa teşhis

```bash
uv run binliquid doctor --profile balanced --provider ollama --model qwen3.5:4b
# model_present=false ise önce: ollama pull qwen3.5:4b
```

### 6) Override kaynağını görme

```bash
BINLIQUID_MODEL_NAME=qwen3.5:4b uv run binliquid config resolve --profile balanced --json
# source_map.model_name alanı env/cli/profile kaynağını gösterir
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

uv run binliquid research calibrate-router \
  --dataset .binliquid/research/router_dataset.jsonl \
  --output-dir research/sltc_experiments/artifacts \
  --seed 42
```

Calibration outputs:

- `research/sltc_experiments/artifacts/router_calibration_candidates.json`
- `research/sltc_experiments/artifacts/router_calibration_report.json`
- `research/sltc_experiments/artifacts/router_calibration_report.md`

## Artifacts

`artifacts/` altında makine-okunur özetler yazılır:

- `status.json`
- `test_summary.json`
- `benchmark_summary.json`
- `router_shadow_summary.json`
- `research_summary.json`
- `governance_summary.json`
- `team_summary.json`

## Privacy and Debug

- Default: `privacy_mode=true`
- Persistent traces only when debug is on and privacy is explicitly off
- Web access default: off

## Known Limits (v0.4.0)

- `transformers` fallback is for continuity, not quality parity.
- Measured energy depends on platform permissions (`powermetrics`).
- sLTC gains vary by workload distribution.
- UI thin shell is intentionally deferred to keep CLI reliability first.
- Model assets are not auto-installed (`ollama pull` remains operator-driven).
- Team runs intentionally fail-closed when governance requires approval in a blocking dependency chain.
- `team resume` depends on resolved approvals; unresolved/expired approvals keep runs blocked by design.
- Enterprise GA hardening is still in progress (scoped production-readiness pre-check only).
