# OPERATIONS_RUNBOOK

## 1. Resolve Config

```bash
uv run binliquid config resolve --profile balanced --json
```

## 2. Health Check

```bash
uv run binliquid doctor --profile balanced
uv run binliquid doctor --profile balanced --provider auto --model qwen3.5:4b --hf-model-id Qwen/Qwen3.5-4B-Instruct
```

## 3. Functional Smoke

```bash
uv run binliquid chat --profile balanced --once "selam" --stream --fast-path
uv run binliquid chat --profile balanced --provider ollama --model qwen3.5:4b --once "uzun plan çıkar"
uv run binliquid benchmark smoke --mode all --profile balanced
```

## 4. Quality Ablation

```bash
uv run binliquid benchmark ablation --mode all --profile balanced --suite quality
```

## 5. Energy Check

```bash
uv run binliquid benchmark energy --profile balanced --energy-mode measured
uv run binliquid benchmark energy --profile balanced --energy-mode measured --provider auto --model qwen3.5:4b --hf-model-id Qwen/Qwen3.5-4B-Instruct
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

## 8. Operator Panel Compatibility Check

```bash
uv run binliquid --version
uv run binliquid operator capabilities --json
uv run binliquid team list --root-dir .binliquid/team/jobs --json
```

If capabilities contract or command flags are missing, keep UI mutations disabled.

## 9. Incident Hints

- Planner fallback spikes: inspect `planner_parse_fail_rate` and `planner_fallback_rate`.
- Router drift: inspect `router_shadow_agreement_rate` and disagreement samples.
- Fast-path quality drift: inspect `fast_path_regret_rate`.
- Unexpected memory growth: verify `memory_ttl_days`, dedup hits, prune behavior.

## 10. Team Runtime Pilot Runbook

### Preflight

Run the release-blocking gate before any controlled pilot:

```bash
uv run ruff check .
uv run pytest -q \
  tests/test_team_governance.py \
  tests/test_team_memory_fail_closed.py \
  tests/test_team_audit_envelope.py \
  tests/test_team_cli.py \
  tests/test_team_pilot_gate.py
uv run binliquid team validate --spec examples/team/restricted_pilot.yaml --json
uv run binliquid team pilot-check \
  --spec examples/team/restricted_pilot.yaml \
  --profile restricted \
  --mode deterministic \
  --report artifacts/team_pilot_report.json \
  --json
```

Gate outcome requirements:

- `team pilot-check` exits `0`.
- `artifacts/team_pilot_report.json` exists and reports `overall_status=pass`.
- clean `team replay --verify` passes for the smoke artifacts.
- tamper probe fails verification.
- approval reuse probe is blocked.
- scope isolation probe fails closed.
- bounded-concurrency checks report `stale_approval_count=0` and `memory_conflict_count=0`.

Approval lifecycle for Team Runtime is `pending -> approved -> executed -> consumed`.
`approved` alone is not sufficient for resume or override use.
Approval-gated resume is bound to a frozen execution contract. If memory view or canonical task input drifts, resume must stop with `STALE_APPROVAL_SNAPSHOT`.
Shared `memory_target` writes use optimistic version checks and reject on conflict; there is no last-write-wins fallback in restricted pilot mode.

### Live Pilot Rehearsal

Before a real restricted pilot, run one live-provider rehearsal in the target environment:

```bash
uv run binliquid team pilot-check \
  --spec examples/team/restricted_pilot_live.yaml \
  --profile restricted \
  --mode live-provider \
  --provider auto \
  --report artifacts/team_pilot_live_report.json \
  --json
