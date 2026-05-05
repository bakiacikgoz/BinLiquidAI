# Qualification Matrix

## Purpose

This document defines the evidence required before BinLiquid / AegisOS can be described as `enterprise deployment-ready under defined constraints`.
It does not claim that evidence already exists.

## Supported Deployment Classes

- `Linux Standard`: primary GA runtime reference
- `macOS Operator`: secondary operator tooling surface
- `Windows Standard`: core runtime, operator panel, bundled runtime, signed release-candidate evidence, and clean NSIS installer smoke

## Workload Families

- mixed bounded-concurrency workflow
- approval-heavy workflow
- conflict-heavy shared-state workflow
- long-running workflow
- provider transient-failure workflow
- supervised macOS vision-first computer-use deterministic smoke

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
- Windows Standard additionally requires green `windows-2022` CI, bundled runtime
  manifest verification, external and bundled bridge handshake proof, clean VM
  install/open/handshake smoke, no shell passthrough, no path traversal or symlink
  escape, no unsupported computer-use overclaim, and signed release gate before
  any public release. Windows live computer-use remains disabled until signed
  qualification evidence exists.

## Computer-Use Vision Pilot

- `deterministic` qualification uses `computer_use_vision_qualification/v1`.
- `live` qualification is macOS-only and opt-in.
- Raw screenshots must remain disabled by default with persisted count `0`.
- Replay verifies integrity and policy invariants, not business correctness.
  any public or enterprise Windows release claim.
- Windows release evidence additionally requires schema drift gate PASS,
  recursive resource bundle proof, runtime hash manifest, signed RC release
  status JSON, bundle hash evidence, `docs/WINDOWS_INSTALLER_SMOKE.md` clean VM
  smoke report, installed runtime/capabilities/doctor evidence, and
  `windows-public-release-gate.json` with `status=pass`,
  `public_release_allowed=true`, and no blocking reasons.
- Windows live computer-use automation remains disabled with
  `WINDOWS_COMPUTER_USE_NOT_QUALIFIED` unless a separate signed Windows
  qualification report explicitly enables that surface.

## Phase 4A Platform Status

| Platform | Stage | Live Enabled | Reason |
|---|---:|---:|---|
| macOS | not_qualified until fresh supervised local evidence exists | false by default | `MACOS_COMPUTER_USE_NOT_QUALIFIED` |
| Windows | not_qualified | false | `WINDOWS_COMPUTER_USE_NOT_QUALIFIED` |
| Linux | not_qualified | false | `LINUX_COMPUTER_USE_NOT_QUALIFIED` |

macOS can move to `fixture_qualified` after a fresh matching supervised local
fixture report, but live execution still remains off until explicit config
enablement and current doctor pass. Phase 4C separates
`qualificationPassed=false` from `replayIntegrityVerified=true` for blocked
preflight reports, so no-op evidence can be audit-valid without being
qualification-valid.

Deterministic mock qualification is useful for CI contracts. It is not proof of
real-world desktop reliability.

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

The JSON artifact is signed. `ga readiness` must verify that signature, require
the mandatory workload set, enforce the `6h` soak threshold for `green/go`, and
use the published support-boundary table before any enterprise-ready claim.
