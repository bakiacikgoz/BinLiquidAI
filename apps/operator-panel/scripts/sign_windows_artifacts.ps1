param(
  [Parameter(Mandatory = $true)]
  [string]$ArtifactPath,
  [Parameter(Mandatory = $true)]
  [string]$CertPfxPath,
  [Parameter(Mandatory = $true)]
  [string]$CertPassword,
  [string]$TimestampUrl = "http://timestamp.digicert.com",
  [string]$EvidencePath = ""
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

$SignOutput = & $SignTool.Source sign `
  /fd SHA256 `
  /tr $TimestampUrl `
  /td SHA256 `
  /f $CertPfxPath `
  /p $CertPassword `
  $ArtifactPath 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "[sign] signtool sign failed for $ArtifactPath"
}

$VerifyOutput = & $SignTool.Source verify /pa /v $ArtifactPath 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "[sign] signtool verify failed for $ArtifactPath"
}

if (-not [string]::IsNullOrWhiteSpace($EvidencePath)) {
  $evidenceDir = Split-Path -Parent $EvidencePath
  if (-not [string]::IsNullOrWhiteSpace($evidenceDir)) {
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
  }
  @{
    artifact_name = Split-Path -Leaf $ArtifactPath
    signed = $true
    timestamped = -not [string]::IsNullOrWhiteSpace($TimestampUrl)
    timestamp_url_configured = -not [string]::IsNullOrWhiteSpace($TimestampUrl)
    signtool_verify_status = "pass"
    signature_subject_present = $true
    certificate_thumbprint_present = $true
    sign_output_line_count = @($SignOutput).Count
    verify_output_line_count = @($VerifyOutput).Count
  } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $EvidencePath -Encoding utf8
}

Write-Output "[sign] signed_and_verified=$ArtifactPath"
