from __future__ import annotations

from binliquid.local_product.claim_guard import evaluate_platform_claims
from binliquid.local_product.models import PlatformClaimDecision
from binliquid.release.product_complete import (
    ProductCompleteInput,
    build_product_complete_no_ship_register,
)
from scripts.run_product_complete_closure_gate import run_product_complete_closure_gate


def test_product_complete_blocks_overbroad_platform_claims() -> None:
    register = build_product_complete_no_ship_register(
        ProductCompleteInput(localProductOverbroadPlatformClaim=True)
    )

    reason_codes = [item.reason_code for item in register.items]
    assert "LOCAL_PRODUCT_OVERBROAD_PLATFORM_CLAIM" in reason_codes


def test_product_complete_allows_not_evidenced_targets_without_blocker() -> None:
    decision = PlatformClaimDecision(
        schemaVersion="local_product_claim_boundary/v1",
        status="pass",
        supportedClaims=["windows-x64"],
        notEvidencedTargets=["darwin-arm64", "darwin-x64", "linux-x64"],
        unsupportedTargets=[],
        blockedTargets=[],
        productClaimSummary="Supported claims are limited to evidenced targets.",
        blockingReasons=[],
    )

    assert evaluate_platform_claims([], existing_decision=decision).status == "pass"


def test_product_complete_closure_attaches_local_product_readiness(tmp_path) -> None:
    report = run_product_complete_closure_gate(
        output_root=tmp_path,
        profile="enterprise",
        skip_commands=True,
    )

    readiness = report["localProductReadiness"]
    assert readiness["currentTarget"]
    assert "notEvidencedTargets" in readiness
    assert readiness["noShipBlockers"] == []
