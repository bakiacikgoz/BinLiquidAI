from __future__ import annotations

from binliquid.local_product.models import LocalProductReadinessReport, PlatformClaimDecision
from binliquid.local_product.platforms import SUPPORTED_TARGETS

OVERBROAD_CLAIM_MARKERS = (
    "all processors",
    "every cpu",
    "all desktop cpus",
    "her islemci",
    "her işlemci",
)


def evaluate_platform_claims(
    reports: list[LocalProductReadinessReport],
    requested_claim: str | None = None,
    existing_decision: PlatformClaimDecision | None = None,
) -> PlatformClaimDecision:
    if existing_decision is not None:
        return existing_decision
    supported = sorted(
        {
            report.target.target_id
            for report in reports
            if report.overall_status in {"pass", "conditional"}
            and report.claim_boundary.claim_allowed
        }
    )
    blocked = sorted(
        {
            report.target.target_id
            for report in reports
            if report.overall_status in {"blocked", "fail"}
        }
    )
    not_evidenced = [
        target for target in SUPPORTED_TARGETS if target not in supported and target not in blocked
    ]
    blocking_reasons: list[str] = []
    normalized_claim = (requested_claim or "").lower()
    if supported and any(marker in normalized_claim for marker in OVERBROAD_CLAIM_MARKERS):
        blocking_reasons.append("OVERBROAD_PLATFORM_CLAIM")
    status = "blocked" if blocking_reasons else "pass"
    return PlatformClaimDecision(
        status=status,
        supportedClaims=supported,
        notEvidencedTargets=not_evidenced,
        unsupportedTargets=[],
        blockedTargets=blocked,
        productClaimSummary=(
            "Supported platform claims are limited to evidenced targets: "
            + (", ".join(supported) if supported else "none")
        ),
        blockingReasons=blocking_reasons,
    )
