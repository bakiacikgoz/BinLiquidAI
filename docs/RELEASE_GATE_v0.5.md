# RELEASE_GATE_v0.5

## 1) Team Runtime Pilot Gate

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
uv run binliquid team pilot-check \
  --spec examples/team/restricted_pilot_live.yaml \
  --profile restricted \
  --mode live-provider \
  --provider auto \
  --report artifacts/team_pilot_live_report.json \
  --json
```

Required outcomes:
- `team pilot-check` exits `0`.
- `artifacts/team_pilot_report.json` exists and reports `overall_status=pass`.
- Approval lifecycle is `pending -> approved -> executed -> consumed`; `approved` alone never authorizes resume or override use.
- Approval-gated actions are bound to an execution contract (`snapshot_hash`, memory fingerprint, causal ancestry); context drift must fail closed as `STALE_APPROVAL_SNAPSHOT`.
- Clean `team replay --verify` passes for the smoke artifacts.
- Tampered replay fixture fails verification.
- Approval reuse probe is blocked.
- Scope isolation probe fails closed.
- Bounded-concurrency counters report zero stale approvals, zero memory conflicts, and visible fallback events.

No-Ship if any of the following are true:
- `team pilot-check` is red.
- `team replay --verify` is nondeterministic across repeated deterministic smoke runs.
- `approval_consumed` can occur without a prior executed approval.
- approval snapshot drift is silently accepted during resume.
- shared `memory_target` writes produce nondeterministic final state or silent overwrite.
- any clean smoke replay reports missing causal refs, missing terminal task events, or event sequence drift.
- the restricted smoke spec passes while missing handoff coverage or using an unknown tool policy profile.

## 2) Core Gates

```bash
uv run pytest -q
uv run binliquid operator capabilities --json
uv run binliquid approval show --id <known_approval_id> --json
uv run binliquid team list --root-dir .binliquid/team/jobs --json
uv run binliquid team replay --job-id <id> --root-dir .binliquid/team/jobs --verify --json
```

## 3) Operator Panel Gates

```bash
cd apps/operator-panel
pnpm install
pnpm lint
pnpm build
cd src-tauri
cargo test -q
```

Required outcomes:
- `BridgeResult<T>` contract is stable.
- mutation actions are disabled when `operator_id` is missing.
- handshake mismatch disables mutations.

## 4) Security Gates

No-Ship if any of the following are true:
- shell passthrough exists in bridge command execution
- path traversal or symlink escape is possible in artifact access
- Windows child processes fail because required system env variables are removed
- Windows live computer-use automation is advertised without a Windows qualification report
- default UI view exposes raw sensitive payloads
- parse failures are silent in UI/bridge

## 5) Performance & UX Gates

- cold start to meaningful render target: < 3s
- dashboard data ready target: < 2s
- 100+ runs list remains smooth
- timeline polling and rendering stays stable at 200+ events

## 6) macOS Signing + Notarization Gates (Required)

Release artifacts must be signed and notarized:
- `.app` and `.dmg` signed
- `codesign --verify --deep --strict` PASS
- `xcrun notarytool submit --wait` PASS
- `xcrun stapler staple` and `xcrun stapler validate` PASS

GitHub release workflow requirements:
- Environment `release-macos` must exist with required reviewer/policy controls.
- Signing secrets must be present: `MACOS_SIGNING_IDENTITY`,
  `MACOS_SIGNING_CERT_P12_B64`, `MACOS_SIGNING_CERT_PASSWORD`.
- Notarization auth must use one mode:
  - API key mode (preferred): `APPLE_NOTARY_KEY_ID`,
    `APPLE_NOTARY_ISSUER_ID`, `APPLE_NOTARY_KEY_P8_B64`
  - Apple ID mode: `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`

If these credentials are missing, the release remains RC with an external
credential blocker. Do not bypass this gate and do not mark notarization proof
as passing without `notarytool`, stapler, and quarantine evidence.

Quarantine gate:
- clean macOS user/VM test required
- downloaded artifact must open without Gatekeeper block

If notarization fails, release is blocked (beta included).

## 7) Windows Signing + Installer Gates

Windows release artifacts must pass:
- `windows-2022` CI
- core lint/test
- operator panel test/lint/build
- Rust bridge tests
- bundled runtime manifest verification
- Tauri NSIS build
- clean Windows VM install/open/handshake smoke

Unsigned NSIS artifacts are internal CI smoke artifacts only. Public or
enterprise Windows release artifacts require Authenticode signing and timestamp
proof. If signing credentials are missing, the Windows release remains RC with
an external credential blocker.

## 8) Updater / Telemetry Defaults

- updater defaults to `off`
- remote telemetry defaults to `off`
- no background network call in off mode
