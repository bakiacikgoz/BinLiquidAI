from __future__ import annotations

import json
import zipfile
from pathlib import Path

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle
from binliquid.local_product.evidence_collector import collect_platform_evidence
from binliquid.local_product.evidence_verifier import verify_platform_evidence_bundle


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


def test_verify_platform_evidence_bundle_passes_valid_bundle(tmp_path: Path) -> None:
    verification = verify_platform_evidence_bundle(bundle_path=_bundle(tmp_path))

    assert verification.status == "pass"
    assert verification.hashes_valid is True
    assert verification.secret_scan_pass is True


def test_verify_platform_evidence_bundle_blocks_commit_mismatch(tmp_path: Path) -> None:
    verification = verify_platform_evidence_bundle(
        bundle_path=_bundle(tmp_path),
        expected_commit="0" * 40,
    )

    assert verification.status == "blocked"
    assert "PLATFORM_EVIDENCE_COMMIT_MISMATCH" in verification.reason_codes


def test_verify_platform_evidence_bundle_blocks_secret_marker(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    with zipfile.ZipFile(bundle, "r") as archive:
        manifest = json.loads(archive.read("platform_evidence_manifest.json"))
        index = json.loads(archive.read("bundle_index.json"))
    manifest["limitations"] = ["api_key = sk-testsecret123456789"]
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("platform_evidence_manifest.json", json.dumps(manifest))
        archive.writestr("bundle_index.json", json.dumps(index))

    verification = verify_platform_evidence_bundle(bundle_path=bundle)

    assert verification.status == "blocked"
    assert "PLATFORM_EVIDENCE_SECRET_LEAK" in verification.reason_codes
