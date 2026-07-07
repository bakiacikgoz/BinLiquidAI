from __future__ import annotations

from pathlib import Path

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle
from binliquid.local_product.evidence_collector import collect_platform_evidence
from binliquid.local_product.evidence_importer import import_platform_evidence_bundle
from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence


def _import_current(tmp_path: Path) -> None:
    collect_platform_evidence(
        profile="enterprise",
        target="windows-x64",
        output_root=tmp_path / "evidence",
    )
    export_platform_evidence_bundle(
        manifest_path=tmp_path / "evidence" / "platform_evidence_manifest.json",
        bundle_path=tmp_path / "bundle.zip",
    )
    import_platform_evidence_bundle(
        bundle_path=tmp_path / "bundle.zip",
        store_root=tmp_path / "store",
    )


def test_reconcile_marks_imported_target_evidenced(tmp_path: Path) -> None:
    _import_current(tmp_path)

    report = reconcile_platform_evidence(store_root=tmp_path / "store")

    assert report.status == "pass"
    assert "windows-x64" in report.evidenced_targets
    assert "darwin-arm64" in report.not_evidenced_targets


def test_reconcile_blocks_claim_without_evidence(tmp_path: Path) -> None:
    report = reconcile_platform_evidence(
        store_root=tmp_path / "missing",
        claimed_targets=["darwin-arm64"],
    )

    assert report.status == "blocked"
    assert report.no_ship_blockers[0].reason_code == "PLATFORM_CLAIM_WITHOUT_EVIDENCE"
