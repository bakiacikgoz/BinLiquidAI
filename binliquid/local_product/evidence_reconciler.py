from __future__ import annotations

import subprocess
from pathlib import Path

from binliquid.local_product.evidence_importer import (
    DEFAULT_EVIDENCE_STORE,
    load_imported_records,
)
from binliquid.local_product.evidence_models import (
    ImportedPlatformEvidenceRecord,
    PlatformEvidenceReconciliation,
    PlatformNoShipBlocker,
    TargetReconciliation,
)
from binliquid.local_product.targets import default_target_registry


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        shell=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _record_sort_key(record: ImportedPlatformEvidenceRecord) -> tuple[float, str]:
    try:
        modified_at = Path(record.record_path).stat().st_mtime
    except OSError:
        modified_at = 0.0
    return (modified_at, record.evidence_id)


def reconcile_platform_evidence(
    *,
    evidence_records: list[ImportedPlatformEvidenceRecord] | None = None,
    claimed_targets: list[str] | None = None,
    current_commit: str | None = None,
    store_root: Path = DEFAULT_EVIDENCE_STORE,
) -> PlatformEvidenceReconciliation:
    current_commit = current_commit or current_git_commit()
    claimed_targets = claimed_targets or []
    records = (
        evidence_records if evidence_records is not None else load_imported_records(store_root)
    )
    latest_by_target: dict[str, ImportedPlatformEvidenceRecord] = {}
    for record in records:
        existing = latest_by_target.get(record.target_id)
        if existing is None or _record_sort_key(record) > _record_sort_key(existing):
            latest_by_target[record.target_id] = record
    targets: dict[str, TargetReconciliation] = {}
    evidenced_targets: list[str] = []
    not_evidenced_targets: list[str] = []
    blockers: list[PlatformNoShipBlocker] = []
    warnings: list[str] = []
    for target in default_target_registry(include_experimental=False):
        record = latest_by_target.get(target.target_id)
        if record is None:
            targets[target.target_id] = TargetReconciliation(
                targetId=target.target_id,
                status="not_evidenced",
                reasonCodes=["TARGET_NOT_EVIDENCED"],
                source="none",
            )
            not_evidenced_targets.append(target.target_id)
            continue
        if record.git_commit != current_commit:
            targets[target.target_id] = TargetReconciliation(
                targetId=target.target_id,
                status="stale",
                evidenceId=record.evidence_id,
                gitCommit=record.git_commit,
                bundleSha256=record.bundle_sha256,
                reasonCodes=["PLATFORM_EVIDENCE_COMMIT_MISMATCH"],
                source="imported",
            )
            not_evidenced_targets.append(target.target_id)
            warnings.append(f"{target.target_id} evidence was produced for a different commit.")
            continue
        if record.verification.status != "pass":
            targets[target.target_id] = TargetReconciliation(
                targetId=target.target_id,
                status="blocked",
                evidenceId=record.evidence_id,
                gitCommit=record.git_commit,
                bundleSha256=record.bundle_sha256,
                reasonCodes=record.verification.reason_codes,
                source="imported",
            )
            blockers.append(
                PlatformNoShipBlocker(
                    reasonCode="PLATFORM_EVIDENCE_VERIFICATION_FAILED",
                    targetId=target.target_id,
                    message=f"{target.target_id} evidence verification failed.",
                )
            )
            continue
        targets[target.target_id] = TargetReconciliation(
            targetId=target.target_id,
            status="evidenced",
            evidenceId=record.evidence_id,
            gitCommit=record.git_commit,
            bundleSha256=record.bundle_sha256,
            reasonCodes=[],
            source="imported",
        )
        evidenced_targets.append(target.target_id)
    for claimed_target in claimed_targets:
        if claimed_target not in evidenced_targets:
            blockers.append(
                PlatformNoShipBlocker(
                    reasonCode="PLATFORM_CLAIM_WITHOUT_EVIDENCE",
                    targetId=claimed_target,
                    message=f"{claimed_target} was claimed without matching evidence.",
                )
            )
    status = "blocked" if blockers else "pass"
    return PlatformEvidenceReconciliation(
        status=status,
        gitCommit=current_commit,
        targets=targets,
        claimedTargets=claimed_targets,
        evidencedTargets=sorted(evidenced_targets),
        notEvidencedTargets=sorted(not_evidenced_targets),
        noShipBlockers=blockers,
        warnings=warnings,
    )
