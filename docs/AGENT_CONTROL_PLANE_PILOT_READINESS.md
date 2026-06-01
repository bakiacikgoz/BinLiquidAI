# Agent Control Plane Pilot Readiness

This branch starts the pilot-readiness plan with the runtime truth and snapshot
foundation.

## Completed In This Slice

- Added `DataSourceState` and `ControlPlaneSnapshot` backend contracts.
- Added `binliquid control-plane snapshot --json`.
- Added the Operator Panel snapshot TypeScript types and loader.
- Added the Tauri bridge command for live snapshot loading.
- Added preview snapshot fixture data that is explicitly marked as
  `preview_fixture`.
- Added `make control-plane-snapshot-gate`.

## Current Claim Boundaries

- Live computer-use remains blocked and qualification-gated.
- Public desktop installer remains blocked without signing/notarization and
  clean-machine evidence.
- Enterprise self-hosted readiness remains conditional until signed
  qualification evidence is present.

## Pilot Readiness Checklist

- [ ] Self-hosted install completes.
- [ ] `control-plane doctor` is healthy or returns deterministic blockers.
- [ ] Enterprise security baseline passes.
- [x] Agent registry accepts the governed ops agent.
- [x] Policy simulation shows allow/approval/deny decisions.
- [x] Approval-heavy run returns approval pending without executing mutation.
- [x] Evidence export and verify pass.
- [x] Support bundle export remains redacted.
- [x] Claim guard blocks unsupported desktop and live computer-use claims.
- [x] Operator Console shows gated execution surfaces.
- [x] Runtime truth snapshot contract exists.

## Next Slices

- Move primary raw JSON into a reusable advanced/raw inspector.
- Map the snapshot into page-specific view models.
- Add no-primary-raw-JSON and i18n coverage gates.
- Add Tauri launched smoke and pilot readiness release-pack artifacts.
