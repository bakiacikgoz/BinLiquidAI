param(
  [ValidateSet("x64")]
  [string]$Arch = "x64",
  [string]$PythonBin = "py -3.11",
  [string]$WheelPath = ""
)

$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
  param([string]$Command)

  $trimmed = $Command.Trim()
  if ($trimmed.Length -eq 0) {
    throw "[runtime] PythonBin must not be empty"
  }

  if (Test-Path -LiteralPath $trimmed) {
    return @{ Exe = (Resolve-Path -LiteralPath $trimmed).Path; Args = @() }
  }

  $parts = $trimmed -split "\s+"
  return @{ Exe = $parts[0]; Args = @($parts | Select-Object -Skip 1) }
}

function Invoke-Checked {
  param(
    [string]$FilePath,
    [string[]]$Arguments
  )

  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "[runtime] command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
  }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..\..\..")).Path
$AppDir = Join-Path $RepoRoot "apps\operator-panel"
$RuntimeDir = Join-Path $AppDir "src-tauri\resources\binliquid-runtime"
$RuntimeParent = Split-Path -Parent $RuntimeDir
$RuntimePythonDir = Join-Path $RuntimeDir "python"
$RuntimePython = Join-Path $RuntimePythonDir "Scripts\python.exe"
$DistDir = Join-Path $RepoRoot "dist"

if ($Arch -ne "x64") {
  throw "[runtime] unsupported arch: $Arch"
}

$RuntimeParentResolved = (Resolve-Path -LiteralPath $RuntimeParent).Path
if (-not $RuntimeDir.StartsWith($RuntimeParentResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "[runtime] refusing to clean unexpected runtime path: $RuntimeDir"
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

if ([string]::IsNullOrWhiteSpace($WheelPath)) {
  Write-Host "[runtime] building binliquid wheel"
  Push-Location $RepoRoot
  try {
    Invoke-Checked -FilePath "uv" -Arguments @("build", "--wheel", "--out-dir", $DistDir)
  } finally {
    Pop-Location
  }
  $latestWheel = Get-ChildItem -Path $DistDir -Filter "binliquid-*.whl" |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
  if ($null -eq $latestWheel) {
    throw "[runtime] no binliquid wheel found in $DistDir"
  }
  $WheelPath = $latestWheel.FullName
}

if (-not (Test-Path -LiteralPath $WheelPath -PathType Leaf)) {
  throw "[runtime] wheel not found: $WheelPath"
}

$python = Resolve-PythonCommand -Command $PythonBin

Write-Host "[runtime] target platform=windows arch=$Arch"
if (Test-Path -LiteralPath $RuntimeDir) {
  Remove-Item -LiteralPath $RuntimeDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

Invoke-Checked -FilePath $python.Exe -Arguments @($python.Args + @("-m", "venv", $RuntimePythonDir))

if (-not (Test-Path -LiteralPath $RuntimePython -PathType Leaf)) {
  throw "[runtime] invalid runtime: expected $RuntimePython"
}

Invoke-Checked -FilePath $RuntimePython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "wheel")
Invoke-Checked -FilePath $RuntimePython -Arguments @("-m", "pip", "install", $WheelPath)

$version = (& $RuntimePython -m binliquid --version)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
  throw "[runtime] runtime validation failed: $RuntimePython -m binliquid --version"
}

$manifest = @(
  "platform=windows",
  "arch=x86_64",
  "python=python/Scripts/python.exe",
  "binliquid_version=$($version.Trim())",
  "created_at_utc=$((Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"))",
  "source_wheel=$WheelPath"
)
$manifest | Set-Content -LiteralPath (Join-Path $RuntimeDir "RUNTIME_MANIFEST.txt") -Encoding utf8

@"
Generated Windows runtime bundle for AegisOS Operator Panel.

Release gate:
1) python/Scripts/python.exe exists
2) python/Scripts/python.exe -m binliquid --version passes
3) RUNTIME_MANIFEST.txt records platform, arch, Python entrypoint, and source wheel

Do not ship placeholder-only runtime contents.
"@ | Set-Content -LiteralPath (Join-Path $RuntimeDir "README.txt") -Encoding utf8

Write-Host "[runtime] bundled runtime ready: $RuntimeDir"
