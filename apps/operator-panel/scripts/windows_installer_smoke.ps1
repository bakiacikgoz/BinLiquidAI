param(
  [Parameter(Mandatory = $true)]
  [string]$InstallerPath,
  [string]$ExpectedProductName = "AegisOS Operator Panel",
  [string]$OutputDir = "artifacts/windows-installer-smoke",
  [switch]$AllowUnsignedSmoke,
  [switch]$RunInstall
)

$ErrorActionPreference = "Stop"

function Write-JsonEvidence {
  param(
    [string]$Path,
    [hashtable]$Payload
  )

  $Payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Find-InstalledApp {
  param([string]$ProductName)

  $candidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\$ProductName\$ProductName.exe"),
    (Join-Path $env:ProgramFiles "$ProductName\$ProductName.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "$ProductName\$ProductName.exe")
  )
  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
      return $candidate
    }
  }
  return $null
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$ResolvedInstaller = (Resolve-Path -LiteralPath $InstallerPath).Path
$InstallerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ResolvedInstaller).Hash.ToLowerInvariant()
$Signature = Get-AuthenticodeSignature -LiteralPath $ResolvedInstaller
$Signed = $Signature.Status -eq "Valid"

if (-not $Signed -and -not $AllowUnsignedSmoke) {
  $blocked = @{
    platform = "windows"
    installer_sha256 = $InstallerHash
    signed = $false
    install_status = "blocked"
    bundled_runtime_status = "blocked"
    operator_capabilities_status = "blocked"
    doctor_status = "blocked"
    computer_use_live_enabled = $false
    computer_use_reason_code = "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    reason = "unsigned_installer_requires_AllowUnsignedSmoke"
  }
  Write-JsonEvidence -Path (Join-Path $OutputDir "windows-installer-smoke.json") -Payload $blocked
  throw "[smoke] unsigned installer requires -AllowUnsignedSmoke"
}

$InstallStatus = "manual"
if ($RunInstall) {
  $process = Start-Process -FilePath $ResolvedInstaller -ArgumentList "/S" -Wait -PassThru
  if ($process.ExitCode -ne 0) {
    throw "[smoke] installer exited with $($process.ExitCode)"
  }
  $InstallStatus = "pass"
}

$AppExe = Find-InstalledApp -ProductName $ExpectedProductName
$RuntimeStatus = "manual"
$CapabilitiesStatus = "manual"
$DoctorStatus = "manual"
$Capabilities = $null

if ($AppExe) {
  $resourceRoot = Join-Path (Split-Path -Parent $AppExe) "resources\binliquid-runtime"
  $runtimePython = Join-Path $resourceRoot "python\Scripts\python.exe"
  if (Test-Path -LiteralPath $runtimePython -PathType Leaf) {
    & $runtimePython -m binliquid --version | Set-Content -LiteralPath (Join-Path $OutputDir "binliquid-version.txt")
    if ($LASTEXITCODE -eq 0) {
      $RuntimeStatus = "pass"
    } else {
      $RuntimeStatus = "fail"
    }

    & $runtimePython -m binliquid operator capabilities --json |
      Set-Content -LiteralPath (Join-Path $OutputDir "operator_capabilities.json")
    if ($LASTEXITCODE -eq 0) {
      $CapabilitiesStatus = "pass"
      $Capabilities = Get-Content -Raw -LiteralPath (Join-Path $OutputDir "operator_capabilities.json") | ConvertFrom-Json
    } else {
      $CapabilitiesStatus = "fail"
    }

    & $runtimePython -m binliquid doctor --profile balanced --json |
      Set-Content -LiteralPath (Join-Path $OutputDir "doctor_balanced.json")
    $DoctorStatus = if ($LASTEXITCODE -eq 0) { "pass" } else { "fail" }
  } else {
    $RuntimeStatus = "fail"
  }
}

$reasonCode = "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
if ($Capabilities -and $Capabilities.features.computerUsePilot.reasonCode) {
  $reasonCode = $Capabilities.features.computerUsePilot.reasonCode
}

$report = @{
  platform = "windows"
  installer_sha256 = $InstallerHash
  signed = $Signed
  install_status = $InstallStatus
  bundled_runtime_status = $RuntimeStatus
  operator_capabilities_status = $CapabilitiesStatus
  doctor_status = $DoctorStatus
  computer_use_live_enabled = $false
  computer_use_reason_code = $reasonCode
}
Write-JsonEvidence -Path (Join-Path $OutputDir "windows-installer-smoke.json") -Payload $report

Write-Output "[smoke] report=$(Join-Path $OutputDir "windows-installer-smoke.json")"
