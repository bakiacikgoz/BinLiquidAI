param()

$ErrorActionPreference = "Stop"

function Assert-Command {
  param(
    [string]$Name,
    [string]$InstallHint
  )

  if ($null -eq (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "[bootstrap] missing ${Name}. $InstallHint"
  }
}

function Invoke-Checked {
  param(
    [string]$FilePath,
    [string[]]$Arguments
  )

  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "[bootstrap] command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
  }
}

Assert-Command -Name "uv" -InstallHint "Install uv from https://docs.astral.sh/uv/getting-started/installation/"
Assert-Command -Name "node" -InstallHint "Install Node.js 22 LTS."
Assert-Command -Name "corepack" -InstallHint "Install Node.js with Corepack enabled."
Assert-Command -Name "cargo" -InstallHint "Install Rust from https://rustup.rs/."

$python311 = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $python311) {
  Write-Warning "[bootstrap] py launcher not found; uv will still enforce Python 3.11 during sync."
}

$webView2Key = "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F1D0E5F1-2D4B-4A2E-84D1-2F03C642B90D}"
if (-not (Test-Path $webView2Key)) {
  Write-Warning "[bootstrap] Microsoft Edge WebView2 Runtime was not detected. Install it before Tauri runtime validation."
}

Invoke-Checked -FilePath "uv" -Arguments @("sync", "--python", "3.11", "--extra", "dev", "--frozen")
Invoke-Checked -FilePath "corepack" -Arguments @("enable")
Invoke-Checked -FilePath "pnpm" -Arguments @("install", "--dir", "apps/operator-panel", "--frozen-lockfile")

Write-Output "[bootstrap] Windows development dependencies are ready."
