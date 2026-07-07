from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from binliquid.local_product.evidence_models import (
    PlatformEvidenceBundleSummary,
    PlatformEvidenceManifest,
)

MANIFEST_ENTRY = "platform_evidence_manifest.json"
BUNDLE_INDEX_ENTRY = "bundle_index.json"


class EvidenceBundleError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_safe_relative_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and value.strip() == value


def _load_manifest(path: Path) -> PlatformEvidenceManifest:
    return PlatformEvidenceManifest.model_validate_json(path.read_text(encoding="utf-8"))


def export_platform_evidence_bundle(
    *,
    manifest_path: Path,
    bundle_path: Path,
) -> PlatformEvidenceBundleSummary:
    if not manifest_path.exists():
        raise EvidenceBundleError("PLATFORM_EVIDENCE_MANIFEST_MISSING")
    manifest = _load_manifest(manifest_path)
    for command in manifest.commands:
        for artifact_path in command.artifact_paths:
            if not is_safe_relative_path(artifact_path):
                raise EvidenceBundleError("PLATFORM_EVIDENCE_UNSAFE_ARTIFACT_PATH")
    manifest_bytes = json.dumps(
        manifest.model_dump(mode="json", by_alias=True),
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    index: dict[str, Any] = {
        "schemaVersion": "local-product-platform-evidence-bundle-index/v1",
        "files": {
            MANIFEST_ENTRY: sha256_bytes(manifest_bytes),
        },
    }
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_ENTRY, manifest_bytes)
        archive.writestr(
            BUNDLE_INDEX_ENTRY,
            json.dumps(index, indent=2, sort_keys=True).encode("utf-8"),
        )
    return PlatformEvidenceBundleSummary(
        status="pass",
        bundlePath=str(bundle_path),
        bundleSha256=sha256_file(bundle_path),
        targetId=manifest.target.target_id,
        gitCommit=manifest.git_commit,
        fileCount=2,
        reasonCodes=[],
    )


def read_bundle_entries(bundle_path: Path) -> dict[str, bytes]:
    if not bundle_path.exists():
        raise EvidenceBundleError("PLATFORM_EVIDENCE_BUNDLE_MISSING")
    if bundle_path.is_dir():
        entries: dict[str, bytes] = {}
        for file_path in sorted(path for path in bundle_path.rglob("*") if path.is_file()):
            relative = file_path.relative_to(bundle_path).as_posix()
            if not is_safe_relative_path(relative):
                raise EvidenceBundleError("PLATFORM_EVIDENCE_ZIP_SLIP")
            entries[relative] = file_path.read_bytes()
        return entries
    entries = {}
    with zipfile.ZipFile(bundle_path, "r") as archive:
        for info in archive.infolist():
            if not is_safe_relative_path(info.filename):
                raise EvidenceBundleError("PLATFORM_EVIDENCE_ZIP_SLIP")
            entries[info.filename] = archive.read(info)
    return entries
