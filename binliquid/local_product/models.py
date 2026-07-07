from __future__ import annotations

from typing import Literal

from pydantic import Field

from binliquid.memory.models import StrictModel

PlatformOs = Literal["darwin", "windows", "linux", "unknown"]
PlatformArch = Literal["arm64", "x64", "unknown"]
SupportTier = Literal["supported", "experimental", "not_evidenced", "unsupported"]
CheckStatus = Literal["pass", "fail", "blocked", "skipped", "not_applicable"]
ReadinessStatus = Literal["pass", "conditional", "blocked", "fail"]


class PlatformTarget(StrictModel):
    os: PlatformOs
    arch: PlatformArch
    target_id: str = Field(alias="targetId")
    support_tier: SupportTier = Field(default="not_evidenced", alias="supportTier")
    claim_allowed: bool = Field(default=False, alias="claimAllowed")
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")


class LocalEnvironmentProbe(StrictModel):
    target: PlatformTarget
    python_version: str = Field(alias="pythonVersion")
    uv_available: bool = Field(alias="uvAvailable")
    node_version: str | None = Field(alias="nodeVersion")
    pnpm_mode: Literal["corepack", "local_bin", "missing"] = Field(alias="pnpmMode")
    rustc_version: str | None = Field(alias="rustcVersion")
    cargo_available: bool = Field(alias="cargoAvailable")
    tauri_cli_available: bool = Field(alias="tauriCliAvailable")
    webview_status: Literal["available", "missing", "not_applicable", "unknown"] = Field(
        alias="webviewStatus"
    )
    path_style: Literal["posix", "windows"] = Field(alias="pathStyle")
    newline_mode: Literal["lf", "crlf", "mixed", "unknown"] = Field(alias="newlineMode")
    detected_at: str = Field(alias="detectedAt")


class GateCheckResult(StrictModel):
    name: str
    status: CheckStatus
    required: bool
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")
    artifact_path: str | None = Field(default=None, alias="artifactPath")
    duration_ms: int | None = Field(default=None, alias="durationMs")
    redacted: bool = True


class LocalProductClaimBoundary(StrictModel):
    schema_version: Literal["local_product_claim_boundary/v1"] = Field(
        default="local_product_claim_boundary/v1",
        alias="schemaVersion",
    )
    target_id: str = Field(alias="targetId")
    claim_allowed: bool = Field(alias="claimAllowed")
    supported_claims: list[str] = Field(default_factory=list, alias="supportedClaims")
    not_evidenced_targets: list[str] = Field(default_factory=list, alias="notEvidencedTargets")
    unsupported_targets: list[str] = Field(default_factory=list, alias="unsupportedTargets")
    blocked_targets: list[str] = Field(default_factory=list, alias="blockedTargets")
    product_claim_summary: str = Field(alias="productClaimSummary")
    blocking_reasons: list[str] = Field(default_factory=list, alias="blockingReasons")


class LocalProductReadinessReport(StrictModel):
    schema_version: Literal["local_product_readiness/v1"] = Field(
        default="local_product_readiness/v1",
        alias="schemaVersion",
    )
    profile: str
    target: PlatformTarget
    probe: LocalEnvironmentProbe
    checks: list[GateCheckResult]
    overall_status: ReadinessStatus = Field(alias="overallStatus")
    claim_boundary: LocalProductClaimBoundary = Field(alias="claimBoundary")
    no_ship_blockers: list[str] = Field(default_factory=list, alias="noShipBlockers")
    artifacts: dict[str, str] = Field(default_factory=dict)
    secret_scan_status: Literal["pass", "fail"] = Field(default="pass", alias="secretScanStatus")
    raw_prompt_persisted: bool = Field(default=False, alias="rawPromptPersisted")
    live_computer_use_enabled: bool = Field(default=False, alias="liveComputerUseEnabled")


class PlatformClaimDecision(StrictModel):
    schema_version: Literal["local_product_claim_boundary/v1"] = Field(
        default="local_product_claim_boundary/v1",
        alias="schemaVersion",
    )
    status: Literal["pass", "blocked"]
    supported_claims: list[str] = Field(default_factory=list, alias="supportedClaims")
    not_evidenced_targets: list[str] = Field(default_factory=list, alias="notEvidencedTargets")
    unsupported_targets: list[str] = Field(default_factory=list, alias="unsupportedTargets")
    blocked_targets: list[str] = Field(default_factory=list, alias="blockedTargets")
    product_claim_summary: str = Field(alias="productClaimSummary")
    blocking_reasons: list[str] = Field(default_factory=list, alias="blockingReasons")


class PlatformReadinessMatrix(StrictModel):
    schema_version: Literal["local_product_readiness_matrix/v1"] = Field(
        default="local_product_readiness_matrix/v1",
        alias="schemaVersion",
    )
    targets: list[LocalProductReadinessReport]
    supported_claims: list[str] = Field(default_factory=list, alias="supportedClaims")
    not_evidenced_targets: list[str] = Field(default_factory=list, alias="notEvidencedTargets")
    unsupported_targets: list[str] = Field(default_factory=list, alias="unsupportedTargets")
    blocked_targets: list[str] = Field(default_factory=list, alias="blockedTargets")
    product_claim_summary: str = Field(alias="productClaimSummary")