```

Use the same spec, profile, and artifact retention path that will be used for the pilot window.

### Artifact Retention

Retain these artifacts for every pilot check and pilot rehearsal:

- `artifacts/team_pilot_report.json`
- `artifacts/team_pilot_live_report.json` when a live rehearsal is run
- `.binliquid/team/jobs/<job_id>/status.json`
- `.binliquid/team/jobs/<job_id>/events.jsonl`
- `.binliquid/team/jobs/<job_id>/tasks.json`
- `.binliquid/team/jobs/<job_id>/handoffs.json`
- `.binliquid/team/jobs/<job_id>/audit_envelope.json`
- `artifacts/team_summary.json`
- `uv run binliquid config resolve --profile restricted --json` output
- approval store snapshot or the approval summary embedded in the pilot report

### Incident Response

- Replay verify fails:
  - stop the pilot immediately
  - export the affected job artifacts
  - preserve the failing `team replay --verify` output
  - open a root-cause item before any rerun
- Approval mismatch or approval reuse attempt succeeds:
  - mark the pilot `No-Go`
  - invalidate outstanding approvals for the affected run set
  - do not reuse the blocked source jobs
- Audit inconsistency or missing causal refs:
  - stop the pilot
  - copy artifacts to immutable storage
  - treat the release candidate as invalid until fixed
- Scope violation or unexpected memory write succeeds:
  - disable Team Runtime immediately
  - revert to the core single-agent path only

### Rollback And Kill-Switch

The supported hard stop for this slice is disabling Team Runtime entirely:

```bash
BINLIQUID_TEAM_ENABLED=false uv run binliquid team run --spec examples/team/restricted_pilot.yaml --once "pilot disable check" --profile restricted --json
```

Expected result: the command fails with Team Runtime disabled and no new team delegation starts.

Operational fallback for this slice is the core single-agent runtime, not a degraded team mode.
`BINLIQUID_TEAM_MAX_PARALLEL_TASKS=1` may help diagnosis, but it is not a rollback mechanism.
If bounded concurrency repeatedly falls back to serialized execution, treat that as a pilot warning. If drift/conflict repeats in the same workload, force serial diagnosis first; if it persists, disable Team Runtime entirely.

### Stop Conditions

Do not start or continue a pilot if any of the following occur:

- any deterministic `team pilot-check` failure
- nondeterministic smoke behavior across repeated deterministic runs
- replay or audit inconsistency
- approval reuse or consumed-state bypass
- scope isolation bypass

## 11. Enterprise Deployment Runbook

### Preflight

```bash
uv run python scripts/prepare_enterprise_fixture.py --root .
uv run binliquid security baseline --profile enterprise --json
uv run binliquid auth whoami --profile enterprise --json
uv run binliquid auth check --profile enterprise --permission runtime.run --json
uv run binliquid metrics snapshot --profile enterprise --json
uv run binliquid ga readiness --profile enterprise --report artifacts/ga_readiness_report.json --json
```

### Required Operator Drills

- `uv run binliquid keys status --profile enterprise --json`
- `uv run binliquid keys rotate-plan --profile enterprise --json`
- `uv run binliquid migrate plan --profile enterprise --json`
- `uv run binliquid backup create --profile enterprise --json`
- `uv run binliquid restore verify --profile enterprise --backup-dir <backup_dir> --json`
- `uv run binliquid support bundle export --profile enterprise --json`

### Evidence To Retain

- `artifacts/security_posture.json`
- `artifacts/metrics_snapshot.json`
- `artifacts/ga_readiness_report.json`
- `artifacts/GA_READINESS_REPORT.md`
- backup manifest generated by `backup create`
- signed support bundle manifest
- key status and rotation plan outputs

### Incident Guidance

- signature verify failure:
  - treat as `SEV0`
  - stop export-driven workflows
  - rotate or revoke the affected key only after preserving evidence
- unauthorized mutation or RBAC deny mismatch:
  - treat as `SEV0`
  - disable enterprise mutation paths until identity enforcement is revalidated
- restore verification failure:
  - treat as `SEV1`
  - block upgrade or rollback completion
- high fallback/conflict/serialization rate:
  - treat as `SEV2`
  - reduce workload, review qualification envelope, and rerun metrics snapshot

### Kill-Switch And Safe Fallback

- disable Team Runtime entirely with `BINLIQUID_TEAM_ENABLED=false`
- keep enterprise CLI controls read-only until identity and signing checks return to `pass`
- do not claim GA readiness while `ga readiness` is `yellow` or `red`
