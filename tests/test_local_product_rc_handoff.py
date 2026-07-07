from __future__ import annotations

from pathlib import Path

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle
from binliquid.local_product.evidence_collector import collect_platform_evidence
from binliquid.local_product.evidence_importer import import_platform_evidence_bundle
from binliquid.local_product.rc_handoff import (
    build_local_product_rc_handoff,
    verify_local_product_rc_handoff,
)


def test_rc_handoff_builds_and_verifies(tmp_path: Path) -> None:
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

    manifest = build_local_product_rc_handoff(
        profile="enterprise",
        evidence_root=tmp_path / "store",
        output_root=tmp_path / "handoff",
    )
    verification = verify_local_product_rc_handoff(
        manifest_path=tmp_path / "handoff" / "manifest.json"
    )

    assert manifest.status in {"ready", "conditional"}
    assert verification.status == "pass"
    assert (tmp_path / "handoff" / "LOCAL_PRODUCT_RC_HANDOFF.md").exists()
