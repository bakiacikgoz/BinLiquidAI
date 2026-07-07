from __future__ import annotations

from binliquid.release.product_complete import (
    ProductCompleteInput,
    build_product_complete_no_ship_register,
)
from scripts.run_product_complete_closure_gate import run_product_complete_closure_gate


def test_product_complete_blocks_platform_claim_without_evidence() -> None:
    register = build_product_complete_no_ship_register(
        ProductCompleteInput(platformClaimWithoutEvidence=True)
    )

    assert "PLATFORM_CLAIM_WITHOUT_EVIDENCE" in [
        item.reason_code for item in register.items
    ]


def test_product_complete_blocks_source_install_overclaim() -> None:
    register = build_product_complete_no_ship_register(
        ProductCompleteInput(sourceInstallTargetWithoutEvidence=True)
    )

    assert "SOURCE_INSTALL_TARGET_WITHOUT_EVIDENCE" in [
        item.reason_code for item in register.items
    ]


def test_product_complete_closure_attaches_platform_evidence_reconciliation(tmp_path) -> None:
    report = run_product_complete_closure_gate(
        output_root=tmp_path,
        profile="enterprise",
        skip_commands=True,
    )

    reconciliation = report["platformEvidenceReconciliation"]
    assert reconciliation["artifactVersion"] == "local-product-platform-reconciliation/v1"
    assert "windows-x64" in reconciliation["targets"]
    assert report["platformEvidenceHarvest"]["schemaVersion"] == "local_product_harvest/v1"
    assert report["sourceInstallRcClaim"]["schemaVersion"] == "source_install_rc_claim/v1"
    assert report["releaseClaimAccuracy"]["status"] in {"pass", "blocked"}
    assert isinstance(report["targetClosureActions"], list)
    assert report["noShipBlockers"] == []
