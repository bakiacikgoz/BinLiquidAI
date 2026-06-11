from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.generate_provider_conformance_matrix import generate_provider_conformance_matrix
    from scripts.run_provider_governance_gate import run_gate
except ModuleNotFoundError:
    from generate_provider_conformance_matrix import generate_provider_conformance_matrix
    from run_provider_governance_gate import run_gate

REQUIRED_DOCS = [
    Path("docs/MODEL_PROVIDER_GOVERNANCE_V1_1_CLOSURE_REPORT.md"),
    Path("docs/MODEL_PROVIDER_LIVE_CANARY_RUNBOOK.md"),
    Path("docs/RFC_NATIVE_PROVIDER_ADAPTER_V2.md"),
    Path("docs/MODEL_PROVIDER_GOVERNANCE_V1_1_PR_BODY.md"),
]


def verify_provider_release_closure(
    *,
    profile: str,
    evidence_root: Path,
) -> dict[str, Any]:
    evidence_root.mkdir(parents=True, exist_ok=True)
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    missing_docs = [path.as_posix() for path in REQUIRED_DOCS if not path.exists()]
    if missing_docs:
        blocking_reasons.extend(f"missing_doc:{item}" for item in missing_docs)

    gate_report = run_gate(profile=profile, output_dir=evidence_root / "governance-gate")
    if gate_report["status"] != "pass":
        blocking_reasons.append("provider_governance_gate_failed")

    conformance_report = generate_provider_conformance_matrix(
        profile=profile,
        mode="offline",
        output_root=evidence_root / "conformance",
    )
    if conformance_report["status"] != "pass":
        blocking_reasons.append("provider_conformance_matrix_failed")

    sensitive_scan = _scan_release_evidence(evidence_root)
    if sensitive_scan["violations"]:
        blocking_reasons.extend(
            f"forbidden_marker_in_release_evidence:{item}" for item in sensitive_scan["violations"]
        )
    if sensitive_scan["skippedPaths"]:
        warnings.extend(
            f"non_release_artifact_skipped:{item}" for item in sensitive_scan["skippedPaths"]
        )

    status = "pass" if not blocking_reasons else "fail"
    report: dict[str, Any] = {
        "version": "model_provider.v1_1_closure/v1",
        "generatedAtUtc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "profile": profile,
        "status": status,
        "blockingReasons": blocking_reasons,
        "warnings": warnings,
        "checks": {
            "requiredDocsPresent": not missing_docs,
            "providerGovernanceGate": gate_report["status"],
            "providerConformanceMatrix": conformance_report["status"],
            "liveCanaryRequired": False,
            "releaseEvidenceSensitiveScan": "pass" if not sensitive_scan["violations"] else "fail",
        },
        "paths": {
            "governanceGate": (evidence_root / "governance-gate").as_posix(),
            "conformance": (evidence_root / "conformance").as_posix(),
        },
    }
    closure_path = evidence_root / "provider_v1_1_closure.json"
    closure_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _scan_release_evidence(root: Path) -> dict[str, list[str]]:
    forbidden_markers = ("sk-", "Bearer ", "Authorization:")
    skipped_paths: list[str] = []
    violations: list[str] = []
    for path in root.glob("**/*"):
        if not path.is_file():
            continue
        if path.parts[-2:] and any(part in {"git", "security"} for part in path.parts):
            skipped_paths.append(path.as_posix())
            continue
        if path.suffix.lower() not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text for marker in forbidden_markers):
            violations.append(path.as_posix())
    return {"violations": violations, "skippedPaths": skipped_paths}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify provider governance V1.1 release closure.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("artifacts/model-provider-governance/v1_1"),
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = verify_provider_release_closure(
        profile=args.profile,
        evidence_root=args.evidence_root,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']} profile={report['profile']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
