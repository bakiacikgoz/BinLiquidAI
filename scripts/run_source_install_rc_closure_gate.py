from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.local_product.artifact_sources import current_git_head  # noqa: E402
from binliquid.local_product.source_install_claim import (  # noqa: E402
    SourceInstallClaimPolicy,
    build_source_install_rc_claim,
)
from binliquid.local_product.target_closure import build_target_closure_actions  # noqa: E402

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "local-product" / "source-install-rc"
DEFAULT_EVIDENCE_ROOT = REPO_ROOT / "artifacts" / "local-product" / "harvest" / "store"


def run_source_install_rc_closure_gate(
    *,
    profile: str = "enterprise",
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    del profile
    output_root.mkdir(parents=True, exist_ok=True)
    head_sha = current_git_head()
    claim = build_source_install_rc_claim(
        policy=SourceInstallClaimPolicy(expectedHeadSha=head_sha),
        evidence_root=evidence_root,
    )
    actions = build_target_closure_actions(
        evidence_root=evidence_root,
        head_sha=head_sha,
    )
    payload = {
        "schemaVersion": "source_install_rc_closure_gate/v1",
        "status": "pass" if claim.status in {"pass", "conditional"} else "blocked",
        "sourceInstallRcClaim": claim.model_dump(mode="json", by_alias=True),
        "targetClosureActions": [
            action.model_dump(mode="json", by_alias=True) for action in actions
        ],
    }
    (output_root / "source_install_rc_closure_gate.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run source install RC closure gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = run_source_install_rc_closure_gate(
        profile=args.profile,
        evidence_root=args.evidence_root,
        output_root=args.output_root,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

