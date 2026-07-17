# Artifact Workspace Operator Guide

Artifact Workspace starts disabled in the enterprise profile. Enable only a candidate that has a green release-readiness report and an empty no-ship register. Set `artifact_workspace.enabled` first, then enable one per-kind gate at a time. Keep `artifact_workspace.export.enabled` separate so editing can be observed before native writes are allowed. `assistant_ui_runtime.enabled` and `ai_sdk_tauri_transport.enabled` are independent cutovers; the AI SDK flag off retains the legacy assistant session projection.

Before rollout, create and verify a backup, run the artifact integrity doctor, confirm the sidecar reconciliation state is healthy, and record the candidate commit. Start with document. Observe conflict rate, mutation latency, integrity failures, export failures, crash recovery, and support signals before enabling form, code, flow, or slides. Spreadsheet and canvas remain forced off unless the backend license doctor returns an enabled capability for the exact package versions and target.

Normal operator actions use the CLI and release runner, not direct database or content-file edits. Run `imperaos artifact doctor --json` for a bounded diagnostic snapshot and `imperaos artifact integrity --json` for store checks. Support bundles contain the redacted artifact diagnostics; they must not contain content bodies, prompts, secrets, absolute paths, license evidence, or provider responses.

For an incident, turn off the narrowest affected kind; use the global gate for integrity, cross-workspace, unauthorized mutation, crash-loop, export corruption, CSP, or license failures. Stop the sidecar if writes must cease. Do not delete the SQLite database, revision files, assets, quarantine, or journal. Capture audit/evidence, run read-only integrity, then use forward repair or a verified restore.

An operator must not override a conflict, manufacture a commercial capability in renderer configuration, reuse an export ticket, downgrade classification, or approve an AI proposal without reviewing its exact action hash and base revision. See the recovery and release guides for command order and closure criteria.
