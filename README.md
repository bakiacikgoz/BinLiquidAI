# BinLiquid (AegisOS)

BinLiquid is a private, security-first agentic runtime designed to run fully local/offline in enterprise-controlled environments, including on-prem datacenters and edge deployments.

It provides two layers:

- **BinLiquid Runtime (core):** the production-grade foundation for single-assistant execution, including planning, routing, specialist execution, scoped memory, and governance.
- **Team Runtime:** a governed multi-agent execution layer that supports delegated task handoff, shared/scoped memory access, approval-gated actions, bounded-concurrency controls, and audit-grade replayable traces.

> **Status:**
> BinLiquid core is production-grade.
> Team Runtime is pilot-hardened for controlled/restricted profiles, with release-blocking gates, replay verification, approval hardening, and bounded-concurrency safeguards.
> Enterprise deployment readiness is implemented under defined constraints through secure defaults, verified identity/RBAC gates, asymmetric artifact signing, operational support bundles, and GA readiness reporting.
> Broader GA claims still require published qualification evidence from the documented deployment envelope.

## Current Status

### Core Runtime

The core runtime is the most mature part of the system and should be considered the production-grade foundation of the platform.

### Team Runtime

Team Runtime has completed pilot-readiness hardening for restricted, controlled profiles and currently includes:

- deterministic release-blocking pilot gate
- approval lifecycle hardening (`pending -> approved -> executed -> consumed`)
- stale approval snapshot detection
- duplicate resume suppression / idempotent resume claims
- optimistic shared-memory conflict rejection
- concurrency-aware audit/replay metadata
- bounded-concurrency fallback / serialization events
- restricted smoke scenarios and machine-readable pilot reports
- release-gate, runbook, rollback, and messaging alignment

Under restricted pilot profiles, Team Runtime now provides fail-closed approval handling, audit-grade event trails, replay verification, bounded-concurrency safety controls, visible fallback/serialization behavior, and conflict rejection instead of silent shared-state overwrite.

Team Runtime should currently be described as:

- pilot-ready under controlled/restricted profiles
- bounded-concurrency capable with safety degradation
- governable and auditable by design

Team Runtime should not yet be described as:

- unrestricted enterprise-wide multi-agent orchestration
- fully general high-concurrency agent execution
- universally production-ready across arbitrary live-provider environments

### Enterprise Profile

The `enterprise` profile is the self-hosted secure-default path for single-tenant deployment and adds:

- verified identity assertions plus RBAC checks for mutating operations
- asymmetric signing for audit and operational artifacts
- security baseline preflight and startup abort rules
- backup, restore verification, migration planning, and support bundle export
- file-based metrics snapshots and GA readiness reporting

This slice formalizes the deployment contract. It does not replace qualification evidence. Enterprise positioning remains bounded by the published qualification matrix and executed drills.

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
| Team Runtime v0.4 (DAG + bounded concurrency + handoff/memory governance) | pilot-hardened under restricted profile | bounded-concurrency safeguards, replay verification, and pilot usage only behind `team pilot-check` plus target-environment live-provider rehearsal |
| Desktop UI (Tauri operator panel) | beta | `apps/operator-panel` (macOS-first) |

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
| `restricted` (controlled pilot profile) | rule | sltc | on | on | short |
| `enterprise` (self-hosted secure default) | rule | sltc | on | on | signed + file metrics |

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
uv run binliquid approval show --id <approval_id> --json
uv run binliquid approval decide --id <approval_id> --approve --actor ops-user
uv run binliquid approval execute --id <approval_id> --actor ops-user
uv run binliquid operator capabilities --json
```

Approval lifecycle is `pending -> approved -> executed -> consumed`.
`approved` alone does not authorize override use; team resume and pilot gate only consume `executed` approvals.

Enterprise validation:

```bash
uv run python scripts/prepare_enterprise_fixture.py --root .
uv run binliquid auth whoami --profile enterprise --json
uv run binliquid auth check --profile enterprise --permission runtime.run --json
uv run binliquid security baseline --profile enterprise --json
uv run binliquid metrics snapshot --profile enterprise --json
uv run binliquid ga readiness --profile enterprise --report artifacts/ga_readiness_report.json --json
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
uv run binliquid team list --root-dir .binliquid/team/jobs --json
uv run binliquid team logs --job-id <id> --root-dir .binliquid/team/jobs --json-stream
uv run binliquid team replay --job-id <id> --root-dir .binliquid/team/jobs --verify --json
uv run binliquid team artifacts --job-id <id> --root-dir .binliquid/team/jobs --export ./team-artifacts
uv run binliquid team pilot-check --spec examples/team/restricted_pilot.yaml --profile restricted --mode deterministic --report artifacts/team_pilot_report.json --json
uv run binliquid team pilot-check --spec examples/team/restricted_pilot_live.yaml --profile restricted --mode live-provider --provider auto --report artifacts/team_pilot_live_report.json --json
```

### Operator Panel (v0.5.0-beta)

```bash
make ui-install
make ui-dev
```

Packaging and release scripts live under `apps/operator-panel/scripts/`.

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
- `security_posture.json`
- `metrics_snapshot.json`
- `ga_readiness_report.json`

## Privacy and Debug

- Default: `privacy_mode=true`
- Persistent traces only when debug is on and privacy is explicitly off
- Web access default: off

## Known Limits (v0.4.1)

- `transformers` fallback is for continuity, not quality parity.
- Measured energy depends on platform permissions (`powermetrics`).
- sLTC gains vary by workload distribution.
- UI thin shell is intentionally deferred to keep CLI reliability first.
- Model assets are not auto-installed (`ollama pull` remains operator-driven).
- Team runs intentionally fail-closed when governance requires approval in a blocking dependency chain.
- `team resume` and `team pilot-check` only consume approvals that are both `executed` and not yet `consumed`.
- approval-gated resume now freezes the execution contract; context drift raises `STALE_APPROVAL_SNAPSHOT` instead of silently continuing.
- shared `memory_target` writes use optimistic version checks and reject on conflict; there is no last-write-wins path in restricted pilot mode.
- approval-gated subtrees may serialize themselves under bounded fallback; those decisions are visible in audit/replay artifacts.
- `team replay --verify` checks event ordering, causal continuity, handoff consistency, and trace integrity; it does not guarantee business correctness or external side-effect validation.
- Enterprise deployment is scoped to self-hosted single-tenant environments; multi-tenant control plane and broad cloud-native integrations remain deferred.
- Enterprise artifacts require asymmetric signing; `BINLIQUID_AUDIT_SIGNING_KEY` remains compatibility-only and is not acceptable for enterprise mode.

## Documentation

- `docs/RELEASE_GATE_v0.5.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `SECURITY_BASELINE.md`
- `KEY_MANAGEMENT.md`
- `UPGRADE_AND_RECOVERY.md`
- `OBSERVABILITY_AND_SLO.md`
- `QUALIFICATION_MATRIX.md`
- `INSTALL.md`
- `DEPLOYMENT_GUIDE.md`
- `SUPPORT_BUNDLE.md`
