from __future__ import annotations

from typing import Literal

from pydantic import Field

from binliquid.local_product.artifact_sources import current_git_head, utc_now
from binliquid.local_product.evidence_importer import DEFAULT_EVIDENCE_STORE
from binliquid.local_product.evidence_models import PlatformEvidenceReconciliation
from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence
from binliquid.local_product.release_claims import (
    SOURCE_INSTALL_CLAIM_SET,
    SOURCE_INSTALL_TARGET_BLOCKED,
    SOURCE_INSTALL_TARGET_STALE,
    SOURCE_INSTALL_TARGET_WITHOUT_EVIDENCE,
)
from binliquid.memory.models import StrictModel


class SourceInstallBlockedTarget(StrictModel):
    target: str
    reason_code: str = Field(alias="reasonCode")
    message: str


class SourceInstallClaimPolicy(StrictModel):
    claim_set: Literal["source-local-install"] = Field(
        default=SOURCE_INSTALL_CLAIM_SET,
        alias="claimSet",
    )
    expected_head_sha: str | None = Field(default=None, alias="expectedHeadSha")
    evidence_max_age_hours: int = Field(default=168, alias="evidenceMaxAgeHours")
    requested_targets: list[str] = Field(default_factory=list, alias="requestedTargets")


class SourceInstallRcClaim(StrictModel):
    schema_version: Literal["source_install_rc_claim/v1"] = Field(
        default="source_install_rc_claim/v1",
        alias="schemaVersion",
    )
    claim_set: Literal["source-local-install"] = Field(
        default=SOURCE_INSTALL_CLAIM_SET,
        alias="claimSet",
    )
    status: Literal["pass", "conditional", "blocked"]
    claimed_targets: list[str] = Field(default_factory=list, alias="claimedTargets")
    not_evidenced_targets: list[str] = Field(default_factory=list, alias="notEvidencedTargets")
    blocked_targets: list[SourceInstallBlockedTarget] = Field(
        default_factory=list,
        alias="blockedTargets",
    )
    head_sha: str = Field(alias="headSha")
    evidence_max_age_hours: int = Field(alias="evidenceMaxAgeHours")
    release_notes_allowed_claims: list[str] = Field(
        default_factory=list,
        alias="releaseNotesAllowedClaims",
    )
    no_ship_blockers: list[str] = Field(default_factory=list, alias="noShipBlockers")
    generated_at_utc: str = Field(default_factory=utc_now, alias="generatedAtUtc")


def build_source_install_rc_claim(
    *,
    reconciliation: PlatformEvidenceReconciliation | None = None,
    policy: SourceInstallClaimPolicy | None = None,
    evidence_root=DEFAULT_EVIDENCE_STORE,
) -> SourceInstallRcClaim:
    policy = policy or SourceInstallClaimPolicy()
    expected_head = policy.expected_head_sha or current_git_head()
    reconciliation = reconciliation or reconcile_platform_evidence(
        store_root=evidence_root,
        current_commit=expected_head,
    )
    claimed_targets = sorted(reconciliation.evidenced_targets)
    not_evidenced = sorted(reconciliation.not_evidenced_targets)
    blocked: list[SourceInstallBlockedTarget] = []
    no_ship: list[str] = []

    for target_id, target in sorted(reconciliation.targets.items()):
        if target.status == "stale":
            blocked.append(
                SourceInstallBlockedTarget(
                    target=target_id,
                    reasonCode=SOURCE_INSTALL_TARGET_STALE,
                    message=f"{target_id} evidence is stale for {expected_head}.",
                )
            )
        elif target.status == "blocked":
            blocked.append(
                SourceInstallBlockedTarget(
                    target=target_id,
                    reasonCode=SOURCE_INSTALL_TARGET_BLOCKED,
                    message=f"{target_id} evidence verification is blocked.",
                )
            )

    for requested in sorted(set(policy.requested_targets)):
        if requested not in claimed_targets:
            blocked.append(
                SourceInstallBlockedTarget(
                    target=requested,
                    reasonCode=SOURCE_INSTALL_TARGET_WITHOUT_EVIDENCE,
                    message=(
                        f"{requested} was requested for source install RC claim "
                        "without evidence."
                    ),
                )
            )

    if blocked:
        no_ship = sorted({item.reason_code for item in blocked})

    return SourceInstallRcClaim(
        status="blocked" if blocked else "pass",
        claimedTargets=claimed_targets,
        notEvidencedTargets=not_evidenced,
        blockedTargets=blocked,
        headSha=expected_head,
        evidenceMaxAgeHours=policy.evidence_max_age_hours,
        releaseNotesAllowedClaims=[
            f"{target} source-local-install evidenced" for target in claimed_targets
        ],
        noShipBlockers=no_ship,
    )
