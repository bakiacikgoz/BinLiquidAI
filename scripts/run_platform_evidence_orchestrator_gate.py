from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle  # noqa: E402
from binliquid.local_product.evidence_collector import collect_platform_evidence  # noqa: E402
from binliquid.local_product.evidence_importer import import_platform_evidence_bundle  # noqa: E402
from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence  # noqa: E402
from binliquid.local_product.evidence_verifier import verify_platform_evidence_bundle  # noqa: E402
from binliquid.local_product.rc_handoff import (  # noqa: E402
    build_local_product_rc_handoff,
    verify_local_product_rc_handoff,
)

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "local-product-platform-evidence"


def run_platform_evidence_orchestrator_gate(
    *,
    profile: str = "enterprise",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    evidence_root = output_root / "evidence"
    bundle_root = output_root / "bundles"
    store_root = output_root / "store"
    handoff_root = REPO_ROOT / "artifacts" / "local-product-rc-handoff"
    if output_root.exists():
        shutil.rmtree(output_root)
    manifest = collect_platform_evidence(
        profile=profile,
        target="current",
        output_root=evidence_root / "current",
    )
    bundle = export_platform_evidence_bundle(
        manifest_path=evidence_root / "current" / "platform_evidence_manifest.json",
        bundle_path=bundle_root / f"{manifest.target.target_id}.zip",
    )
    verification = verify_platform_evidence_bundle(bundle_path=Path(bundle.bundle_path))
    imported = import_platform_evidence_bundle(
        bundle_path=Path(bundle.bundle_path),
        store_root=store_root,
        verification=verification,
    )
    reconciliation = reconcile_platform_evidence(store_root=store_root)
    handoff = build_local_product_rc_handoff(
        profile=profile,
        evidence_root=store_root,
        output_root=handoff_root,
    )
    handoff_verification = verify_local_product_rc_handoff(
        manifest_path=handoff_root / "manifest.json"
    )
    status = (
        "pass"
        if verification.status == "pass"
        and imported.status in {"imported", "already_imported"}
        and reconciliation.status == "pass"
        and handoff_verification.status == "pass"
        else "blocked"
    )
    return {
        "schemaVersion": "local-product-platform-evidence-orchestrator-gate/v1",
        "status": status,
        "profile": profile,
        "manifest": manifest.model_dump(mode="json", by_alias=True),
        "bundle": bundle.model_dump(mode="json", by_alias=True),
        "verification": verification.model_dump(mode="json", by_alias=True),
        "imported": imported.model_dump(mode="json", by_alias=True),
        "reconciliation": reconciliation.model_dump(mode="json", by_alias=True),
        "handoff": handoff.model_dump(mode="json", by_alias=True),
        "handoffVerification": handoff_verification.model_dump(mode="json", by_alias=True),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run platform evidence orchestrator gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = run_platform_evidence_orchestrator_gate(
        profile=args.profile,
        output_root=args.output_root,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
