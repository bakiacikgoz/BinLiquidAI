# Windows Installer Smoke Runbook

Status: release gate runbook

Windows installer smoke is required before any public or enterprise Windows release claim. Unsigned NSIS artifacts may be used only for internal CI smoke and must be clearly labeled as unsigned.

## Preconditions

- Windows runner or clean Windows VM.
- Microsoft Edge WebView2 Runtime installed.
- NSIS installer artifact produced by the Windows release workflow.
- Authenticode signature present for public release candidates, or `-AllowUnsignedSmoke` used only for internal smoke.

## Internal Unsigned Smoke

```powershell
pwsh apps/operator-panel/scripts/windows_installer_smoke.ps1 `
  -InstallerPath <path-to-nsis-exe> `
  -ExpectedProductName "AegisOS Operator Panel" `
  -OutputDir artifacts/windows-installer-smoke `
  -AllowUnsignedSmoke
```

Unsigned smoke is internal validation only. It must never be used as public release evidence.

## Signed Public RC Smoke

Run this only with a signed installer on a clean or disposable Windows VM:

```powershell
pwsh apps/operator-panel/scripts/windows_installer_smoke.ps1 `
  -InstallerPath <signed-nsis-exe> `
  -ExpectedProductName "AegisOS Operator Panel" `
  -OutputDir artifacts/windows-installer-smoke `
  -RunInstall `
  -CleanVm
```

Do not use `-AllowUnsignedSmoke` for signed public RC smoke. Use `-RunInstall` only on a clean or disposable VM because it installs the NSIS package.

## Evidence

The smoke script writes:

- `windows-installer-smoke.json`
- `operator_capabilities.json` when an installed runtime is found
- `doctor_balanced.json` when an installed runtime is found
- `binliquid-version.txt` when an installed runtime is found

The expected report shape includes:

```json
{
  "platform": "windows",
  "installer_sha256": "...",
  "signed": false,
  "timestamped": false,
  "clean_vm_claimed": false,
  "run_install_used": false,
  "allow_unsigned_smoke_used": true,
  "os_version": "...",
  "powershell_version": "...",
  "webview2_status": "present|unknown",
  "app_exe_found": false,
  "install_root_kind": "LocalAppData|ProgramFiles|ProgramFilesX86|unknown",
  "install_status": "pass|manual|blocked|fail",
  "bundled_runtime_status": "pass|manual|blocked|fail",
  "operator_capabilities_status": "pass|manual|blocked|fail",
  "doctor_status": "pass|manual|blocked|fail",
  "computer_use_live_enabled": false,
  "computer_use_reason_code": "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
}
```

## Public Release Gate

After `windows-release-status.json` and installer smoke evidence exist, evaluate the machine-readable public release gate:

```powershell
uv run python scripts/evaluate_windows_release_gate.py `
  --release-status artifacts/windows-release-evidence/windows-release-status.json `
  --installer-smoke artifacts/windows-installer-smoke/windows-installer-smoke.json `
  --operator-capabilities artifacts/windows-installer-smoke/operator_capabilities.json `
  --doctor artifacts/windows-installer-smoke/doctor_balanced.json `
  --output artifacts/windows-public-release-gate/windows-public-release-gate.json
```

Expected internal unsigned smoke result:

```json
{
  "public_release_allowed": false,
  "blocking_reasons": [
    "unsigned_internal_smoke_not_public_release_eligible"
  ]
}
```

## Release Rule

Public or enterprise Windows release remains blocked until:

- NSIS artifact is Authenticode signed and timestamped.
- `signtool verify /pa /v` passes.
- Clean VM installer smoke passes with `-RunInstall` and `-CleanVm`.
- `operator capabilities --json` reports Windows live computer-use disabled with `WINDOWS_COMPUTER_USE_NOT_QUALIFIED`.
- `windows-public-release-gate.json` reports `status=pass`, `public_release_allowed=true`, and no `blocking_reasons`.
