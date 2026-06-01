# Pilot Readiness Release Pack

This release pack is the handoff artifact for the constrained self-hosted Agent
Control Plane pilot.

## Regenerate

Run:

```bash
make pilot-readiness-gate
```

The gate regenerates the pilot readiness report after UI, backend, Tauri bridge,
evidence, i18n, claim, and formatting checks pass.

## Artifact Roots

```text
artifacts/pilot-readiness/
artifacts/operator-panel-ui/
artifacts/release-pack/control-plane-v1/
```

## Required Files

```text
artifacts/pilot-readiness/PILOT_READINESS_REPORT.md
artifacts/pilot-readiness/control-plane-snapshot.json
artifacts/pilot-readiness/claim-guard-matrix.json
artifacts/pilot-readiness/reports/operator-panel-productized-pages.json
artifacts/pilot-readiness/tauri-smoke/report.json
artifacts/operator-panel-ui/e2e-json/results.json
artifacts/operator-panel-ui/productized-pages/manifest.json
artifacts/operator-panel-ui/tauri-smoke/TAURI_LAUNCHED_SMOKE.md
```

The current release-pack support files are:

```text
artifacts/release-pack/control-plane-v1/control_plane_claim_matrix.json
artifacts/release-pack/control-plane-v1/control_plane_readiness_report.json
artifacts/release-pack/control-plane-v1/ga_readiness_report.json
artifacts/release-pack/control-plane-v1/security_posture.json
artifacts/release-pack/control-plane-v1/support_bundle_manifest.json
```

## Evidence Interpretation

- `PILOT_READINESS_REPORT.md` proves the local deterministic readiness gate.
- `control-plane-snapshot.json` records the source-of-truth snapshot used by the
  UI and assertions.
- `claim-guard-matrix.json` records supported, conditional, and blocked claims.
- `operator-panel-productized-pages.json` records route screenshot coverage.
- `tauri-smoke/report.json` records the Tauri bridge smoke result.
- `e2e-json/results.json` records the Playwright proof for the pilot flow,
  accessibility, responsive coverage, evidence, productized pages, and raw JSON
  guard.

Preview fixture evidence is acceptable for deterministic UI readiness only. It
is not live customer evidence and cannot be used to unlock live computer-use or
public desktop claims.

## Release Candidate Decision

The release candidate may be shown as:

> Constrained self-hosted Agent Control Plane pilot-ready for policy, approval,
> identity, audit, replay, and signed evidence workflows.

It must not be shown as:

- unrestricted desktop automation,
- public desktop installer ready,
- live computer-use ready,
- multi-tenant SaaS ready,
- target-environment enterprise ready without fresh signed qualification
  evidence.

## Handoff Checklist

1. Run `make pilot-readiness-gate`.
2. Open `artifacts/pilot-readiness/PILOT_READINESS_REPORT.md`.
3. Confirm all checks are `passed`.
4. Open `artifacts/pilot-readiness/claim-guard-matrix.json`.
5. Confirm computer-use remains blocked unless separately qualified.
6. Open `artifacts/operator-panel-ui/tauri-smoke/TAURI_LAUNCHED_SMOKE.md`.
7. Confirm the Tauri bridge smoke passed and whether a GUI launch probe was
   requested.
8. Attach the artifact roots to the pilot handoff.
