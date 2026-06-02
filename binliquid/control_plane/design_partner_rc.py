from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from binliquid.control_plane.models import (
    AlertSummary,
    DataSourceState,
    DesignPartnerRcCheck,
    DesignPartnerRcStatus,
    EvidencePackSummary,
    ExecutionSurfaceSummary,
    ReportSummary,
)


def build_design_partner_rc_status(
    *,
    data_source: DataSourceState,
    claims: dict[str, Any],
    evidence_packs: list[EvidencePackSummary],
    reports: list[ReportSummary],
    alerts: list[AlertSummary],
    execution_surfaces: list[ExecutionSurfaceSummary],
    generated_at: datetime | None = None,
    artifact_root: str = "artifacts/design-partner-rc",
) -> DesignPartnerRcStatus:
    """Aggregate Design Partner RC readiness without opening blocked claims."""

    checks = [
        _check(
            "runtime-truth",
            "Runtime truth",
            not data_source.is_silent_fallback and data_source.mode != "error",
            f"mode={data_source.mode} silentFallback={data_source.is_silent_fallback}",
            blocking=True,
        ),
        _conditional_check(
            "preview-source",
            "Preview source boundary",
            data_source.mode != "preview_fixture",
            f"mode={data_source.mode}",
        ),
        _conditional_check(
            "evidence-index",
            "Evidence coverage",
            len(evidence_packs) > 0,
            f"{len(evidence_packs)} evidence pack(s)",
        ),
        _conditional_check(
            "reports",
            "Report coverage",
            any(report.status == "ready" for report in reports),
            f"{sum(1 for report in reports if report.status == 'ready')} ready report(s)",
        ),
        _check(
            "computer-use-boundary",
            "Computer-use claim boundary",
            _surface_status(execution_surfaces, "computer-use") == "blocked",
            f"computer-use={_surface_status(execution_surfaces, 'computer-use')}",
            blocking=True,
        ),
        _check(
            "public-desktop-boundary",
            "Public desktop claim boundary",
            _surface_status(execution_surfaces, "public-desktop-installer") == "blocked",
            "public-desktop-installer="
            f"{_surface_status(execution_surfaces, 'public-desktop-installer')}",
            blocking=True,
        ),
        _conditional_check(
            "enterprise-hat-a",
            "Enterprise Hat A evidence",
            _claim_status(claims, "enterprise-self-hosted-agent-control-plane") == "allowed",
            f"status={_claim_status(claims, 'enterprise-self-hosted-agent-control-plane')}",
        ),
        _conditional_check(
            "active-alerts",
            "Active alert review",
            not any(
                alert.status == "active" and alert.severity in {"error", "critical"}
                for alert in alerts
            ),
            f"{sum(1 for alert in alerts if alert.status == 'active')} active alert(s)",
        ),
    ]
    blockers = [check.check_id for check in checks if check.status == "failed" and check.blocking]
    warnings = [check.check_id for check in checks if check.status == "conditional"]
    status = "blocked" if blockers else "conditional" if warnings else "ready"

    return DesignPartnerRcStatus(
        generated_at_utc=generated_at or datetime.now(UTC),
        status=status,
        checks=checks,
        blockers=blockers,
        warnings=warnings,
        artifact_root=artifact_root,
    )


def _check(
    check_id: str,
    label: str,
    passed: bool,
    detail: str,
    *,
    blocking: bool,
) -> DesignPartnerRcCheck:
    return DesignPartnerRcCheck(
        check_id=check_id,
        label=label,
        status="passed" if passed else "failed",
        detail=detail,
        blocking=blocking,
    )


def _conditional_check(
    check_id: str,
    label: str,
    passed: bool,
    detail: str,
) -> DesignPartnerRcCheck:
    return DesignPartnerRcCheck(
        check_id=check_id,
        label=label,
        status="passed" if passed else "conditional",
        detail=detail,
        blocking=False,
    )


def _claim_status(claims: dict[str, Any], claim_id: str) -> str:
    for claim in claims.get("claims", []):
        if isinstance(claim, dict) and claim.get("claim_id") == claim_id:
            return str(claim.get("status", "conditional"))
    return "conditional"


def _surface_status(surfaces: list[ExecutionSurfaceSummary], surface_id: str) -> str:
    for surface in surfaces:
        if surface.surface_id == surface_id:
            return surface.status
    return "missing"
