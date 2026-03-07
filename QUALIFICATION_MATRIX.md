# Qualification Matrix

## Purpose

This document defines the evidence required before BinLiquid / AegisOS can be described as `enterprise deployment-ready under defined constraints`.
It does not claim that evidence already exists.

## Supported Deployment Classes

- `Linux Standard`: primary GA runtime reference
- `macOS Operator`: secondary operator tooling surface

## Workload Families

- mixed bounded-concurrency workflow
- approval-heavy workflow
- conflict-heavy shared-state workflow
- long-running workflow
- provider transient-failure workflow

## Qualification Windows

- `6h` candidate smoke-soak
- `24h` release-candidate soak
- `72h` final pre-GA soak

## Blocking Pass Criteria

- `0` replay or audit integrity failures
- `0` duplicate side effects
- `0` restore verification failures after checkpointed restart drills
- no silent shared-state overwrite
- no unclassified provider/runtime failures
- sqlite integrity passes before and after soak
- artifact growth remains inside retention forecast

## Required Report Outputs

At minimum publish:

- supported concurrent team task envelope
- supported approval-heavy rate
- supported artifact retention window
- fallback thresholds where serial execution becomes expected
- provider failure classification summary

## Blocking Test Set Before Enterprise Claim

- role boundary negative tests
- key rotation and revocation drills
- backup/restore partial-upgrade drill
- replay and signature tamper drills
- 24h approval-heavy soak
- conflict-heavy bounded-concurrency soak
- provider failure classification soak

## Evidence Artifact

Run qualification through the canonical runner:

```bash
uv run binliquid qualification run \
  --profile enterprise \
  --mode mixed \
  --soak-hours 6 \
  --output-root artifacts/qualification \
  --json
```

This publishes:

- `artifacts/qualification/<run_id>/qualification_report.json`
- `artifacts/qualification/<run_id>/QUALIFICATION_REPORT.md`
- latest pointers at `artifacts/qualification_report.json` and `artifacts/QUALIFICATION_REPORT.md`

The JSON artifact is signed. `ga readiness` must verify that signature, require the mandatory workload set, enforce the `6h` soak threshold for `green/go`, and use the published support-boundary table before any enterprise-ready claim.
