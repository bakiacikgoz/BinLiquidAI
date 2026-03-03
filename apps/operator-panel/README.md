# AegisOS Operator Panel (v0.5.0-beta)

Tauri 2 + React control plane for BinLiquid core.

## Dev Mode (External CLI)

```bash
pnpm install
pnpm tauri:dev
```

Settings defaults:
- `mode=auto`
- profile `balanced`
- root dir `.binliquid/team/jobs`

In `auto` mode, bridge resolution order is:
1. configured `cliPath`
2. bundled runtime python
3. `binliquid` on PATH

## Release Mode (Bundled Runtime)

Build runtime payload into Tauri resources:

```bash
apps/operator-panel/scripts/build_bundled_runtime_macos.sh arm64
apps/operator-panel/scripts/build_bundled_runtime_macos.sh x86_64
```

Runtime entrypoint used by bridge:

`Contents/Resources/binliquid-runtime/python/bin/python -m binliquid ...`

## Security Notes

- No shell passthrough.
- Bridge command surface is allowlisted.
- Artifact reads are root-dir bounded with symlink/traversal checks.
- Event tail uses cursor contract with reset/truncated/badLineCount reporting.
- Mutation actions require valid `operator_id`; actor format is `ui:<operator_id>`.

## Signing / Notarization

```bash
apps/operator-panel/scripts/codesign_notarize_macos.sh <App.app> <artifact.dmg>
```

Required env vars:
- `SIGNING_IDENTITY`
- `APPLE_ID`
- `APPLE_TEAM_ID`
- `APPLE_APP_PASSWORD`

Release gate requires:
- codesign verify
- notarytool submit --wait
- stapler staple + validate
- quarantine + Gatekeeper check
