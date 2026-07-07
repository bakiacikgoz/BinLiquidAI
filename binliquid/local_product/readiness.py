from __future__ import annotations

from binliquid.local_product.models import (
    GateCheckResult,
    LocalEnvironmentProbe,
    LocalProductClaimBoundary,
    LocalProductReadinessReport,
    PlatformTarget,
)
from binliquid.local_product.platforms import SUPPORTED_TARGETS


def evaluate_local_product_readiness(
    *,
    profile: str,
    target: PlatformTarget,
    probe: LocalEnvironmentProbe,
    checks: list[GateCheckResult],
    artifacts: dict[str, str] | None = None,
) -> LocalProductReadinessReport:
    required_failures = [
        code
        for check in checks
        if check.required and check.status in {"fail", "blocked"}
        for code in (check.reason_codes or [f"{check.name.upper()}_FAILED"])
    ]
    non_required_failures = [
        check for check in checks if not check.required and check.status in {"fail", "blocked"}
    ]
    if target.support_tier == "unsupported":
        overall = "blocked"
        required_failures.append("UNSUPPORTED_PLATFORM_TARGET")
    elif required_failures:
        overall = "blocked"
    elif non_required_failures:
        overall = "conditional"
    else:
        overall = "pass"
    claim_allowed = overall in {"pass", "conditional"} and target.support_tier == "supported"
    supported_claims = [target.target_id] if claim_allowed else []
    not_evidenced = [
        item for item in SUPPORTED_TARGETS if item != target.target_id or not claim_allowed
    ]
    boundary = LocalProductClaimBoundary(
        targetId=target.target_id,
        claimAllowed=claim_allowed,
        supportedClaims=supported_claims,
        notEvidencedTargets=not_evidenced,
        unsupportedTargets=[] if target.support_tier != "unsupported" else [target.target_id],
        blockedTargets=[target.target_id] if required_failures else [],
        productClaimSummary=(
            f"Claims are limited to evidenced target {target.target_id}."
            if claim_allowed
            else "No supported platform claim is allowed without passing evidence."
        ),
        blockingReasons=required_failures,
    )
    return LocalProductReadinessReport(
        profile=profile,
        target=target.model_copy(update={"claim_allowed": claim_allowed, "reason_codes": []}),
        probe=probe,
        checks=checks,
        overallStatus=overall,
        claimBoundary=boundary,
        noShipBlockers=required_failures,
        artifacts=artifacts or {},
        secretScanStatus="pass",
        rawPromptPersisted=False,
        liveComputerUseEnabled=False,
    )

