from __future__ import annotations

from binliquid.local_product.models import GateCheckResult, LocalEnvironmentProbe
from binliquid.local_product.platforms import parse_target
from binliquid.local_product.readiness import evaluate_local_product_readiness


def _probe(target_id: str = "windows-x64") -> LocalEnvironmentProbe:
    return LocalEnvironmentProbe(
        target=parse_target(target_id),
        pythonVersion="Python 3.11.9",
        uvAvailable=True,
        nodeVersion="v22.12.0",
        pnpmMode="local_bin",
        rustcVersion="rustc 1.88.0",
        cargoAvailable=True,
        tauriCliAvailable=False,
        webviewStatus="available",
        pathStyle="windows",
        newlineMode="unknown",
        detectedAt="2026-07-07T00:00:00Z",
    )


def test_required_failures_block_readiness_claim() -> None:
    report = evaluate_local_product_readiness(
        profile="enterprise",
        target=parse_target("windows-x64"),
        probe=_probe(),
        checks=[
            GateCheckResult(
                name="operator_panel_build",
                status="fail",
                required=True,
                reasonCodes=["NODE_RUNTIME_MISSING"],
                redacted=True,
            )
        ],
    )

    assert report.overall_status == "blocked"
    assert report.claim_boundary.claim_allowed is False
    assert "NODE_RUNTIME_MISSING" in report.no_ship_blockers


def test_non_required_failures_are_conditional_not_claim_blockers() -> None:
    report = evaluate_local_product_readiness(
        profile="enterprise",
        target=parse_target("windows-x64"),
        probe=_probe(),
        checks=[
            GateCheckResult(
                name="tauri_generated_permissions",
                status="fail",
                required=False,
                reasonCodes=["TAURI_PERMISSIONS_DIAGNOSTIC_FAILED"],
                redacted=True,
            )
        ],
    )

    assert report.overall_status == "conditional"
    assert report.claim_boundary.claim_allowed is True
    assert report.no_ship_blockers == []

