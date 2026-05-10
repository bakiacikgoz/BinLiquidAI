# Hat B Desktop Release Handoff - 2026-05-10

## Current Status

Hat B is blocked by external credentials and clean-machine evidence. No public
desktop installer release has been made, and no desktop release claim should be
published from the current evidence.

Local evidence already captured:

- Operator Panel UI gate: PASS.
- Operator Panel Rust/Tauri tests: PASS.
- Local unsigned macOS `.app` and `.dmg` build: PASS.
- Windows release gate evaluator tests: PASS.
- Windows public release gate fail-closed evidence: `status=blocked`,
  `public_release_allowed=false`.
- macOS notarization fail-closed evidence:
  `status=blocked_external_credentials`.

GitHub inventory observed on 2026-05-10:

- Repository secrets: none listed.
- Repository variables: none listed.
- Existing environment: `release-macos`.
- Missing/empty release environment coverage for Windows release credentials.

## macOS Blocker

Required GitHub environment: `release-macos`.

Required signing secrets:

- `MACOS_SIGNING_IDENTITY`
- `MACOS_SIGNING_CERT_P12_B64`
- `MACOS_SIGNING_CERT_PASSWORD`

Required notarization secrets, using one mode only.

API key mode:

- `APPLE_NOTARY_KEY_ID`
- `APPLE_NOTARY_ISSUER_ID`
- `APPLE_NOTARY_KEY_P8_B64`

Apple ID mode:

- `APPLE_ID`
- `APPLE_TEAM_ID`
- `APPLE_APP_PASSWORD`

Workflow to run after secrets are provisioned:

```bash
gh workflow run operator-panel-release-macos.yml \
  --repo bakiacikgoz/BinLiquidAI
```

macOS PASS criteria:

- `codesign --verify --deep --strict` PASS.
- `xcrun notarytool submit --wait` PASS.
- Stapler PASS.
- Clean-machine Gatekeeper open test PASS.
- Evidence JSON records all of the above without secret material.

## Windows Blocker

Required GitHub environment: `release-windows`.

Required secrets:

- `WINDOWS_SIGNING_CERT_PFX_B64`
- `WINDOWS_SIGNING_CERT_PASSWORD`

Required variable:

- `WINDOWS_TIMESTAMP_URL`

Workflow sequence after secrets are provisioned:

```bash
gh workflow run operator-panel-release-windows.yml \
  --repo bakiacikgoz/BinLiquidAI

gh workflow run operator-panel-windows-clean-smoke.yml \
  --repo bakiacikgoz/BinLiquidAI

gh workflow run operator-panel-promote-windows.yml \
  --repo bakiacikgoz/BinLiquidAI
```

Windows PASS criteria:

- Signed RC artifact exists.
- Artifact is timestamped.
- `signtool verify /pa /v` PASS.
- Clean Windows VM install/open/runtime/capabilities/doctor smoke PASS.
- `windows-public-release-gate.json` reports:
  `status=pass`, `public_release_allowed=true`, and
  `blocking_reasons=[]`.
- Windows live computer-use remains disabled with
  `WINDOWS_COMPUTER_USE_NOT_QUALIFIED` unless separate signed qualification
  evidence enables it.

## No-Ship Rule

Do not publish a Hat B desktop release until every macOS or Windows target being
claimed has green signing, notarization/signature, clean-machine smoke, and
public release gate evidence. Hat A may remain published as a source/CLI/
enterprise self-hosted candidate without desktop installer claims.
