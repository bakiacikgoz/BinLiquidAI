from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from binliquid.local_product.evidence_bundle import (
    BUNDLE_INDEX_ENTRY,
    MANIFEST_ENTRY,
    EvidenceBundleError,
    read_bundle_entries,
    sha256_bytes,
)
from binliquid.local_product.evidence_models import (
    PlatformEvidenceManifest,
    PlatformEvidenceVerification,
)

SECRET_MARKERS = (
    "sk-",
    "api_key",
    "private key",
    "BEGIN PRIVATE KEY",
    "session_token",
    "C:\\Users\\",
    "/Users/",
)


def _has_secret_marker(entries: dict[str, bytes]) -> bool:
    for content in entries.values():
        text = content.decode("utf-8", errors="ignore")
        if any(marker in text for marker in SECRET_MARKERS):
            return True
    return False


def _fresh(generated_at: str, freshness_window_days: int) -> bool:
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed >= datetime.now(UTC) - timedelta(days=freshness_window_days)


def verify_platform_evidence_bundle(
    *,
    bundle_path: Path,
    expected_commit: str | None = None,
    expected_head_sha: str | None = None,
    expected_target: str | None = None,
    freshness_window_days: int = 30,
) -> PlatformEvidenceVerification:
    reason_codes: list[str] = []
    entries: dict[str, bytes] = {}
    manifest: PlatformEvidenceManifest | None = None
    hashes_valid = False
    schema_valid = False
    try:
        entries = read_bundle_entries(bundle_path)
        if MANIFEST_ENTRY not in entries:
            reason_codes.append("PLATFORM_EVIDENCE_MANIFEST_MISSING")
        if BUNDLE_INDEX_ENTRY not in entries:
            reason_codes.append("PLATFORM_EVIDENCE_HASH_INDEX_MISSING")
        if not reason_codes:
            index = json.loads(entries[BUNDLE_INDEX_ENTRY].decode("utf-8"))
            expected_hash = index.get("files", {}).get(MANIFEST_ENTRY)
            hashes_valid = expected_hash == sha256_bytes(entries[MANIFEST_ENTRY])
            if not hashes_valid:
                reason_codes.append("PLATFORM_EVIDENCE_HASH_MISMATCH")
            manifest = PlatformEvidenceManifest.model_validate_json(
                entries[MANIFEST_ENTRY].decode("utf-8")
            )
            schema_valid = True
    except (EvidenceBundleError, json.JSONDecodeError, ValueError) as exc:
        reason_codes.append(str(exc) or "PLATFORM_EVIDENCE_SCHEMA_INVALID")
    secret_scan_pass = not _has_secret_marker(entries) if entries else False
    if not secret_scan_pass:
        reason_codes.append("PLATFORM_EVIDENCE_SECRET_LEAK")
    target_id = manifest.target.target_id if manifest else None
    expected_commit = expected_commit or expected_head_sha
    commit_match = bool(
        manifest and (expected_commit is None or manifest.git_commit == expected_commit)
    )
    target_match = bool(manifest and (expected_target is None or target_id == expected_target))
    fresh = bool(manifest and _fresh(manifest.generated_at, freshness_window_days))
    if manifest and not commit_match:
        reason_codes.append("PLATFORM_EVIDENCE_COMMIT_MISMATCH")
    if manifest and not target_match:
        reason_codes.append("PLATFORM_EVIDENCE_TARGET_MISMATCH")
    if manifest and not fresh:
        reason_codes.append("PLATFORM_EVIDENCE_STALE")
    if not schema_valid and "PLATFORM_EVIDENCE_SCHEMA_INVALID" not in reason_codes:
        reason_codes.append("PLATFORM_EVIDENCE_SCHEMA_INVALID")
    status = "pass" if not reason_codes else "blocked"
    return PlatformEvidenceVerification(
        status=status,
        bundlePath=str(bundle_path),
        targetId=target_id,
        commitMatch=commit_match,
        targetMatch=target_match,
        schemaValid=schema_valid,
        hashesValid=hashes_valid,
        secretScanPass=secret_scan_pass,
        fresh=fresh,
        reasonCodes=sorted(set(reason_codes)),
    )


def load_manifest_from_bundle(bundle_path: Path) -> PlatformEvidenceManifest:
    entries = read_bundle_entries(bundle_path)
    return PlatformEvidenceManifest.model_validate_json(entries[MANIFEST_ENTRY].decode("utf-8"))
