# RELEASE_GATE_v0.5

## 1) Core Gates

```bash
uv run ruff check .
uv run pytest -q
uv run binliquid operator capabilities --json
uv run binliquid approval show --id <known_approval_id> --json
uv run binliquid team list --root-dir .binliquid/team/jobs --json
uv run binliquid team replay --job-id <id> --root-dir .binliquid/team/jobs --json
```

## 2) Operator Panel Gates

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

## 3) Security Gates

No-Ship if any of the following are true:
- shell passthrough exists in bridge command execution
- path traversal or symlink escape is possible in artifact access
- default UI view exposes raw sensitive payloads
- parse failures are silent in UI/bridge

## 4) Performance & UX Gates

- cold start to meaningful render target: < 3s
- dashboard data ready target: < 2s
- 100+ runs list remains smooth
- timeline polling and rendering stays stable at 200+ events

## 5) macOS Signing + Notarization Gates (Required)

Release artifacts must be signed and notarized:
- `.app` and `.dmg` signed
- `codesign --verify --deep --strict` PASS
- `xcrun notarytool submit --wait` PASS
- `xcrun stapler staple` and `xcrun stapler validate` PASS

Quarantine gate:
- clean macOS user/VM test required
- downloaded artifact must open without Gatekeeper block

If notarization fails, release is blocked (beta included).

## 6) Updater / Telemetry Defaults

- updater defaults to `off`
- remote telemetry defaults to `off`
- no background network call in off mode
