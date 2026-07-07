from __future__ import annotations

import json
import subprocess
from pathlib import Path

from binliquid.local_product.evidence_bundle import sha256_file
from binliquid.local_product.evidence_importer import DEFAULT_EVIDENCE_STORE, load_imported_records
from binliquid.local_product.evidence_models import (
    PlatformRCHandoffManifest,
    PlatformRCHandoffVerification,
)
from binliquid.local_product.evidence_reconciler import (
    current_git_commit,
    reconcile_platform_evidence,
)


def _git_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        shell=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def build_local_product_rc_handoff(
    *,
    profile: str,
    evidence_root: Path = DEFAULT_EVIDENCE_STORE,
    output_root: Path = Path("artifacts") / "local-product-rc-handoff",
) -> PlatformRCHandoffManifest:
    del profile
    output_root.mkdir(parents=True, exist_ok=True)
    reconciliation = reconcile_platform_evidence(store_root=evidence_root)
    reconciliation_path = output_root / "platform_evidence_reconciliation.json"
    reconciliation_path.write_text(
        json.dumps(reconciliation.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    product_closure_path = (
        Path("artifacts") / "product-complete-closure" / "product_complete_closure_report.json"
    )
    product_status = "missing"
    if product_closure_path.exists():
        try:
            product_status = json.loads(product_closure_path.read_text(encoding="utf-8")).get(
                "status",
                "unknown",
            )
        except json.JSONDecodeError:
            product_status = "invalid"
    records = load_imported_records(evidence_root)
    repo_root = Path.cwd()
    evidence_bundles = [
        {
            "targetId": record.target_id,
            "path": _relative(Path(record.record_path).parent / "bundle.zip", repo_root),
            "sha256": record.bundle_sha256,
        }
        for record in records
    ]
    if reconciliation.status != "pass" or product_status in {"blocked", "fail", "invalid"}:
        status = "blocked"
    elif product_status == "pass":
        status = "ready"
    else:
        status = "conditional"
    manifest = PlatformRCHandoffManifest(
        status=status,
        gitCommit=current_git_commit(),
        branch=_git_branch(),
        reconciliationPath=_relative(reconciliation_path, output_root),
        productClosurePath=_relative(product_closure_path, repo_root),
        evidenceBundles=evidence_bundles,
        supportedClaims=[
            f"{target} source/local install evidenced"
            for target in reconciliation.evidenced_targets
        ],
        blockedClaims=[blocker.reason_code for blocker in reconciliation.no_ship_blockers],
        operatorNextSteps=[
            "Collect and import evidence for not-evidenced targets before claiming support.",
            "Run product-complete closure before release-candidate review.",
        ],
        hashLedger={},
    )
    manifest_path = output_root / "manifest.json"
    markdown_path = output_root / "LOCAL_PRODUCT_RC_HANDOFF.md"
    pr_body_path = output_root / "PRODUCT_COMPLETE_PR_BODY.md"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_rc_handoff_markdown(manifest), encoding="utf-8")
    pr_body_path.write_text(render_rc_handoff_pr_body(manifest), encoding="utf-8")
    hash_ledger = {
        "LOCAL_PRODUCT_RC_HANDOFF.md": sha256_file(markdown_path),
        "PRODUCT_COMPLETE_PR_BODY.md": sha256_file(pr_body_path),
        "platform_evidence_reconciliation.json": sha256_file(reconciliation_path),
    }
    manifest = manifest.model_copy(update={"hash_ledger": hash_ledger})
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return manifest


def render_rc_handoff_markdown(manifest: PlatformRCHandoffManifest) -> str:
    claims = "\n".join(f"- {claim}" for claim in manifest.supported_claims) or "- none"
    blockers = "\n".join(f"- {claim}" for claim in manifest.blocked_claims) or "- none"
    return (
        "# Local Product RC Handoff\n\n"
        f"- Status: `{manifest.status}`\n"
        f"- Branch: `{manifest.branch}`\n"
        f"- Commit: `{manifest.git_commit}`\n\n"
        "## Supported Claims\n\n"
        f"{claims}\n\n"
        "## Blocked Claims\n\n"
        f"{blockers}\n"
    )


def render_rc_handoff_pr_body(manifest: PlatformRCHandoffManifest) -> str:
    return (
        "## Local Product RC Handoff\n\n"
        f"- status: `{manifest.status}`\n"
        f"- reconciliation: `{manifest.reconciliation_path}`\n"
        f"- product closure: `{manifest.product_closure_path}`\n"
    )


def verify_local_product_rc_handoff(*, manifest_path: Path) -> PlatformRCHandoffVerification:
    reason_codes: list[str] = []
    try:
        manifest = PlatformRCHandoffManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ValueError):
        return PlatformRCHandoffVerification(
            status="blocked",
            manifestPath=str(manifest_path),
            hashesValid=False,
            reasonCodes=["LOCAL_PRODUCT_RC_HANDOFF_MANIFEST_INVALID"],
        )
    hashes_valid = True
    root = manifest_path.parent
    for relative, expected_hash in manifest.hash_ledger.items():
        file_path = root / relative
        if not file_path.exists() or sha256_file(file_path) != expected_hash:
            hashes_valid = False
            reason_codes.append("LOCAL_PRODUCT_RC_HANDOFF_HASH_MISMATCH")
    if manifest.status == "blocked":
        reason_codes.append("LOCAL_PRODUCT_RC_HANDOFF_BLOCKED")
    return PlatformRCHandoffVerification(
        status="pass" if hashes_valid and not reason_codes else "blocked",
        manifestPath=str(manifest_path),
        hashesValid=hashes_valid,
        reasonCodes=sorted(set(reason_codes)),
    )
