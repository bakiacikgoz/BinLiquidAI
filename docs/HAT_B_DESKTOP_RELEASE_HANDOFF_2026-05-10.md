# Hat B Desktop Release Handoff - 2026-05-10

## Current Status

Hat B is blocked by external credentials and clean-machine evidence. No public
desktop installer release has been made, and no desktop release claim should be
published from the current evidence.

Tracking issue: https://github.com/bakiacikgoz/BinLiquidAI/issues/4

Local evidence already captured:

- Operator Panel UI gate: PASS.
- Operator Panel Rust/Tauri tests: PASS.
- Local unsigned macOS `.app` and `.dmg` build: PASS.
- macOS release workflow now preflights signing/notarization credentials before
  checkout/build and uploads `operator-panel-macos-credential-preflight-<arch>`
  evidence when blocked.
- GitHub Actions run `25638420468` verified the macOS preflight behavior:
  both `arm64` and `x86_64` lanes stopped at credential preflight with
  `status=blocked_external_credentials`, uploaded preflight evidence, skipped
  checkout/build/sign/notarize steps, and wrote no secret material.
- GitHub Actions run `25638465677` verified Windows CI: `windows-2022`
  required lane and `windows-2025` canary lane both completed with
  `conclusion=success`. Evidence was downloaded under
  `artifacts/readiness/2026-05-10/github_windows_ci_25638465677/`.
- GitHub Actions run `25638818041` verified the Windows signed-RC workflow in
  missing-secret mode. The workflow completed and uploaded unsigned CI smoke
  evidence, but did not upload signed release-candidate artifacts.
  `windows-release-status.json` reports `status=blocked_external_credentials`,
  `signed=false`, `timestamped=false`, `signed_rc_allowed=false`, and
  `secret_material_written=false`. The public gate reports
  `public_release_allowed=false`.
- Windows release gate ownership verification PASS:
  `tests/test_windows_release_gate.py` and
  `tests/test_windows_release_workflows_static.py` confirm
  `windows-release-status.json` stays scoped to signed-RC status and
  `windows-public-release-gate.json` remains the public release authority.
- Windows release gate evaluator tests: PASS.
- Windows public release gate fail-closed evidence: `status=blocked`,
  `public_release_allowed=false`.
- macOS notarization fail-closed evidence:
  `status=blocked_external_credentials`.

GitHub inventory observed on 2026-05-10:

- Repository secrets: none listed.
- Repository variables: none listed.
- Existing environments: `release-macos`, `release-windows`,
  `clean-smoke-windows`, and `promote-windows`.
- Environment protection reviewer/wait-timer rules were attempted but rejected
  by the repository billing plan (`HTTP 422`). Current environments therefore
  have empty `protection_rules`.
- `release-windows` environment variable configured:
  `WINDOWS_TIMESTAMP_URL=http://timestamp.digicert.com`.
- macOS and Windows signing secrets remain missing.

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

If secrets are still missing or partial, the workflow should fail before
checkout/build with `status=blocked_external_credentials`; this is expected
blocked evidence, not a desktop release failure.

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

Configured variable:

- `WINDOWS_TIMESTAMP_URL`

2026-05-11 recheck:

- Repository-level secrets: absent.
- `release-windows` environment secrets: absent.
- `release-windows` environment variable: `WINDOWS_TIMESTAMP_URL` present.
- Clean smoke remains blocked until a signed RC artifact exists.
- The Windows release workflow now preflights signing credentials before
  checkout/build and uploads `operator-panel-windows-credential-preflight`
  evidence when credentials are missing.

Workflow sequence after secrets are provisioned:

```bash
gh workflow run operator-panel-release-windows.yml \
  --repo bakiacikgoz/BinLiquidAI

gh workflow run operator-panel-windows-clean-smoke.yml \
  --repo bakiacikgoz/BinLiquidAI \
  -f signed_rc_run_id=<SIGNED_RC_RUN_ID> \
  -f installer_sha256=<SIGNED_RC_INSTALLER_SHA256>

gh workflow run operator-panel-promote-windows.yml \
  --repo bakiacikgoz/BinLiquidAI \
  -f signed_rc_run_id=<SIGNED_RC_RUN_ID> \
  -f clean_smoke_run_id=<CLEAN_SMOKE_RUN_ID> \
  -f expected_installer_sha256=<SIGNED_RC_INSTALLER_SHA256>
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
