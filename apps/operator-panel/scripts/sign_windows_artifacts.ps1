param(
  [Parameter(Mandatory = $true)]
  [string]$ArtifactPath,
  [Parameter(Mandatory = $true)]
  [string]$CertPfxPath,
  [Parameter(Mandatory = $true)]
  [string]$CertPassword,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ArtifactPath -PathType Leaf)) {
  throw "[sign] artifact not found: $ArtifactPath"
}
if (-not (Test-Path -LiteralPath $CertPfxPath -PathType Leaf)) {
  throw "[sign] certificate PFX not found"
}

$SignTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if ($null -eq $SignTool) {
  throw "[sign] signtool.exe not found; install Windows SDK signing tools on the runner"
}

& $SignTool.Source sign `
  /fd SHA256 `
  /tr $TimestampUrl `
  /td SHA256 `
  /f $CertPfxPath `
  /p $CertPassword `
  $ArtifactPath
if ($LASTEXITCODE -ne 0) {
  throw "[sign] signtool sign failed for $ArtifactPath"
}

& $SignTool.Source verify /pa /v $ArtifactPath
if ($LASTEXITCODE -ne 0) {
  throw "[sign] signtool verify failed for $ArtifactPath"
}

Write-Output "[sign] signed_and_verified=$ArtifactPath"
