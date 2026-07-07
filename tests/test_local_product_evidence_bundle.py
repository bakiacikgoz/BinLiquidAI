from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from binliquid.local_product.evidence_bundle import (
    EvidenceBundleError,
    export_platform_evidence_bundle,
    read_bundle_entries,
)
from binliquid.local_product.evidence_collector import collect_platform_evidence


def test_export_platform_evidence_bundle_writes_manifest_and_index(tmp_path: Path) -> None:
    manifest = collect_platform_evidence(
        profile="enterprise",
        target="windows-x64",
        output_root=tmp_path / "evidence",
    )
    bundle = export_platform_evidence_bundle(
        manifest_path=tmp_path / "evidence" / "platform_evidence_manifest.json",
        bundle_path=tmp_path / "bundle.zip",
    )

    assert bundle.status == "pass"
    assert bundle.target_id == manifest.target.target_id
    with zipfile.ZipFile(tmp_path / "bundle.zip") as archive:
        assert sorted(archive.namelist()) == [
            "bundle_index.json",
            "platform_evidence_manifest.json",
        ]


def test_read_bundle_entries_blocks_zip_slip(tmp_path: Path) -> None:
    bundle = tmp_path / "evil.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("../../evil.txt", "bad")

    with pytest.raises(EvidenceBundleError):
        read_bundle_entries(bundle)


def test_export_rejects_unsafe_artifact_path(tmp_path: Path) -> None:
    collect_platform_evidence(
        profile="enterprise",
        target="windows-x64",
        output_root=tmp_path / "evidence",
    )
    manifest_path = tmp_path / "evidence" / "platform_evidence_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["commands"][0]["artifactPaths"] = ["../secret.txt"]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvidenceBundleError):
        export_platform_evidence_bundle(
            manifest_path=manifest_path,
            bundle_path=tmp_path / "bundle.zip",
        )
