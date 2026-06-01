# Control Plane Runtime Truth Model

This document defines the first pilot-readiness contract for distinguishing live
control-plane data from preview, stale, and error states.

## Data Source States

`control-plane snapshot --json` emits `dataSource` on every response:

- `preview_fixture`: explicit browser preview fixture data. It is useful for UI
  development, but it is never pilot evidence.
- `tauri_live`: the Tauri shell called the local CLI and returned a live
  self-hosted snapshot.
- `cli_live`: the CLI built the snapshot directly from local control-plane,
  governance, claim, and artifact stores.
- `stale_cache`: data exists but is older than the freshness threshold.
- `error`: the snapshot source is unavailable or cannot be trusted.

`isSilentFallback` is the hard boundary. If a live/Tauri path uses preview data,
the UI and gates must fail closed.

## Snapshot Contract

The snapshot contract is `control-plane.snapshot/v1` and includes:

- `dataSource`
- `system`
- `dashboard`
- `agents`
- `runs`
- `approvals`
- `evidencePacks`
- `policyPacks`
- `executionSurfaces`
- `logs`
- `alerts`
- `reports`
- `operations`
- `admin`
- `quickActions`

The source of each major section is recorded in `system.sourceMap`. Missing
pilot-readiness signals are surfaced in `system.health.missingSignals` and
`partialReasons`.

## Health Rule

The system page must not report high-confidence `healthy` when required pilot
signals are missing. Missing metrics or qualification evidence yields `partial`
even when the local CLI is reachable.

Computer-use live execution and public desktop installer claims remain blocked
unless their signed qualification evidence exists.

## Validation

The snapshot gate is:

```bash
make control-plane-snapshot-gate
```

It runs the snapshot CLI, backend snapshot tests, and the Operator Panel snapshot
loader tests.

The release-candidate gate is:

```bash
make pilot-readiness-gate
```

That gate also checks no-primary-raw-JSON coverage, i18n coverage,
productized-page screenshots, evidence verification, Tauri bridge smoke, and the
pilot readiness artifact report.

## Artifact Rules

`artifacts/pilot-readiness/control-plane-snapshot.json` is the release-pack copy
of the snapshot used by the pilot readiness assertion.

`artifacts/pilot-readiness/PILOT_READINESS_REPORT.md` must not claim live
evidence when the snapshot source is `preview_fixture`. Preview data is valid for
deterministic UI and contract testing only.

If the source is `tauri_live` or `cli_live`, `isSilentFallback` must be `false`.
Any live path that falls back to preview data is a fail-closed condition.
