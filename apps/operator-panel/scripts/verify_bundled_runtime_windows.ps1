param(
  [Parameter(Mandatory = $true)]
  [string]$RuntimeDir
)

$ErrorActionPreference = "Stop"

function Get-FileSha256 {
  param([string]$Path)

  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Read-RuntimeManifest {
  param([string]$Path)

  $values = @{}
  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if ($line.Length -eq 0 -or $line.StartsWith("#")) {
      return
    }
    $separator = $line.IndexOf("=")
    if ($separator -lt 1) {
      throw "[verify] invalid manifest line: $line"
    }
    $key = $line.Substring(0, $separator)
    $value = $line.Substring($separator + 1)
    if ($values.ContainsKey($key)) {
      throw "[verify] duplicate manifest key: $key"
    }
    $values[$key] = $value
  }
  return $values
}

function Assert-ManifestValue {
  param(
    [hashtable]$Manifest,
    [string]$Key
  )

  if (-not $Manifest.ContainsKey($Key) -or [string]::IsNullOrWhiteSpace([string]$Manifest[$Key])) {
    throw "[verify] missing manifest key: $Key"
  }
}

function Assert-Sha256 {
  param(
    [hashtable]$Manifest,
    [string]$Key
  )

  Assert-ManifestValue -Manifest $Manifest -Key $Key
  if ([string]$Manifest[$Key] -notmatch "^[0-9a-fA-F]{64}$") {
    throw "[verify] invalid sha256 format for ${Key}: $($Manifest[$Key])"
  }
}

function Assert-ExactManifestKeys {
  param(
    [hashtable]$Manifest,
    [string[]]$AllowedKeys
  )

  if ($Manifest.Count -ne $AllowedKeys.Count) {
    throw "[verify] manifest key set mismatch"
  }
  foreach ($key in $Manifest.Keys) {
    if ($AllowedKeys -notcontains $key) {
      throw "[verify] unexpected manifest key: $key"
    }
  }
}

$ResolvedRuntimeDir = (Resolve-Path -LiteralPath $RuntimeDir).Path
$ManifestPath = Join-Path $ResolvedRuntimeDir "RUNTIME_MANIFEST.txt"
$RuntimePython = Join-Path $ResolvedRuntimeDir "python\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
  throw "[verify] missing manifest: $ManifestPath"
}
if (-not (Test-Path -LiteralPath $RuntimePython -PathType Leaf)) {
  throw "[verify] missing runtime Python: $RuntimePython"
}

$Manifest = Read-RuntimeManifest -Path $ManifestPath

$AllowedManifestKeys = @(
  "platform",
  "arch",
  "python",
  "imperaos_version",
  "created_at_utc",
  "source_wheel",
  "source_wheel_sha256",
  "python_exe_sha256",
  "uv_lock_sha256",
  "git_sha"
)
Assert-ExactManifestKeys -Manifest $Manifest -AllowedKeys $AllowedManifestKeys
$AllowedManifestKeys | ForEach-Object { Assert-ManifestValue -Manifest $Manifest -Key $_ }

if ($Manifest["platform"] -ne "windows") {
  throw "[verify] expected platform=windows, got $($Manifest["platform"])"
}
if ($Manifest["arch"] -ne "x86_64") {
  throw "[verify] expected arch=x86_64, got $($Manifest["arch"])"
}
if ($Manifest["python"] -ne "python/Scripts/python.exe") {
  throw "[verify] expected python=python/Scripts/python.exe, got $($Manifest["python"])"
}

Assert-Sha256 -Manifest $Manifest -Key "source_wheel_sha256"
Assert-Sha256 -Manifest $Manifest -Key "python_exe_sha256"
if ($Manifest["uv_lock_sha256"] -ne "missing") {
  Assert-Sha256 -Manifest $Manifest -Key "uv_lock_sha256"
}

$ActualPythonHash = Get-FileSha256 -Path $RuntimePython
if ($ActualPythonHash -ne ([string]$Manifest["python_exe_sha256"]).ToLowerInvariant()) {
  throw "[verify] python_exe_sha256 mismatch: expected $($Manifest["python_exe_sha256"]), got $ActualPythonHash"
}

$VersionOutput = @(& $RuntimePython -m imperaos --version)
if ($LASTEXITCODE -ne 0 -or $VersionOutput.Count -eq 0) {
  throw "[verify] runtime validation failed: $RuntimePython -m imperaos --version"
}
$ActualVersion = ($VersionOutput -join "`n").Trim()
$ManifestVersion = ([string]$Manifest["imperaos_version"]).Trim()
if ([string]::IsNullOrWhiteSpace($ActualVersion) -or $ActualVersion -ne $ManifestVersion) {
  throw "[verify] imperaos_version mismatch: expected $ManifestVersion, got $ActualVersion"
}

Write-Output "[verify] runtime_dir=$ResolvedRuntimeDir"
Write-Output "[verify] imperaos_version=$ActualVersion"
Write-Output "[verify] python_exe_sha256=$ActualPythonHash"
Write-Output "[verify] manifest=pass"
