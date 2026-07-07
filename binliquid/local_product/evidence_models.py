from __future__ import annotations

from typing import Literal

from pydantic import Field

from binliquid.local_product.targets import PlatformTargetDefinition
from binliquid.memory.models import StrictModel

EvidenceStatus = Literal[
    "evidenced",
    "not_evidenced",
    "stale",
    "mismatch",
    "unsupported",
    "blocked",
]


class HostProbe(StrictModel):
    host_id_hash: str = Field(alias="hostIdHash")
    target_id: str = Field(alias="targetId")
    os_name: str = Field(alias="osName")
    os_version: str = Field(alias="osVersion")
    machine: str
    python_version: str = Field(alias="pythonVersion")
    node_version: str | None = Field(default=None, alias="nodeVersion")
    rust_version: str | None = Field(default=None, alias="rustVersion")
    git_commit: str = Field(alias="gitCommit")
    branch: str | None = None


class CommandEvidence(StrictModel):
    command_id: str = Field(alias="commandId")
    display_name: str = Field(alias="displayName")
    status: Literal["pass", "fail", "skipped", "not_available"]
    exit_code: int | None = Field(default=None, alias="exitCode")
    duration_ms: int = Field(alias="durationMs")
    stdout_hash: str | None = Field(default=None, alias="stdoutHash")
    stderr_hash: str | None = Field(default=None, alias="stderrHash")
    artifact_paths: list[str] = Field(default_factory=list, alias="artifactPaths")
    reason_code: str | None = Field(default=None, alias="reasonCode")


class RawArtifactPolicy(StrictModel):
    raw_prompt_persisted: bool = Field(default=False, alias="rawPromptPersisted")
    provider_payload_persisted: bool = Field(default=False, alias="providerPayloadPersisted")
    secrets_persisted: bool = Field(default=False, alias="secretsPersisted")


class PlatformEvidenceManifest(StrictModel):
    artifact_version: Literal["local-product-platform-evidence/v1"] = Field(
        default="local-product-platform-evidence/v1",
        alias="artifactVersion",
    )
    evidence_id: str = Field(alias="evidenceId")
    target: PlatformTargetDefinition
    host_probe: HostProbe = Field(alias="hostProbe")
    profile: str
    git_commit: str = Field(alias="gitCommit")
    generated_at: str = Field(alias="generatedAt")
    commands: list[CommandEvidence]
    readiness_status: Literal["pass", "fail", "partial", "blocked"] = Field(
        alias="readinessStatus"
    )
    claim_status: Literal["evidenced", "not_evidenced", "blocked"] = Field(
        alias="claimStatus"
    )
    secret_scan_status: Literal["pass", "fail"] = Field(alias="secretScanStatus")
    raw_artifact_policy: RawArtifactPolicy = Field(alias="rawArtifactPolicy")
    hashes: dict[str, str] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class PlatformEvidenceBundleSummary(StrictModel):
    artifact_version: Literal["local-product-platform-evidence-bundle/v1"] = Field(
        default="local-product-platform-evidence-bundle/v1",
        alias="artifactVersion",
    )
    status: Literal["pass", "fail"]
    bundle_path: str = Field(alias="bundlePath")
    bundle_sha256: str = Field(alias="bundleSha256")
    target_id: str = Field(alias="targetId")
    git_commit: str = Field(alias="gitCommit")
    file_count: int = Field(alias="fileCount")
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")


class PlatformEvidenceVerification(StrictModel):
    artifact_version: Literal["local-product-platform-evidence-verification/v1"] = Field(
        default="local-product-platform-evidence-verification/v1",
        alias="artifactVersion",
    )
    status: Literal["pass", "fail", "blocked"]
    bundle_path: str = Field(alias="bundlePath")
    target_id: str | None = Field(default=None, alias="targetId")
    commit_match: bool = Field(alias="commitMatch")
    target_match: bool = Field(alias="targetMatch")
    schema_valid: bool = Field(alias="schemaValid")
    hashes_valid: bool = Field(alias="hashesValid")
    secret_scan_pass: bool = Field(alias="secretScanPass")
    fresh: bool
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")


class ImportedPlatformEvidenceRecord(StrictModel):
    artifact_version: Literal["local-product-platform-evidence-import/v1"] = Field(
        default="local-product-platform-evidence-import/v1",
        alias="artifactVersion",
    )
    status: Literal["imported", "already_imported", "blocked"]
    evidence_id: str = Field(alias="evidenceId")
    target_id: str = Field(alias="targetId")
    git_commit: str = Field(alias="gitCommit")
    bundle_sha256: str = Field(alias="bundleSha256")
    record_path: str = Field(alias="recordPath")
    verification: PlatformEvidenceVerification


class PlatformNoShipBlocker(StrictModel):
    reason_code: str = Field(alias="reasonCode")
    target_id: str | None = Field(default=None, alias="targetId")
    message: str


class TargetReconciliation(StrictModel):
    target_id: str = Field(alias="targetId")
    status: EvidenceStatus
    evidence_id: str | None = Field(default=None, alias="evidenceId")
    git_commit: str | None = Field(default=None, alias="gitCommit")
    bundle_sha256: str | None = Field(default=None, alias="bundleSha256")
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")
    source: Literal["current_host", "imported", "none"] = "none"


class PlatformEvidenceReconciliation(StrictModel):
    artifact_version: Literal["local-product-platform-reconciliation/v1"] = Field(
        default="local-product-platform-reconciliation/v1",
        alias="artifactVersion",
    )
    status: Literal["pass", "fail", "blocked"]
    git_commit: str = Field(alias="gitCommit")
    targets: dict[str, TargetReconciliation]
    claimed_targets: list[str] = Field(default_factory=list, alias="claimedTargets")
    evidenced_targets: list[str] = Field(default_factory=list, alias="evidencedTargets")
    not_evidenced_targets: list[str] = Field(default_factory=list, alias="notEvidencedTargets")
    no_ship_blockers: list[PlatformNoShipBlocker] = Field(
        default_factory=list,
        alias="noShipBlockers",
    )
    warnings: list[str] = Field(default_factory=list)


class PlatformRCHandoffManifest(StrictModel):
    artifact_version: Literal["local-product-rc-handoff/v1"] = Field(
        default="local-product-rc-handoff/v1",
        alias="artifactVersion",
    )
    status: Literal["ready", "conditional", "blocked"]
    git_commit: str = Field(alias="gitCommit")
    branch: str
    reconciliation_path: str = Field(alias="reconciliationPath")
    product_closure_path: str = Field(alias="productClosurePath")
    evidence_bundles: list[dict[str, str]] = Field(default_factory=list, alias="evidenceBundles")
    supported_claims: list[str] = Field(default_factory=list, alias="supportedClaims")
    blocked_claims: list[str] = Field(default_factory=list, alias="blockedClaims")
    operator_next_steps: list[str] = Field(default_factory=list, alias="operatorNextSteps")
    hash_ledger: dict[str, str] = Field(default_factory=dict, alias="hashLedger")


class PlatformRCHandoffVerification(StrictModel):
    artifact_version: Literal["local-product-rc-handoff-verification/v1"] = Field(
        default="local-product-rc-handoff-verification/v1",
        alias="artifactVersion",
    )
    status: Literal["pass", "fail", "blocked"]
    manifest_path: str = Field(alias="manifestPath")
    hashes_valid: bool = Field(alias="hashesValid")
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")
