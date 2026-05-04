param(
  [Parameter(Mandatory = $true)]
  [string]$ArtifactPath,
  [Parameter(Mandatory = $true)]
  [string]$CertPfxPath,
  [Parameter(Mandatory = $true)]
  [string]$CertPassword,
  [string]$TimestampUrl = "",
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

if ([string]::IsNullOrWhiteSpace($TimestampUrl)) {
  $TimestampUrl = $env:WINDOWS_TIMESTAMP_URL
}
if ([string]::IsNullOrWhiteSpace($TimestampUrl)) {
  $TimestampUrl = "http://timestamp.digicert.com"
}

$ArtifactHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ArtifactPath).Hash.ToLowerInvariant()
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

$Signature = Get-AuthenticodeSignature -LiteralPath $ArtifactPath
$Timestamped = $false
$TimestampProofSource = "missing"
if ($Signature.PSObject.Properties.Name -contains "TimeStamperCertificate") {
  $Timestamped = $null -ne $Signature.TimeStamperCertificate
  if ($Timestamped) {
    $TimestampProofSource = "Get-AuthenticodeSignature.TimeStamperCertificate"
  }
}
$Signed = $Signature.Status -eq "Valid"
$CertificateThumbprintPresent = $false
$CertificateSubjectPresent = $false
if ($Signature.SignerCertificate) {
  $CertificateThumbprintPresent = -not [string]::IsNullOrWhiteSpace($Signature.SignerCertificate.Thumbprint)
  $CertificateSubjectPresent = -not [string]::IsNullOrWhiteSpace($Signature.SignerCertificate.Subject)
}

if (-not [string]::IsNullOrWhiteSpace($EvidencePath)) {
  $evidenceDir = Split-Path -Parent $EvidencePath
  if (-not [string]::IsNullOrWhiteSpace($evidenceDir)) {
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
  }
  @{
    artifact_name = Split-Path -Leaf $ArtifactPath
    artifact_sha256 = $ArtifactHash
    signed = $Signed
    signature_status = [string]$Signature.Status
    timestamped = $Timestamped
    timestamp_proof_source = $TimestampProofSource
    timestamp_url_configured = -not [string]::IsNullOrWhiteSpace($TimestampUrl)
    signtool_sign_status = "pass"
    signtool_verify_status = "pass"
    certificate_subject_present = $CertificateSubjectPresent
    certificate_thumbprint_present = $CertificateThumbprintPresent
    secret_material_written = $false
    sign_output_line_count = @($SignOutput).Count
    verify_output_line_count = @($VerifyOutput).Count
  } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $EvidencePath -Encoding utf8
}

if (-not $Signed) {
  throw "[sign] Authenticode signature is not valid for $ArtifactPath"
}
if (-not $Timestamped) {
  throw "[sign] Authenticode timestamp proof missing for $ArtifactPath"
}

Write-Output "[sign] signed_and_verified=$ArtifactPath"
