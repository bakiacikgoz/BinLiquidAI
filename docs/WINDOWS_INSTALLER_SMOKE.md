# Windows Installer Smoke Runbook

Status: release gate runbook

Windows installer smoke is required before any public or enterprise Windows release claim. Unsigned NSIS artifacts may be used only for internal CI smoke and must be clearly labeled as unsigned.

## Preconditions

- Windows runner or clean Windows VM.
- Microsoft Edge WebView2 Runtime installed.
- NSIS installer artifact produced by the Windows release workflow.
- Authenticode signature present for public release candidates, or `-AllowUnsignedSmoke` used only for internal smoke.

## Automated Smoke

```powershell
pwsh apps/operator-panel/scripts/windows_installer_smoke.ps1 `
  -InstallerPath <path-to-nsis-exe> `
  -ExpectedProductName "AegisOS Operator Panel" `
  -OutputDir artifacts/windows-installer-smoke `
  -AllowUnsignedSmoke
```

Use `-RunInstall` only on an isolated VM or disposable runner:

```powershell
pwsh apps/operator-panel/scripts/windows_installer_smoke.ps1 `
  -InstallerPath <path-to-nsis-exe> `
  -OutputDir artifacts/windows-installer-smoke `
  -AllowUnsignedSmoke `
  -RunInstall
```

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
  "install_status": "pass|manual|blocked|fail",
  "bundled_runtime_status": "pass|manual|blocked|fail",
  "operator_capabilities_status": "pass|manual|blocked|fail",
  "doctor_status": "pass|manual|blocked|fail",
  "computer_use_live_enabled": false,
  "computer_use_reason_code": "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
}
```

## Release Rule

Public or enterprise Windows release remains blocked until:

- NSIS artifact is Authenticode signed and timestamped.
- `signtool verify /pa /v` passes.
- Clean VM installer smoke passes.
- `operator capabilities --json` reports Windows live computer-use disabled with `WINDOWS_COMPUTER_USE_NOT_QUALIFIED`.
