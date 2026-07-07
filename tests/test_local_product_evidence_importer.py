from __future__ import annotations

from pathlib import Path

import pytest

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle
from binliquid.local_product.evidence_collector import collect_platform_evidence
from binliquid.local_product.evidence_importer import (
    EvidenceImportError,
    import_platform_evidence_bundle,
)
from binliquid.local_product.evidence_models import PlatformEvidenceVerification


def _bundle(tmp_path: Path) -> Path:
    collect_platform_evidence(
        profile="enterprise",
        target="windows-x64",
        output_root=tmp_path / "evidence",
    )
    export_platform_evidence_bundle(
        manifest_path=tmp_path / "evidence" / "platform_evidence_manifest.json",
        bundle_path=tmp_path / "bundle.zip",
    )
    return tmp_path / "bundle.zip"


def test_import_platform_evidence_bundle_is_idempotent(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)

    first = import_platform_evidence_bundle(bundle_path=bundle, store_root=tmp_path / "store")
    second = import_platform_evidence_bundle(bundle_path=bundle, store_root=tmp_path / "store")

    assert first.status == "imported"
    assert second.status == "already_imported"
    assert (tmp_path / "store").exists()


def test_import_rejects_failed_verification(tmp_path: Path) -> None:
    failed = PlatformEvidenceVerification(
        status="blocked",
        bundlePath=str(tmp_path / "bundle.zip"),
        targetId="windows-x64",
        commitMatch=False,
        targetMatch=True,
        schemaValid=True,
        hashesValid=True,
        secretScanPass=True,
        fresh=True,
        reasonCodes=["PLATFORM_EVIDENCE_COMMIT_MISMATCH"],
    )

    with pytest.raises(EvidenceImportError):
        import_platform_evidence_bundle(
            bundle_path=_bundle(tmp_path),
            store_root=tmp_path / "store",
            verification=failed,
        )
