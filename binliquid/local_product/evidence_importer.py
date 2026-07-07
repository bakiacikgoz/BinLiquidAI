from __future__ import annotations

import json
import shutil
from pathlib import Path

from binliquid.local_product.evidence_bundle import sha256_file
from binliquid.local_product.evidence_models import (
    ImportedPlatformEvidenceRecord,
    PlatformEvidenceVerification,
)
from binliquid.local_product.evidence_verifier import (
    load_manifest_from_bundle,
    verify_platform_evidence_bundle,
)

DEFAULT_EVIDENCE_STORE = Path(".binliquid") / "local-product" / "evidence"


class EvidenceImportError(ValueError):
    pass


def import_platform_evidence_bundle(
    *,
    bundle_path: Path,
    store_root: Path = DEFAULT_EVIDENCE_STORE,
    verification: PlatformEvidenceVerification | None = None,
) -> ImportedPlatformEvidenceRecord:
    bundle_sha = sha256_file(bundle_path)
    verification = verification or verify_platform_evidence_bundle(bundle_path=bundle_path)
    if verification.status != "pass":
        raise EvidenceImportError("PLATFORM_EVIDENCE_IMPORT_REJECTED")
    manifest = load_manifest_from_bundle(bundle_path)
    record_dir = store_root / manifest.target.target_id / manifest.evidence_id.replace(":", "_")
    record_path = record_dir / "record.json"
    status = "already_imported" if record_path.exists() else "imported"
    record_dir.mkdir(parents=True, exist_ok=True)
    (record_dir / "platform_evidence_manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    shutil.copy2(bundle_path, record_dir / "bundle.zip")
    record = ImportedPlatformEvidenceRecord(
        status=status,
        evidenceId=manifest.evidence_id,
        targetId=manifest.target.target_id,
        gitCommit=manifest.git_commit,
        bundleSha256=bundle_sha,
        recordPath=str(record_path),
        verification=verification,
    )
    record_path.write_text(
        json.dumps(record.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return record


def load_imported_records(
    store_root: Path = DEFAULT_EVIDENCE_STORE,
) -> list[ImportedPlatformEvidenceRecord]:
    if not store_root.exists():
        return []
    records: list[ImportedPlatformEvidenceRecord] = []
    for record_path in sorted(store_root.rglob("record.json")):
        records.append(
            ImportedPlatformEvidenceRecord.model_validate_json(
                record_path.read_text(encoding="utf-8")
            )
        )
    return records
