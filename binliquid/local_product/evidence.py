from __future__ import annotations

import json
from pathlib import Path

from binliquid.local_product.models import LocalProductReadinessReport


def write_local_product_evidence(
    report: LocalProductReadinessReport,
    output_root: Path,
) -> dict[str, str]:
    target_root = output_root / report.target.target_id
    target_root.mkdir(parents=True, exist_ok=True)
    json_path = target_root / "local_product_readiness_report.json"
    markdown_path = target_root / "LOCAL_PRODUCT_READINESS.md"
    manifest_path = target_root / "evidence_manifest.json"
    payload = report.model_dump(mode="json", by_alias=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    manifest = {
        "schemaVersion": "local_product_evidence_manifest/v1",
        "targetId": report.target.target_id,
        "files": [str(json_path), str(markdown_path)],
        "rawPromptPersisted": False,
        "secretScanStatus": report.secret_scan_status,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"json": str(json_path), "markdown": str(markdown_path), "manifest": str(manifest_path)}


def render_markdown(payload: dict[str, object]) -> str:
    target = payload.get("target", {})
    target_id = target.get("targetId") if isinstance(target, dict) else "unknown"
    boundary = payload.get("claimBoundary", {})
    supported = boundary.get("supportedClaims", []) if isinstance(boundary, dict) else []
    not_evidenced = boundary.get("notEvidencedTargets", []) if isinstance(boundary, dict) else []
    return (
        "# Local Product Readiness\n\n"
        f"- Target: `{target_id}`\n"
        f"- Status: `{payload.get('overallStatus')}`\n"
        f"- Supported claims: `{', '.join(supported) if supported else 'none'}`\n"
        f"- Not evidenced targets: `{', '.join(not_evidenced) if not_evidenced else 'none'}`\n"
        "- Raw prompt persisted: `false`\n"
        "- Live computer-use enabled: `false`\n"
    )
