# Tauri Launched Smoke

The Operator Panel Tauri smoke verifies that the desktop bridge contract remains
usable for the Agent Control Plane pilot.

## Run

Default deterministic smoke:

```bash
make operator-panel-tauri-smoke
```

Direct script:

```bash
corepack pnpm --dir apps/operator-panel tauri:smoke
```

Optional local GUI launch probe:

```bash
OPERATOR_PANEL_TAURI_LAUNCH=1 corepack pnpm --dir apps/operator-panel tauri:smoke
```

The optional GUI probe requires a local desktop session and may open the Tauri
development shell. The default CI-safe mode does not open live computer-use
gates.

## Outputs

```text
artifacts/operator-panel-ui/tauri-smoke/report.json
artifacts/operator-panel-ui/tauri-smoke/TAURI_LAUNCHED_SMOKE.md
artifacts/operator-panel-ui/tauri-bridge-smoke.json
```

The pilot readiness pack copies the report to:

```text
artifacts/pilot-readiness/tauri-smoke/report.json
```

## Checks

The smoke checks:

- `src-tauri/tauri.conf.json` is present,
- `tauri:dev` and `tauri:build` scripts are exposed,
- required bridge handlers are registered,
- preview runtime truth is explicit and not a silent fallback,
- the preview snapshot contains runs, approvals, and evidence packs,
- Rust bridge tests pass,
- optional GUI launch stays alive for the configured timeout when requested.

Required bridge handlers:

```text
bridge_handshake
bridge_config_resolve
bridge_control_plane_snapshot
bridge_team_list
bridge_approval_pending
bridge_control_plane_evidence_verify
bridge_control_plane_claims_verify
```

## Interpretation

`status=passed` means the bridge contract, Rust tests, runtime truth fixture, and
reportability passed. If `launchRequested=false`, it is not proof that the GUI
shell was opened in the current run.

For a desktop-session handoff that requires actual GUI launch evidence, rerun
with `OPERATOR_PANEL_TAURI_LAUNCH=1` and attach the updated report.

## Boundary

This smoke must not enable live computer-use. It verifies bridge readiness and
claim transparency for the control-plane pilot.
