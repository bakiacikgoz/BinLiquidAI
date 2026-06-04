# Fallow Codebase Intelligence

Plan 8 adopts Fallow for the Operator Panel TypeScript and JavaScript workspace only. Python and Rust validation remain covered by `ruff`, `pytest`, and `cargo test`.

## Scope

- Workspace: `apps/operator-panel`
- Config: `apps/operator-panel/.fallowrc.json`
- Baselines: `fallow-baselines/`
- Artifacts: `artifacts/code-intelligence/fallow/`

Fallow is intentionally not configured for runtime coverage in this phase. Runtime coverage requires a separate license, privacy, and telemetry review.

## Gate Policy

`make operator-panel-fallow-gate` runs:

```bash
FALLOW_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 corepack pnpm --dir apps/operator-panel fallow:report
BOUNDARY_GATE_MODE=enforce corepack pnpm --dir apps/operator-panel fallow:boundary
FALLOW_GATE_MODE=${FALLOW_GATE_MODE:-warn} corepack pnpm --dir apps/operator-panel fallow:policy
corepack pnpm --dir apps/operator-panel test -- scripts/fallow-policy
```

Blocking findings:

- unresolved imports
- unlisted dependencies
- duplicate exports
- boundary violations
- unresolved catalog references
- misconfigured dependency overrides
- high-confidence secret findings in generated Fallow artifacts

Warn-only findings during the initial rollout:

- unused files
- unused exports
- unused types
- duplication
- health and complexity findings
- circular dependencies

`FALLOW_GATE_MODE=enforce` can be used later to fail on warning buckets after the existing baseline is reduced.

## Baseline Policy

The initial baselines are committed under `fallow-baselines/` so existing repo debt is visible but does not block pilot work.

- Baselines must not grow in normal feature PRs.
- Regenerate baselines only during an explicit code intelligence maintenance task.
- Do not delete code solely because Fallow reports it as unused.
- Prefer narrow entries, public API modeling, or focused suppressions over broad ignores.

## Auto-Fix Policy

`fallow fix` is allowed only with `--dry-run`. Real rewrite, delete, or dependency removal actions require manual review and explicit approval.

The report generator captures a dry-run output as evidence, but it does not apply changes.

## Release Artifacts

The report generator writes:

- `summary.json`
- `SUMMARY.md`
- `dead-code.json`
- `dupes.json`
- `health.json`
- `audit.json`
- `boundary-violations.json`
- `fix-dry-run.json`

Artifacts are intended for engineering and security review. Customer-facing packs should use the summary unless source-path detail is explicitly acceptable.
