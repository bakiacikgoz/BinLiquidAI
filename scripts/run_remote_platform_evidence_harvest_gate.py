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

from binliquid.local_product.artifact_sources import (  # noqa: E402
    current_git_branch,
    current_git_head,
)
from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle  # noqa: E402
from binliquid.local_product.evidence_collector import collect_platform_evidence  # noqa: E402
from binliquid.local_product.harvest import HarvestRequest, harvest_platform_evidence  # noqa: E402

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "local-product" / "harvest"


def run_remote_platform_evidence_harvest_gate(
    *,
    profile: str = "enterprise",
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    if output_root.exists():
        shutil.rmtree(output_root)
    evidence_root = output_root / "local-current"
    bundle_path = output_root / "bundles" / "local-current.zip"
    manifest = collect_platform_evidence(
        profile=profile,
        target="current",
        output_root=evidence_root,
    )
    export_platform_evidence_bundle(
        manifest_path=evidence_root / "platform_evidence_manifest.json",
        bundle_path=bundle_path,
    )
    harvest = harvest_platform_evidence(
        request=HarvestRequest(
            profile=profile,
            branch=current_git_branch(),
            headSha=current_git_head(),
            outputRoot=str(output_root),
            evidenceStore=str(output_root / "store"),
            manualBundle=str(bundle_path),
        )
    )
    status = (
        "pass"
        if harvest.status in {"pass", "conditional"} and not harvest.blockers
        else "blocked"
    )
    return {
        "schemaVersion": "remote_platform_evidence_harvest_gate/v1",
        "status": status,
        "profile": profile,
        "localEvidenceTarget": manifest.target.target_id,
        "harvest": harvest.model_dump(mode="json", by_alias=True),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run remote platform evidence harvest gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = run_remote_platform_evidence_harvest_gate(
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
