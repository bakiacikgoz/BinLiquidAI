param(
  [Parameter(Mandatory = $true)]
  [string]$InstallerPath,
  [string]$ExpectedProductName = "AegisOS Operator Panel",
  [string]$OutputDir = "artifacts/windows-installer-smoke",
  [switch]$AllowUnsignedSmoke,
  [switch]$RunInstall,
  [switch]$CleanVm
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
    @{
      Path = Join-Path $env:LOCALAPPDATA "Programs\$ProductName\$ProductName.exe"
      Kind = "LocalAppData"
    },
    @{
      Path = Join-Path $env:ProgramFiles "$ProductName\$ProductName.exe"
      Kind = "ProgramFiles"
    },
    @{
      Path = Join-Path ${env:ProgramFiles(x86)} "$ProductName\$ProductName.exe"
      Kind = "ProgramFilesX86"
    }
  )
  foreach ($candidate in $candidates) {
    if ($candidate.Path -and (Test-Path -LiteralPath $candidate.Path -PathType Leaf)) {
      return $candidate
    }
  }
  return $null
}

function Get-WebView2Status {
  $clientRoots = @(
    "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients",
    "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients"
  )
  foreach ($root in $clientRoots) {
    $clients = Get-ChildItem -Path $root -ErrorAction SilentlyContinue
    foreach ($client in $clients) {
      $props = Get-ItemProperty -LiteralPath $client.PSPath -ErrorAction SilentlyContinue
      if ($props -and [string]$props.name -match "WebView2") {
        return "present"
      }
    }
  }
  return "unknown"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$ResolvedInstaller = (Resolve-Path -LiteralPath $InstallerPath).Path
$InstallerHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ResolvedInstaller).Hash.ToLowerInvariant()
$Signature = Get-AuthenticodeSignature -LiteralPath $ResolvedInstaller
$Signed = $Signature.Status -eq "Valid"
$Timestamped = $false
if ($Signature.PSObject.Properties.Name -contains "TimeStamperCertificate") {
  $Timestamped = $null -ne $Signature.TimeStamperCertificate
}
$RunInstallUsed = [bool]$RunInstall
$AllowUnsignedSmokeUsed = [bool]$AllowUnsignedSmoke
$CleanVmClaimed = [bool]$CleanVm
$WebView2Status = Get-WebView2Status

if (-not $Signed -and -not $AllowUnsignedSmoke) {
  $blocked = @{
    platform = "windows"
    installer_sha256 = $InstallerHash
    signed = $false
    timestamped = $false
    signature_status = [string]$Signature.Status
    clean_vm_claimed = $CleanVmClaimed
    run_install_used = $RunInstallUsed
    allow_unsigned_smoke_used = $AllowUnsignedSmokeUsed
    os_version = [System.Environment]::OSVersion.VersionString
    powershell_version = $PSVersionTable.PSVersion.ToString()
    webview2_status = $WebView2Status
    app_exe_found = $false
    install_root_kind = "unknown"
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

$AppResult = Find-InstalledApp -ProductName $ExpectedProductName
$AppExe = if ($AppResult) { $AppResult.Path } else { $null }
$InstallRootKind = if ($AppResult) { $AppResult.Kind } else { "unknown" }
if ($RunInstall -and -not $AppExe) {
  $InstallStatus = "fail"
}
$RuntimeStatus = "manual"
$CapabilitiesStatus = "manual"
$DoctorStatus = "manual"
$Capabilities = $null
$ComputerUseEnabled = $false

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
      try {
        $Capabilities = Get-Content -Raw -LiteralPath (Join-Path $OutputDir "operator_capabilities.json") | ConvertFrom-Json
      } catch {
        $CapabilitiesStatus = "fail"
      }
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
if ($Capabilities -and $null -ne $Capabilities.features.computerUsePilot.enabled) {
  $ComputerUseEnabled = [bool]$Capabilities.features.computerUsePilot.enabled
}

$report = @{
  platform = "windows"
  installer_sha256 = $InstallerHash
  signed = $Signed
  timestamped = $Timestamped
  signature_status = [string]$Signature.Status
  clean_vm_claimed = $CleanVmClaimed
  run_install_used = $RunInstallUsed
  allow_unsigned_smoke_used = $AllowUnsignedSmokeUsed
  os_version = [System.Environment]::OSVersion.VersionString
  powershell_version = $PSVersionTable.PSVersion.ToString()
  webview2_status = $WebView2Status
  app_exe_found = $null -ne $AppExe
  install_root_kind = $InstallRootKind
  install_status = $InstallStatus
  bundled_runtime_status = $RuntimeStatus
  operator_capabilities_status = $CapabilitiesStatus
  doctor_status = $DoctorStatus
  computer_use_live_enabled = $ComputerUseEnabled
  computer_use_reason_code = $reasonCode
}
Write-JsonEvidence -Path (Join-Path $OutputDir "windows-installer-smoke.json") -Payload $report

Write-Output "[smoke] report=$(Join-Path $OutputDir "windows-installer-smoke.json")"
