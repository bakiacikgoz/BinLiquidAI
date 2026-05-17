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

Build macOS runtime payload into Tauri resources:

```bash
apps/operator-panel/scripts/build_bundled_runtime_macos.sh arm64
apps/operator-panel/scripts/build_bundled_runtime_macos.sh x86_64
```

macOS runtime entrypoint used by bridge:

`Contents/Resources/binliquid-runtime/python/bin/python -m binliquid ...`

Build Windows x64 runtime payload into Tauri resources:

```powershell
pwsh apps/operator-panel/scripts/build_bundled_runtime_windows.ps1 -Arch x64
pwsh apps/operator-panel/scripts/verify_bundled_runtime_windows.ps1 `
  -RuntimeDir apps/operator-panel/src-tauri/resources/binliquid-runtime
apps/operator-panel/src-tauri/resources/binliquid-runtime/python/Scripts/python.exe -m binliquid --version
pnpm --dir apps/operator-panel exec tauri build --config src-tauri/tauri.windows.conf.json --bundles nsis
```

Windows runtime entrypoint used by bridge:

`binliquid-runtime/python/Scripts/python.exe -m binliquid ...`

Generated runtime contents under `resources/binliquid-runtime/python/` are build
artifacts. Do not commit the generated venv/runtime tree; produce it through the
script or CI and keep `RUNTIME_MANIFEST.txt` as evidence artifact output.

## Security Notes

- No shell passthrough.
- Bridge command surface is allowlisted.
- Artifact reads are root-dir bounded with symlink/traversal checks.
- AI Assistant is read-only by default. It can inspect selected run/log/artifact
  context through bounded prompt packing, but proposed actions remain proposals
  until the existing approval lifecycle is used.
- Assistant streaming uses `bridge_assistant_start_turn` to run
  `chat --stdio-json --stream --once`; stdout JSONL is converted to
  `assistant://event` payloads and malformed lines become non-blocking warnings.
- Bundled mode keeps a minimal platform-aware environment after `env_clear`;
  Windows preserves required system process variables such as `SystemRoot`,
  `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `ComSpec`, `PATHEXT`, `TEMP`, and `TMP`.
- Event tail uses cursor contract with reset/truncated/badLineCount reporting.
- Mutation actions require valid `operator_id`; actor format is `ui:<operator_id>`.
- Assistant approval buttons never execute directly. `Approve`, `Reject`, and
  `Execute` remain separate explicit actions backed by the existing governance
  bridge.

## Signing / Notarization

```bash
apps/operator-panel/scripts/codesign_notarize_macos.sh <App.app> <artifact.dmg>
```

Required env vars:
- `SIGNING_IDENTITY`
- `MACOS_SIGNING_CERT_P12_B64`
- `MACOS_SIGNING_CERT_PASSWORD`

Notarization auth must use one of:
- API key mode (preferred): `APPLE_NOTARY_KEY_FILE`, `APPLE_NOTARY_KEY_ID`,
  optional `APPLE_NOTARY_ISSUER_ID`
- Apple ID mode: `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`

The GitHub release workflow receives the p12 and API key files as base64 secrets
and decodes them only on the release runner. Secret values must not be printed or
committed.

Release gate requires:
- codesign verify
- notarytool submit --wait
- stapler staple + validate
- quarantine + Gatekeeper check
